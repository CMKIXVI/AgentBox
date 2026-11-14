"""Fail-closed gVisor-backed container execution boundary.

This adapter is intentionally separate from agent execution orchestration. It only
runs explicitly allowlisted, digest-pinned images and never mounts host paths or
falls back to an ordinary container runtime.
"""
from __future__ import annotations

import os
import re
import selectors
import signal
import subprocess
import time
import uuid
from dataclasses import dataclass
from typing import Mapping


class SandboxError(RuntimeError):
    """Base sandbox execution failure."""


class SandboxPolicyError(SandboxError):
    """The request or image is outside the configured sandbox policy."""


class SandboxUnavailableError(SandboxError):
    """The required container engine or isolation runtime is unavailable."""


class SandboxTimeoutError(SandboxError):
    """The sandbox exceeded its wall-clock deadline."""


class SandboxOutputLimitError(SandboxError):
    """The sandbox exceeded its combined stdout/stderr budget."""


@dataclass(frozen=True)
class SandboxLimits:
    timeout_seconds: int = 30
    memory_bytes: int = 256 * 1024 * 1024
    cpu_count: float = 1.0
    pids_limit: int = 64
    tmpfs_bytes: int = 64 * 1024 * 1024
    max_input_bytes: int = 1024 * 1024
    max_output_bytes: int = 1024 * 1024

    def __post_init__(self) -> None:
        if not 1 <= self.timeout_seconds <= 300:
            raise ValueError("timeout_seconds must be between 1 and 300")
        if not 64 * 1024 * 1024 <= self.memory_bytes <= 2 * 1024 * 1024 * 1024:
            raise ValueError("memory_bytes must be between 64 MiB and 2 GiB")
        if not 0.1 <= self.cpu_count <= 2.0:
            raise ValueError("cpu_count must be between 0.1 and 2.0")
        if not 16 <= self.pids_limit <= 256:
            raise ValueError("pids_limit must be between 16 and 256")
        if not 8 * 1024 * 1024 <= self.tmpfs_bytes <= 256 * 1024 * 1024:
            raise ValueError("tmpfs_bytes must be between 8 MiB and 256 MiB")
        if not 0 <= self.max_input_bytes <= 1024 * 1024:
            raise ValueError("max_input_bytes must be between 0 and 1 MiB")
        if not 1024 <= self.max_output_bytes <= 1024 * 1024:
            raise ValueError("max_output_bytes must be between 1 KiB and 1 MiB")


@dataclass(frozen=True)
class SandboxRequest:
    image: str
    argv: tuple[str, ...]
    stdin: bytes = b""


@dataclass(frozen=True)
class SandboxResult:
    status: str
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    image: str


