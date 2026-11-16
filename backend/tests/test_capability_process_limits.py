from __future__ import annotations

from app import capability_process_limits as limits


def test_capability_process_limits_set_cpu_memory_file_and_descriptor_caps(monkeypatch):
    calls = []
    monkeypatch.setattr(limits.os, "name", "posix")
    monkeypatch.setattr(limits, "resource", type("Resource", (), {
        "RLIMIT_CPU": 1,
        "RLIMIT_AS": 2,
        "RLIMIT_FSIZE": 3,
        "RLIMIT_NOFILE": 4,
        "RLIMIT_CORE": 5,
        "setrlimit": staticmethod(lambda key, value: calls.append((key, value))),
    })())
    limits.apply_capability_process_limits(8)
    assert calls == [
        (1, (9, 9)),
        (2, (1024 * 1024 * 1024, 1024 * 1024 * 1024)),
        (3, (16 * 1024 * 1024, 16 * 1024 * 1024)),
        (4, (64, 64)),
        (5, (0, 0)),
    ]


def test_capability_process_limits_reject_invalid_timeout():
    import pytest

    with pytest.raises(ValueError):
        limits.apply_capability_process_limits(0)
    with pytest.raises(ValueError):
        limits.apply_capability_process_limits(True)


def test_capability_process_limits_fail_closed_when_unavailable(monkeypatch):
    import pytest

    monkeypatch.setattr(limits, "resource", None)
    with pytest.raises(RuntimeError, match="require a POSIX"):
        limits.apply_capability_process_limits(5)
