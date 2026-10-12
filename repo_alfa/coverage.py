from __future__ import annotations

import json
from pathlib import Path


def build_coverage(report: dict, root: Path) -> dict:
    modules = {m.get("name"): m for m in report.get("modules", [])}

    def status(name: str, artifact: Path | None = None) -> dict:
        mod = modules.get(name)
        available = bool(mod and mod.get("status") == "complete")
        if artifact is not None:
            available = available or artifact.exists()
        return {
            "status": "complete" if available else "unavailable",
            "reason": None if available else "module did not complete or artifact was not produced",
        }

    matrix = {
        "html": status("static-capture", root / "html" / "source.html"),
        "rendered_dom": status("browser-capture", root / "dom" / "rendered.html"),
        "network": status("browser-capture", root / "network" / "events.json"),
        "storage": status("browser-capture", root / "storage" / "browser.json"),
        "crawler": status("crawler"),
        "assets": status("asset-download", root / "assets"),
        "javascript": {"status": "complete" if (root / "reports" / "javascript.json").exists() else "unavailable"},
        "graphql": {"status": "complete" if (root / "reports" / "graphql.json").exists() else "unavailable"},
        "har": {"status": "complete" if (root / "reports" / "capture.har").exists() else "unavailable"},
        "route_graph": {"status": "complete" if (root / "reports" / "route-graph.json").exists() else "unavailable"},
        "endpoint_graph": {"status": "complete" if (root / "reports" / "endpoint-graph.json").exists() else "unavailable"},
    }
    complete = sum(1 for value in matrix.values() if value.get("status") == "complete")
    total = len(matrix)
    return {
        "score": round((complete / total) * 100, 2) if total else 0.0,
        "complete": complete,
        "total": total,
        "matrix": matrix,
    }


def write_coverage(report: dict, root: Path, output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    data = build_coverage(report, root)
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return output
