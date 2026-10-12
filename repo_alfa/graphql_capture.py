from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

GRAPHQL_HINTS = ("graphql", "apollo", "relay", "urql")


def detect_graphql(network_events: list[dict]) -> dict:
    endpoints: dict[str, dict] = {}
    for event in network_events:
        url = str(event.get("url") or "")
        if not url:
            continue
        lowered = url.lower()
        if any(hint in lowered for hint in GRAPHQL_HINTS):
            item = endpoints.setdefault(url, {"url": url, "methods": set(), "statuses": set()})
            if event.get("method"):
                item["methods"].add(str(event["method"]))
            if event.get("status") is not None:
                item["statuses"].add(int(event["status"]))
    normalized = []
    for item in endpoints.values():
        normalized.append(
            {
                "url": item["url"],
                "host": urlparse(item["url"]).netloc,
                "methods": sorted(item["methods"]),
                "statuses": sorted(item["statuses"]),
            }
        )
    return {"detected": bool(normalized), "endpoints": sorted(normalized, key=lambda x: x["url"])}


def write_report(data: dict, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
