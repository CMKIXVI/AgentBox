"""Deny-by-default, deterministic AgentBox capability authorization."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Iterable

from .principal import Principal


def _timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Policy timestamps must include a timezone")
    return parsed.astimezone(UTC)


def authorize_capability(
    principal: Principal | None,
    capability_id: str,
    action: str,
    resource_id: str,
    policies: Iterable[dict[str, Any]],
    evaluated_at: datetime | None = None,
) -> dict[str, Any]:
    """Evaluate explicit policy matches. Any matching deny overrides all allows."""
    now = evaluated_at or datetime.now(UTC)
    if now.tzinfo is None:
        raise ValueError("evaluated_at must be timezone-aware")
    if principal is None:
        return {"allowed": False, "reason": "missing_principal", "matched_policy_ids": []}
    if not principal.active:
        return {"allowed": False, "reason": "inactive_principal", "matched_policy_ids": []}
    if not all((capability_id, action, resource_id)):
        return {"allowed": False, "reason": "incomplete_request", "matched_policy_ids": []}

    allows: list[str] = []
    denies: list[str] = []
    for policy in policies:
        if not isinstance(policy, dict) or not policy.get("active", False):
            continue
        if policy.get("capability_id") != capability_id or policy.get("principal_scope") != principal.principal_type:
            continue
        if principal.subject_id not in policy.get("principal_ids", []):
            continue
        tenant_id = principal.tenant_id
        if tenant_id is None or tenant_id not in policy.get("tenant_ids", []):
            continue
        if action not in policy.get("actions", []) or resource_id not in policy.get("resource_ids", []):
            continue
        try:
            if policy.get("not_before") and now < _timestamp(policy["not_before"]):
                continue
            if policy.get("expires_at") and now >= _timestamp(policy["expires_at"]):
                continue
        except (TypeError, ValueError):
            # Malformed temporal policy is never treated as an authorization grant.
            continue
        policy_id = str(policy.get("policy_id", ""))
        if policy.get("effect") == "deny":
            denies.append(policy_id)
        elif policy.get("effect") == "allow":
            allows.append(policy_id)

    if denies:
        return {"allowed": False, "reason": "explicit_deny", "matched_policy_ids": sorted(denies)}
    if allows:
        return {"allowed": True, "reason": "explicit_allow", "matched_policy_ids": sorted(allows)}
    return {"allowed": False, "reason": "no_matching_allow_policy", "matched_policy_ids": []}
