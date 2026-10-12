import json
from pathlib import Path

from repo_alfa.coverage import build_coverage
from repo_alfa.validator import validate_capture


def test_validator_requires_core_artifacts(tmp_path: Path):
    root = tmp_path / "capture"
    (root / "html").mkdir(parents=True)
    (root / "dom").mkdir(parents=True)
    (root / "html" / "source.html").write_text("<html></html>", encoding="utf-8")
    (root / "dom" / "rendered.html").write_text("<html></html>", encoding="utf-8")
    (root / "full-report.json").write_text(json.dumps({"target": "https://example.com"}), encoding="utf-8")
    result = validate_capture(root)
    assert result.ok is True


def test_coverage_reports_partial_capture(tmp_path: Path):
    root = tmp_path / "capture"
    (root / "html").mkdir(parents=True)
    (root / "html" / "source.html").write_text("<html></html>", encoding="utf-8")
    report = {
        "modules": [
            {"name": "static-capture", "status": "complete"},
            {"name": "browser-capture", "status": "failed"},
        ]
    }
    result = build_coverage(report, root)
    assert result["matrix"]["html"]["status"] == "complete"
    assert result["matrix"]["rendered_dom"]["status"] == "unavailable"
    assert 0 < result["score"] < 100
