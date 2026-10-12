from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass(slots=True)
class ValidationResult:
    ok: bool
    checks: list[dict]

    def to_dict(self) -> dict:
        return asdict(self)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_capture(root: Path) -> ValidationResult:
    checks: list[dict] = []
    required = [
        root / "full-report.json",
        root / "html" / "source.html",
        root / "dom" / "rendered.html",
    ]
    for path in required:
        checks.append({"check": str(path), "ok": path.exists(), "size": path.stat().st_size if path.exists() else 0})
    report = root / "full-report.json"
    if report.exists():
        checks.append({"check": "report-sha256", "ok": True, "sha256": sha256(report)})
    ok = all(item.get("ok", False) for item in checks if not item["check"].startswith("report-sha256"))
    return ValidationResult(ok=ok, checks=checks)
