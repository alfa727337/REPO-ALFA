from __future__ import annotations

import hashlib
import json
import mimetypes
from pathlib import Path
from urllib.parse import urlparse

import httpx


class AssetDownloader:
    def __init__(self, timeout: float = 30.0, max_bytes: int = 25_000_000) -> None:
        self.timeout = timeout
        self.max_bytes = max_bytes

    async def download_many(self, urls: list[str], output: Path) -> list[dict]:
        output.mkdir(parents=True, exist_ok=True)
        results: list[dict] = []
        async with httpx.AsyncClient(follow_redirects=True, timeout=self.timeout) as client:
            for url in sorted(set(urls)):
                try:
                    response = await client.get(url)
                    response.raise_for_status()
                    body = response.content
                    if len(body) > self.max_bytes:
                        results.append({"url": url, "status": "skipped", "reason": "max_bytes"})
                        continue
                    path = self._path_for(url, response.headers.get("content-type"), output)
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(body)
                    results.append(
                        {
                            "url": url,
                            "status": "saved",
                            "path": str(path),
                            "relative_path": str(path.relative_to(output.parent)),
                            "sha256": hashlib.sha256(body).hexdigest(),
                            "bytes": len(body),
                            "content_type": response.headers.get("content-type"),
                        }
                    )
                except Exception as exc:
                    results.append({"url": url, "status": "failed", "error": repr(exc)})

        manifest = {
            item["url"]: item["relative_path"]
            for item in results
            if item.get("status") == "saved" and item.get("relative_path")
        }
        (output / "manifest.json").write_text(
            json.dumps(
                {"assets": results, "url_to_local": manifest},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return results

    def _path_for(self, url: str, content_type: str | None, root: Path) -> Path:
        parsed = urlparse(url)
        name = Path(parsed.path).name or "index"
        if "." not in name and content_type:
            ext = mimetypes.guess_extension(content_type.split(";", 1)[0].strip()) or ""
            name += ext
        digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]
        safe_host = parsed.netloc.replace(":", "_") or "unknown-host"
        return root / safe_host / f"{digest}-{name}"
