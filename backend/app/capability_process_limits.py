"""Per-invocation OS resource limits for trusted capability child processes.

These limits are defense in depth, not a sandbox. The parent still enforces the
wall-clock deadline and systemd supplies aggregate service cgroup limits.
"""
from __future__ import annotations

import math
import os

try:
    import resource
except ImportError:  # pragma: no cover - exercised only on non-POSIX platforms
    resource = None


# Deliberately conservative defaults; deployments should tune against real handler
# workloads rather than raising these limits from untrusted contract input.
_MAX_ADDRESS_SPACE_BYTES = 1024 * 1024 * 1024
_MAX_FILE_BYTES = 16 * 1024 * 1024
_MAX_OPEN_FILES = 64


def apply_capability_process_limits(timeout_seconds: int) -> None:
    """Apply hard per-child limits before any capability handler code runs."""
    if resource is None or os.name != "posix":
        raise RuntimeError("per-invocation resource limits require a POSIX worker")
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, int) or timeout_seconds < 1:
        raise ValueError("timeout_seconds must be a positive integer")

    cpu_seconds = max(1, math.ceil(timeout_seconds)) + 1
    limits = (
        (resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds)),
        (resource.RLIMIT_AS, (_MAX_ADDRESS_SPACE_BYTES, _MAX_ADDRESS_SPACE_BYTES)),
        (resource.RLIMIT_FSIZE, (_MAX_FILE_BYTES, _MAX_FILE_BYTES)),
        (resource.RLIMIT_NOFILE, (_MAX_OPEN_FILES, _MAX_OPEN_FILES)),
        (resource.RLIMIT_CORE, (0, 0)),
    )
    try:
        for limit, value in limits:
            resource.setrlimit(limit, value)
    except (OSError, ValueError) as exc:
        raise RuntimeError("could not enforce capability process resource limits") from exc
