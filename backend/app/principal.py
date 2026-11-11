"""Authenticated principal value object used by AgentBox policy evaluation."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

PrincipalType = Literal["user", "tenant", "service", "system"]


@dataclass(frozen=True)
class Principal:
    subject_id: str
    principal_type: PrincipalType
    tenant_id: str | None = None
    active: bool = True

    def __post_init__(self) -> None:
        if not self.subject_id or len(self.subject_id) > 256:
            raise ValueError("subject_id must contain 1 to 256 characters")
        if self.principal_type not in {"user", "tenant", "service", "system"}:
            raise ValueError("Unsupported principal_type")
        if self.tenant_id is not None and (not self.tenant_id or len(self.tenant_id) > 256):
            raise ValueError("tenant_id must contain 1 to 256 characters")
        if self.principal_type == "tenant" and self.tenant_id != self.subject_id:
            raise ValueError("A tenant principal must use its tenant ID as both subject_id and tenant_id")
        if not isinstance(self.active, bool):
            raise TypeError("active must be a boolean")
