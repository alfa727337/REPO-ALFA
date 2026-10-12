from __future__ import annotations

import html
import json
from pathlib import Path


def _escape(value) -> str:
    return html.escape(str(value if value is not None else ""))


def _table(headers: list[str], rows: list[list[str]]) -> str:
    head = "".join(f"<th>{_escape(item)}</th>" for item in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>"
        for row in rows
    )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def render_html_report(report: dict, output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)

    module_rows = []
    for module in report.get("modules", []):
        errors = "; ".join(module.get("errors", []))
        module_rows.append(
            [
                _escape(module.get("name")),
                _escape(module.get("status")),
                _escape(module.get("recovered_failures", 0)),
                _escape(errors),
            ]
        )

    framework_rows = []
    for framework in report.get("framework_matches", []):
        framework_rows.append(
            [
                _escape(framework.get("name")),
                _escape(framework.get("confidence")),
                _escape(", ".join(framework.get("evidence", []))),
                f"<pre>{_escape(json.dumps(framework.get('details', {}), ensure_ascii=False, indent=2))}</pre>",
            ]
        )

    coverage = report.get("coverage") or {}
    coverage_rows = []
    for layer, data in (coverage.get("matrix") or {}).items():
        coverage_rows.append(
            [
                _escape(layer),
                _escape(data.get("status")),
                _escape(data.get("reason")),
            ]
        )

    route_items = "".join(
        f"<li><code>{_escape(route)}</code></li>" for route in report.get("routes", [])[:1000]
    )
    endpoint_items = "".join(
        f"<li><code>{_escape(endpoint)}</code></li>"
        for endpoint in report.get("observed_endpoints", [])[:1000]
    )
    artifact_items = "".join(
        f"<li><code>{_escape(path)}</code></li>" for path in report.get("artifacts", [])
    )

    raw_json = _escape(json.dumps(report, ensure_ascii=False, indent=2))
    body = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>REPO ALFA Report</title>
<style>
:root {{ color-scheme: dark; }}
body {{ font-family: Inter, system-ui, sans-serif; max-width: 1280px; margin: 0 auto;
  padding: 32px; background: #0d1117; color: #e6edf3; }}
h1,h2 {{ color: #f0f6fc; }}
a {{ color: #58a6ff; }}
code,pre {{ background: #161b22; border-radius: 6px; }}
code {{ padding: 2px 5px; }}
pre {{ padding: 12px; overflow: auto; white-space: pre-wrap; word-break: break-word; }}
table {{ border-collapse: collapse; width: 100%; margin: 12px 0 24px; }}
th,td {{ border: 1px solid #30363d; padding: 8px; text-align: left; vertical-align: top; }}
th {{ background: #161b22; }}
.metrics {{ display: flex; flex-wrap: wrap; gap: 10px; margin: 18px 0 26px; }}
.metric {{ padding: 12px 14px; background: #161b22; border: 1px solid #30363d;
  border-radius: 8px; }}
section {{ margin-top: 32px; }}
details {{ margin-top: 24px; }}
ul {{ max-height: 480px; overflow: auto; }}
</style>
</head>
<body>
<h1>REPO ALFA forensic report</h1>
<p><strong>Target:</strong> {_escape(report.get('target'))}</p>
<div class="metrics">
  <div class="metric">Mode: {_escape(report.get('mode'))}</div>
  <div class="metric">Coverage: {_escape(coverage.get('score', 0))}%</div>
  <div class="metric">Routes: {len(report.get('routes', []))}</div>
  <div class="metric">Endpoints: {len(report.get('observed_endpoints', []))}</div>
  <div class="metric">Technologies: {len(report.get('technologies', []))}</div>
  <div class="metric">Frameworks: {len(report.get('framework_matches', []))}</div>
</div>
<section><h2>Modules</h2>{_table(['Module','Status','Recovered','Errors'], module_rows)}</section>
<section><h2>Coverage</h2>{_table(['Layer','Status','Reason'], coverage_rows)}</section>
<section><h2>Frameworks</h2>{_table(['Framework','Confidence','Evidence','Details'], framework_rows)}</section>
<section><h2>Routes</h2><ul>{route_items}</ul></section>
<section><h2>Observed endpoints</h2><ul>{endpoint_items}</ul></section>
<section><h2>Artifacts</h2><ul>{artifact_items}</ul></section>
<details><summary>Raw report JSON</summary><pre>{raw_json}</pre></details>
</body></html>"""
    output.write_text(body, encoding="utf-8")
    return output
