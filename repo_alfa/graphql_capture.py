from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse, urlunparse

GRAPHQL_HINTS = ("graphql", "apollo", "relay", "urql")
GRAPHQL_QUERY_KEYS = {"query", "operationName", "variables", "extensions"}


def _canonical_endpoint(url: str) -> str:
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))


def detect_graphql(network_events: list[dict]) -> dict:
    endpoints: dict[str, dict] = {}
    for event in network_events:
        url = str(event.get("url") or "")
        if not url:
            continue
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query, keep_blank_values=True)
        lowered = url.lower()
        likely_graphql = any(hint in lowered for hint in GRAPHQL_HINTS)
        likely_graphql = likely_graphql or bool(GRAPHQL_QUERY_KEYS.intersection(query_params))
        if not likely_graphql:
            continue

        endpoint = _canonical_endpoint(url)
        item = endpoints.setdefault(
            endpoint,
            {
                "url": endpoint,
                "methods": set(),
                "statuses": set(),
                "operation_names": set(),
                "query_parameter_names": set(),
                "observations": 0,
            },
        )
        item["observations"] += 1
        if event.get("method"):
            item["methods"].add(str(event["method"]))
        if event.get("status") is not None:
            item["statuses"].add(int(event["status"]))
        item["query_parameter_names"].update(query_params.keys())
        for operation_name in query_params.get("operationName", []):
            if operation_name:
                item["operation_names"].add(operation_name[:500])

    normalized = []
    for item in endpoints.values():
        normalized.append(
            {
                "url": item["url"],
                "host": urlparse(item["url"]).netloc,
                "methods": sorted(item["methods"]),
                "statuses": sorted(item["statuses"]),
                "operation_names": sorted(item["operation_names"]),
                "query_parameter_names": sorted(item["query_parameter_names"]),
                "observations": item["observations"],
            }
        )
    return {
        "detected": bool(normalized),
        "endpoints": sorted(normalized, key=lambda item: item["url"]),
    }


def write_report(data: dict, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
