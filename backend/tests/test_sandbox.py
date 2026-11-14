from __future__ import annotations

from app.sandbox import (
    DockerGVisorSandboxRunner,
    SandboxLimits,
    SandboxPolicyError,
    SandboxRequest,
)

import pytest


IMAGE = "registry.example.test/agentbox/runner@sha256:" + "a" * 64


def runner(**kwargs):
    return DockerGVisorSandboxRunner(allowed_images={IMAGE}, **kwargs)


def test_command_requires_gvisor_and_disables_network_and_host_capabilities():
    value = runner()
    command = value._build_command(
        SandboxRequest(image=IMAGE, argv=("python", "-I", "-c", "print('ok')")),
        "agentbox-sbx-test",
    )
    joined = " ".join(command)
    assert "--runtime=runsc" in command
    assert "--network=none" in command
    assert "--read-only" in command
    assert "--cap-drop=ALL" in command
    assert "--security-opt=no-new-privileges" in command
    assert "--pids-limit 64" in joined
    assert "--memory-swap 268435456" in joined
    assert "--user=65532:65532" in command
    assert not any(arg == "--privileged" or arg.startswith("--volume") for arg in command)
    assert IMAGE in command


def test_non_allowlisted_image_is_denied():
    value = runner()
    with pytest.raises(SandboxPolicyError, match="not allowlisted"):
        value._validate(SandboxRequest(image="alpine:latest", argv=("sh",)))


def test_digest_pinning_is_required_at_configuration_time():
    with pytest.raises(ValueError, match="SHA-256 digest"):
        DockerGVisorSandboxRunner(allowed_images={"runner:latest"})


def test_runtime_fallback_is_rejected():
    with pytest.raises(ValueError, match="mandatory"):
        DockerGVisorSandboxRunner(allowed_images={IMAGE}, runtime="runc")


@pytest.mark.parametrize(
    "limits",
    [
        {"timeout_seconds": 0},
        {"timeout_seconds": 301},
        {"memory_bytes": 1024},
        {"cpu_count": 4.0},
        {"pids_limit": 0},
        {"max_output_bytes": 2 * 1024 * 1024},
    ],
)
def test_unsafe_resource_limits_are_rejected(limits):
    with pytest.raises(ValueError):
        SandboxLimits(**limits)


def test_argument_and_input_limits_are_enforced():
    value = runner(limits=SandboxLimits(max_input_bytes=4))
    with pytest.raises(SandboxPolicyError, match="arguments"):
        value._validate(SandboxRequest(image=IMAGE, argv=()))
    with pytest.raises(SandboxPolicyError, match="input"):
        value._validate(SandboxRequest(image=IMAGE, argv=("cat",), stdin=b"12345"))
    with pytest.raises(SandboxPolicyError, match="arguments"):
        value._validate(SandboxRequest(image=IMAGE, argv=("bad\x00arg",)))


def test_docker_environment_is_allowlisted():
    value = DockerGVisorSandboxRunner(
        allowed_images={IMAGE},
        docker_env={
            "PATH": "/usr/bin",
            "HOME": "/runner",
            "SECRET_TOKEN": "must-not-pass",
            "AWS_SECRET_ACCESS_KEY": "must-not-pass",
        },
    )
    assert value.docker_env == {"PATH": "/usr/bin", "HOME": "/runner"}
