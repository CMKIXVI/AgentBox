from __future__ import annotations

import csv
import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from build_recovery_catalogue import build  # noqa: E402


def make_archive(path: Path, valid_hash: bool = True) -> None:
    payload = b"def clone_agent(parent):\n    return parent.copy()\n"
    digest = hashlib.sha256(payload).hexdigest() if valid_hash else "0" * 64
    index = io.StringIO()
    writer = csv.DictWriter(index, fieldnames=[
        "archive_path", "artifact_type", "block_number", "bytes",
        "context_heading", "detected_language", "output_path", "sha256",
    ])
    writer.writeheader()
    writer.writerow({
        "archive_path": "2026/Agent Factory OS Concept.md",
        "artifact_type": "fenced_code_block", "block_number": "1",
        "bytes": str(len(payload)), "context_heading": "Agent cloning and lifecycle",
        "detected_language": "python", "output_path": "code/agent_clone.py",
        "sha256": digest,
    })
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("extraction_index.csv", index.getvalue())
        archive.writestr("code/agent_clone.py", payload)


def test_catalogue_preserves_provenance_and_candidate_status(tmp_path: Path) -> None:
    archive, output = tmp_path / "source.zip", tmp_path / "out"
    make_archive(archive)
    summary = build(archive, output)
    rows = list(csv.DictReader((output / "agentbox-recovery-candidates.csv").open()))
    assert summary["candidate_count"] == 1
    assert rows[0]["recovery_status"] == "Candidate"
    assert rows[0]["integration_status"] == "Not started"
    assert rows[0]["source_provenance"] == (
        "2026/Agent Factory OS Concept.md#block-1; archive:code/agent_clone.py"
    )
    assert rows[0]["original_hash"] == hashlib.sha256(
        b"def clone_agent(parent):\n    return parent.copy()\n"
    ).hexdigest()
    assert rows[0]["agentbox_subsystem"] == "agent-definition-registry-lineage"
    assert json.loads((output / "agentbox-recovery-candidates.json").read_text())[0]["recovery_id"] == rows[0]["recovery_id"]


def test_catalogue_rejects_index_hash_mismatch(tmp_path: Path) -> None:
    archive, output = tmp_path / "source.zip", tmp_path / "out"
    make_archive(archive, valid_hash=False)
    summary = build(archive, output)
    assert summary["candidate_count"] == 0
    assert summary["hash_mismatches_skipped"] == 1