class DockerGVisorSandboxRunner:
    """Execute a pinned image with Docker's mandatory gVisor runtime.

    The Docker daemon and host remain trusted infrastructure. This is a
    container-isolation layer, not a claim of VM-grade isolation or a complete
    hostile multi-tenant security boundary.
    """

    _DIGEST_IMAGE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/:@-]*@sha256:[a-f0-9]{64}$")
    _ALLOWED_ENV = frozenset({
        "PATH", "HOME", "DOCKER_HOST", "DOCKER_CONTEXT", "DOCKER_CONFIG",
    })

    def __init__(
        self,
        allowed_images: set[str],
        limits: SandboxLimits | None = None,
        docker_binary: str = "docker",
        runtime: str = "runsc",
        docker_env: Mapping[str, str] | None = None,
    ) -> None:
        if not allowed_images:
            raise ValueError("At least one digest-pinned sandbox image is required")
        if any(not self._DIGEST_IMAGE.fullmatch(image) for image in allowed_images):
            raise ValueError("Every allowed image must be pinned by a SHA-256 digest")
        if runtime != "runsc":
            raise ValueError("The gVisor runtime 'runsc' is mandatory; fallback is disabled")
        self.allowed_images = frozenset(allowed_images)
        self.limits = limits or SandboxLimits()
        self.docker_binary = docker_binary
        self.runtime = runtime
        source_env = docker_env if docker_env is not None else os.environ
        self.docker_env = {
            key: value for key, value in source_env.items()
            if key in self._ALLOWED_ENV and isinstance(value, str)
        }

    def _validate(self, request: SandboxRequest) -> None:
        if request.image not in self.allowed_images:
            raise SandboxPolicyError("Sandbox image is not allowlisted")
        if not self._DIGEST_IMAGE.fullmatch(request.image):
            raise SandboxPolicyError("Sandbox image must be pinned by SHA-256 digest")
        if not request.argv or len(request.argv) > 64:
            raise SandboxPolicyError("argv must contain between 1 and 64 arguments")
        if any(
            not isinstance(arg, str) or not arg or len(arg) > 4096 or "\x00" in arg
            for arg in request.argv
        ):
            raise SandboxPolicyError("Sandbox arguments must be non-empty bounded strings")
        if not isinstance(request.stdin, bytes):
            raise SandboxPolicyError("stdin must be bytes")
        if len(request.stdin) > self.limits.max_input_bytes:
            raise SandboxPolicyError("Sandbox input exceeds the configured limit")

    def _build_command(self, request: SandboxRequest, container_name: str) -> list[str]:
        limits = self.limits
        return [
            self.docker_binary, "run",
            "--rm",
            "--interactive",
            f"--name={container_name}",
            f"--runtime={self.runtime}",
            "--pull=never",
            "--network=none",
            "--ipc=none",
            "--uts=private",
            "--read-only",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges",
            "--pids-limit", str(limits.pids_limit),
            "--memory", str(limits.memory_bytes),
            "--memory-swap", str(limits.memory_bytes),
            "--cpus", str(limits.cpu_count),
            "--user=65532:65532",
            "--workdir=/workspace",
            f"--tmpfs=/tmp:rw,noexec,nosuid,nodev,size={limits.tmpfs_bytes}",
            f"--tmpfs=/workspace:rw,noexec,nosuid,nodev,size={limits.tmpfs_bytes}",
            "--log-driver=none",
            "--ulimit=nofile=64:64",
            "--ulimit=core=0",
            request.image,
            *request.argv,
        ]

    def _stop_process(self, process: subprocess.Popen[bytes]) -> None:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError, AttributeError):
            process.kill()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)

    def _remove_container(self, container_name: str) -> None:
        try:
            subprocess.run(
                [self.docker_binary, "rm", "--force", container_name],
                capture_output=True,
                timeout=5,
                check=False,
                env=self.docker_env,
                close_fds=True,
            )
        except (OSError, subprocess.SubprocessError):
            # Cleanup is best-effort; the execution failure is still returned.
            pass

    def run(self, request: SandboxRequest) -> SandboxResult:
        self._validate(request)
        container_name = f"agentbox-sbx-{uuid.uuid4().hex}"
        command = self._build_command(request, container_name)
        started = time.monotonic()
        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0,
                close_fds=True,
                start_new_session=True,
                env=self.docker_env,
            )
        except FileNotFoundError as exc:
            raise SandboxUnavailableError("Docker CLI is not installed") from exc
        except OSError as exc:
            raise SandboxUnavailableError("Docker CLI could not be started") from exc

        assert process.stdin is not None
        assert process.stdout is not None
        assert process.stderr is not None
        selector = selectors.DefaultSelector()
        stdout = bytearray()
        stderr = bytearray()
        pending_input = memoryview(request.stdin)
        input_offset = 0
        total_output = 0
        deadline = started + self.limits.timeout_seconds
        streams_open = {"stdout", "stderr"}
        timed_out = False
        output_limited = False

        try:
            os.set_blocking(process.stdout.fileno(), False)
            os.set_blocking(process.stderr.fileno(), False)
            selector.register(process.stdout, selectors.EVENT_READ, "stdout")
            selector.register(process.stderr, selectors.EVENT_READ, "stderr")
            if pending_input:
                os.set_blocking(process.stdin.fileno(), False)
                selector.register(process.stdin, selectors.EVENT_WRITE, "stdin")
            else:
                process.stdin.close()

            while streams_open or process.poll() is None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    timed_out = True
                    break
                events = selector.select(min(remaining, 0.1))
                for key, _ in events:
                    stream_name = key.data
                    stream = key.fileobj
                    if stream_name == "stdin":
                        try:
                            written = os.write(
                                stream.fileno(),
                                pending_input[input_offset:input_offset + 65536],
                            )
                            input_offset += written
                        except BrokenPipeError:
                            input_offset = len(pending_input)
                        if input_offset >= len(pending_input):
                            selector.unregister(stream)
                            stream.close()
                        continue

                    chunk = os.read(stream.fileno(), 65536)
                    if not chunk:
                        selector.unregister(stream)
                        streams_open.discard(stream_name)
                        stream.close()
                        continue
                    total_output += len(chunk)
                    if total_output > self.limits.max_output_bytes:
                        output_limited = True
                        break
                    (stdout if stream_name == "stdout" else stderr).extend(chunk)
                if output_limited:
                    break

            if timed_out or output_limited:
                self._stop_process(process)
                self._remove_container(container_name)
            else:
                process.wait(timeout=max(0.1, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            timed_out = True
            self._stop_process(process)
            self._remove_container(container_name)
        finally:
            selector.close()
            for stream in (process.stdin, process.stdout, process.stderr):
                if stream and not stream.closed:
                    stream.close()

        if timed_out:
            raise SandboxTimeoutError("Sandbox exceeded its wall-clock deadline")
        if output_limited:
            raise SandboxOutputLimitError("Sandbox exceeded its combined output limit")

        exit_code = process.returncode if process.returncode is not None else -1
        return SandboxResult(
            status="succeeded" if exit_code == 0 else "failed",
            exit_code=exit_code,
            stdout=stdout.decode("utf-8", errors="replace"),
            stderr=stderr.decode("utf-8", errors="replace"),
            duration_ms=max(0, int((time.monotonic() - started) * 1000)),
            image=request.image,
        )
