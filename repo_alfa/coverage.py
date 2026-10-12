from __future__ import annotations

import json
from pathlib import Path


def build_coverage(report: dict, root: Path) -> dict:
    modules = {m.get("name"): m for m in report.get("modules", [])}

    def status(name: str | None = None, artifact: Path | None = None) -> dict:
        module_ok = False
        if name is not None:
            mod = modules.get(name)
            module_ok = bool(mod and mod.get("status") == "complete")
        artifact_ok = artifact.exists() if artifact is not None else False
        available = module_ok or artifact_ok
        return {
            "status": "complete" if available else "unavailable",
            "reason": (
                None
                if available
                else "module did not complete or expected artifact was not produced"
            ),
        }

    reports = root / "reports"
    matrix = {
        "html": status("static-capture", root / "html" / "source.html"),
        "metadata": status("static-capture", root / "html" / "metadata.json"),
        "headers": status("static-capture", root / "headers" / "initial-response.json"),
        "rendered_dom": status("browser-capture", root / "dom" / "rendered.html"),
        "desktop_screenshot": status(None, root / "screenshots" / "desktop.png"),
        "mobile_screenshot": status(None, root / "screenshots" / "mobile.png"),
        "network": status("browser-capture", root / "network" / "events.json"),
        "websocket": status("browser-capture", root / "websocket" / "events.json"),
        "console": status("browser-capture", root / "console" / "events.json"),
        "storage": status("browser-capture", root / "storage" / "browser.json"),
        "ui_inventory": status("browser-capture", root / "ui" / "interactive-elements.json"),
        "ui_states": status(None, root / "ui" / "states.json"),
        "public_discovery": status("public-discovery", root / "discovery" / "discovery.json"),
        "crawler": status("crawler"),
        "assets": status("asset-download", root / "assets" / "manifest.json"),
        "javascript": status(None, reports / "javascript.json"),
        "css": status(None, reports / "css.json"),
        "dom_diff": status(None, reports / "dom-diff.json"),
        "frameworks": status(None, reports / "frameworks.json"),
        "graphql": status(None, reports / "graphql.json"),
        "har": status(None, reports / "capture.har"),
        "network_summary": status(None, reports / "network-summary.json"),
        "route_graph": status(None, reports / "route-graph.json"),
        "endpoint_graph": status(None, reports / "endpoint-graph.json"),
        "pwa": status("pwa-analysis", root / "pwa" / "pwa-analysis.json"),
        "source_maps": status(None, reports / "sourcemaps.json"),
        "security_audit": status(None, reports / "security-audit.json"),
        "reconstruction": status("reconstruction", root / "reconstructed" / "index.html"),
    }
    complete = sum(1 for value in matrix.values() if value.get("status") == "complete")
    total = len(matrix)
    unavailable = total - complete
    return {
        "score": round((complete / total) * 100, 2) if total else 0.0,
        "complete": complete,
        "unavailable": unavailable,
        "total": total,
        "matrix": matrix,
    }


def write_coverage(report: dict, root: Path, output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    data = build_coverage(report, root)
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return output
