"""Local AgentBox tenant administration CLI.

This interface is intentionally offline: it operates on the host's AgentBox
SQLite database and exposes no tenant provisioning HTTP endpoints.
"""
from __future__ import annotations

import argparse
import getpass
import json
import os
import sqlite3
import sys
from collections.abc import Sequence
from pathlib import Path

from .tenant_backup import BackupError, EnvironmentBackupKeyProvider, TenantBackupService
from .tenant_registry import TenantConflictError, TenantNotFoundError, TenantRegistry

VALID_TRANSITIONS = ("active", "suspended", "decommissioned")


def local_operator_actor_id() -> str:
    """Return the local OS identity used for audit attribution."""
    if hasattr(os, "getuid"):
        import pwd

        uid = os.getuid()
        try:
            username = pwd.getpwuid(uid).pw_name
        except KeyError:
            username = "unknown"
        return f"os-user:{uid}:{username}"
    return f"os-user:{getpass.getuser()}"


def default_database_path() -> str:
    configured = os.getenv("AGENTBOX_DATABASE_PATH")
    if configured:
        return configured
    return str(Path(__file__).resolve().parents[1] / "data" / "agentbox.sqlite3")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agentbox-tenant", description="Administer local AgentBox tenants")
    parser.add_argument("--database", default=default_database_path(), help="AgentBox SQLite database path")
    commands = parser.add_subparsers(dest="command", required=True)

    create = commands.add_parser("create", help="Create a tenant in pending state")
    create.add_argument("--tenant-id", required=True)
    create.add_argument("--display-name", required=True)
    create.add_argument("--metadata-json", default="{}", help="Bounded scalar JSON object")

    listing = commands.add_parser("list", help="List tenant records")
    listing.add_argument("--limit", type=int, default=100)
    listing.add_argument("--offset", type=int, default=0)

    for name in VALID_TRANSITIONS:
        transition = commands.add_parser(name, help=f"Transition a tenant to {name}")
        transition.add_argument("--tenant-id", required=True)

    audit = commands.add_parser("audit", help="Show append-only audit events for one tenant")
    audit.add_argument("--tenant-id", required=True)

    backup = commands.add_parser("backup", help="Write an authenticated encrypted tenant backup")
    backup.add_argument("--tenant-id", required=True)
    backup.add_argument("--output", required=True)

    restore = commands.add_parser("restore", help="Restore tenant data from an encrypted backup")
    restore.add_argument("--tenant-id", required=True)
    restore.add_argument("--input", required=True)
    return parser


def _require_agentbox_database(database_path: str) -> None:
    """Refuse to silently create or operate on a different/empty SQLite database."""
    path = Path(database_path)
    if not path.is_file():
        raise ValueError(f"AgentBox database does not exist: {path}")
    uri = f"{path.resolve().as_uri()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    required = {"agent_versions", "executions", "evaluation_profiles", "evaluation_runs", "tenants", "tenant_audit"}
    missing = sorted(required - tables)
    if missing:
        raise ValueError(
            f"Database is not an initialized AgentBox database; missing tables: {missing}"
        )


def _emit(value: object) -> None:
    print(json.dumps(value, sort_keys=True, separators=(",", ":")))


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    actor_id = local_operator_actor_id()
    try:
        _require_agentbox_database(args.database)
        registry = TenantRegistry(args.database)
        if args.command == "create":
            try:
                metadata = json.loads(args.metadata_json)
            except json.JSONDecodeError as exc:
                raise ValueError("--metadata-json must contain valid JSON") from exc
            if not isinstance(metadata, dict):
                raise ValueError("--metadata-json must be a JSON object")
            record = registry.create(args.tenant_id, args.display_name, actor_id, metadata)
            _emit(record.__dict__)
        elif args.command == "list":
            _emit([record.__dict__ for record in registry.list(args.limit, args.offset)])
        elif args.command in VALID_TRANSITIONS:
            record = registry.transition(args.tenant_id, args.command, actor_id)
            _emit(record.__dict__)
        elif args.command == "audit":
            _emit(registry.audit_events(args.tenant_id))
        elif args.command == "backup":
            service = TenantBackupService(args.database, EnvironmentBackupKeyProvider())
            _emit(service.export_encrypted(args.tenant_id, args.output))
        elif args.command == "restore":
            service = TenantBackupService(args.database, EnvironmentBackupKeyProvider())
            _emit(service.restore_encrypted(args.tenant_id, args.input))
        else:
            parser.error("unsupported command")
        return 0
    except (ValueError, BackupError, TenantConflictError, TenantNotFoundError, sqlite3.Error, OSError) as exc:
        print(f"agentbox-tenant: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
