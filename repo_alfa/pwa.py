from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse

import httpx


class PWAAnalyzer:
    def __init__(self, timeout: float = 20.0, max_bytes: int = 5_000_000) -> None:
        self.timeout = timeout
        self.max_bytes = max_bytes

    async def analyze(
        self,
        manifest_url: str | None,
        service_workers: list[dict],
        output: Path,
    ) -> dict:
        output.mkdir(parents=True, exist_ok=True)
        result: dict = {"manifest": None, "service_workers": []}
        async with httpx.AsyncClient(follow_redirects=True, timeout=self.timeout) as client:
            if manifest_url:
                try:
                    response = await client.get(manifest_url)
                    response.raise_for_status()
                    if len(response.content) <= self.max_bytes:
                        path = output / "manifest.json"
                        path.write_bytes(response.content)
                        try:
                            parsed = response.json()
                        except ValueError:
                            parsed = None
                        result["manifest"] = {
                            "url": str(response.url),
                            "path": str(path),
                            "bytes": len(response.content),
                            "sha256": hashlib.sha256(response.content).hexdigest(),
                            "parsed": parsed,
                        }
                except Exception as exc:
                    result["manifest"] = {"url": manifest_url, "error": repr(exc)}

            for item in service_workers:
                script_url = item.get("scriptURL")
                if not script_url:
                    continue
                record = {"scope": item.get("scope"), "script_url": script_url}
                try:
                    response = await client.get(script_url)
                    response.raise_for_status()
                    if len(response.content) <= self.max_bytes:
                        name = Path(urlparse(script_url).path).name or "service-worker.js"
                        digest = hashlib.sha1(script_url.encode("utf-8")).hexdigest()[:12]
                        path = output / "service-workers" / f"{digest}-{name}"
                        path.parent.mkdir(parents=True, exist_ok=True)
                        path.write_bytes(response.content)
                        record.update(
                            {
                                "path": str(path),
                                "bytes": len(response.content),
                                "sha256": hashlib.sha256(response.content).hexdigest(),
                                "content_type": response.headers.get("content-type"),
                            }
                        )
                except Exception as exc:
                    record["error"] = repr(exc)
                result["service_workers"].append(record)

        (output / "pwa-analysis.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return result
