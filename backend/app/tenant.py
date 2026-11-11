"""AgentBox tenant identity and lifecycle value objects."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

TenantStatus = Literal["pending", "active", "suspended", "decommissioned"]
TENANT_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{1,127}$")
RESERVED_TENANT_IDS = frozenset({"__legacy_unassigned__"})
TENANT_TRANSITIONS: dict[str, frozenset[str]] = {
    "pending": frozenset({"active", "suspended", "decommissioned"}),
    "active": frozenset({"suspended", "decommissioned"}),
    "suspended": frozenset({"active", "decommissioned"}),
    "decommissioned": frozenset(),
}


def validate_tenant_id(tenant_id: str) -> str:
    if not isinstance(tenant_id, str) or not TENANT_ID_PATTERN.fullmatch(tenant_id):
        raise ValueError("tenant_id must be 2-128 safe identifier characters")
    if tenant_id in RESERVED_TENANT_IDS:
        raise ValueError("tenant_id is reserved by AgentBox")
    return tenant_id


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds")


@dataclass(frozen=True)
class TenantRecord:
    tenant_id: str
    display_name: str
    status: TenantStatus
    created_at: str
    updated_at: str
    metadata: dict[str, str | int | float | bool | None]

    @property
    def is_accessible(self) -> bool:
        return self.status == "active"


def validate_transition(current: str, target: str) -> None:
    if target not in TENANT_TRANSITIONS.get(current, frozenset()):
        raise ValueError(f"Invalid AgentBox tenant lifecycle transition: {current} -> {target}")
