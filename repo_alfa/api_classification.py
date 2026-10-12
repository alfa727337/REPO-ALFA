from __future__ import annotations

from collections import Counter
from urllib.parse import urlparse

STATIC_EXTENSIONS = {
    ".js", ".mjs", ".css", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg",
    ".woff", ".woff2", ".ttf", ".ico", ".map", ".mp4", ".webm", ".json",
}


def classify_url(url: str, resource_type: str | None = None) -> str:
    parsed = urlparse(url)
    path = parsed.path.lower()
    if parsed.scheme in {"ws", "wss"}:
        return "websocket"
    if "graphql" in path:
        return "graphql"
    if any(path.endswith(ext) for ext in STATIC_EXTENSIONS):
        return "static"
    if resource_type in {"xhr", "fetch"}:
        return "api"
    if "/api/" in path or path.startswith("/api"):
        return "api"
    return "document-or-other"


def summarize_network(events: list[dict]) -> dict:
    requests = [item for item in events if item.get("type") == "request"]
    classified: list[dict] = []
    counts: Counter[str] = Counter()
    hosts: Counter[str] = Counter()
    methods: Counter[str] = Counter()
    for item in requests:
        url = str(item.get("url") or "")
        if not url:
            continue
        category = classify_url(url, item.get("resource_type"))
        counts[category] += 1
        hosts[urlparse(url).netloc] += 1
        methods[str(item.get("method") or "GET")] += 1
        classified.append({
            "url": url,
            "method": item.get("method"),
            "resource_type": item.get("resource_type"),
            "category": category,
        })
    return {
        "counts": dict(counts),
        "hosts": dict(hosts.most_common()),
        "methods": dict(methods),
        "requests": classified,
    }
