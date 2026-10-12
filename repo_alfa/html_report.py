from __future__ import annotations

import html
import json
from pathlib import Path


def render_html_report(report: dict, output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for module in report.get("modules", []):
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(module.get('name','')))}</td>"
            f"<td>{html.escape(str(module.get('status','')))}</td>"
            f"<td>{int(module.get('recovered_failures') or 0)}</td>"
            f"<td>{html.escape('; '.join(module.get('errors', [])))}</td>"
            "</tr>"
        )
    body = f"""<!doctype html>
<html lang='en'>
<head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>REPO ALFA Report</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:1200px;margin:40px auto;padding:0 20px;background:#0d1117;color:#e6edf3}}
code,pre{{background:#161b22;padding:4px 6px;border-radius:6px}} table{{border-collapse:collapse;width:100%}}
th,td{{border:1px solid #30363d;padding:8px;text-align:left}} th{{background:#161b22}}
.metric{{display:inline-block;margin:8px;padding:12px;background:#161b22;border:1px solid #30363d;border-radius:8px}}
</style></head><body>
<h1>REPO ALFA forensic report</h1>
<p><b>Target:</b> {html.escape(str(report.get('target','')))}</p>
<div class='metric'>Mode: {html.escape(str(report.get('mode','')))}</div>
<div class='metric'>Routes: {len(report.get('routes', []))}</div>
<div class='metric'>Endpoints: {len(report.get('observed_endpoints', []))}</div>
<div class='metric'>Technologies: {len(report.get('technologies', []))}</div>
<h2>Modules</h2><table><thead><tr><th>Module</th><th>Status</th><th>Recovered</th><th>Errors</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>
<h2>Raw report</h2><pre>{html.escape(json.dumps(report, ensure_ascii=False, indent=2))}</pre>
</body></html>"""
    output.write_text(body, encoding="utf-8")
    return output
