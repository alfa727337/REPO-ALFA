from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse


def build_har(network_events: list[dict], target: str, output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    requests: dict[str, dict] = {}
    entries: list[dict] = []
    for event in network_events:
        url = event.get("url")
        if not url:
            continue
        if event.get("type") == "request":
            requests[url] = event
        elif event.get("type") == "response":
            req = requests.get(url, {})
            entries.append(
                {
                    "startedDateTime": None,
                    "time": 0,
                    "request": {
                        "method": req.get("method", "GET"),
                        "url": url,
                        "httpVersion": "HTTP/2",
                        "headers": [],
                        "queryString": [],
                        "cookies": [],
                        "headersSize": -1,
                        "bodySize": -1,
                    },
                    "response": {
                        "status": int(event.get("status") or 0),
                        "statusText": "",
                        "httpVersion": "HTTP/2",
                        "headers": [],
                        "cookies": [],
                        "content": {"size": 0, "mimeType": ""},
                        "redirectURL": "",
                        "headersSize": -1,
                        "bodySize": -1,
                    },
                    "cache": {},
                    "timings": {"send": 0, "wait": 0, "receive": 0},
                }
            )
    har = {
        "log": {
            "version": "1.2",
            "creator": {"name": "REPO ALFA", "version": "0.2"},
            "pages": [{"id": "page_1", "title": urlparse(target).netloc, "startedDateTime": None}],
            "entries": entries,
        }
    }
    output.write_text(json.dumps(har, ensure_ascii=False, indent=2), encoding="utf-8")
    return output
