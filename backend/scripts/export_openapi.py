"""Export the live FastAPI OpenAPI document for frontend contract generation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.main import app


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("../contracts/openapi/agentbox-openapi.json"),
        help="Output path for the generated OpenAPI JSON document",
    )
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Exported AgentBox OpenAPI to {args.output}")


if __name__ == "__main__":
    main()
