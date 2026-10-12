import json
from pathlib import Path

from repo_alfa.sqlite_index import build_index, verify_evidence_manifest


def test_evidence_manifest_detects_tampering(tmp_path: Path):
    root = tmp_path / "capture"
    root.mkdir()
    artifact = root / "sample.txt"
    artifact.write_text("original", encoding="utf-8")
    report = {
        "target": "https://example.com",
        "mode": "forensic",
        "routes": [],
        "observed_endpoints": [],
        "technologies": [],
        "framework_matches": [],
        "modules": [],
        "coverage": {"matrix": {}},
    }
    build_index(report, root, root / "reports" / "forensic.sqlite3")
    manifest = json.loads((root / "evidence-manifest.json").read_text(encoding="utf-8"))
    assert manifest["artifact_count"] >= 1
    assert verify_evidence_manifest(root)["ok"] is True

    artifact.write_text("tampered", encoding="utf-8")
    verification = verify_evidence_manifest(root)
    assert verification["ok"] is False
    assert any(item["path"] == "sample.txt" for item in verification["mismatches"])
