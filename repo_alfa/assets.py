from __future__ import annotations

import hashlib
import json
import mimetypes
import re
from collections import deque
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx

CSS_URL_RE = re.compile(r"url\(\s*['\"]?(?P<url>[^)'\"\s]+)['\"]?\s*\)", re.IGNORECASE)
CSS_IMPORT_RE = re.compile(
    r"@import\s+(?:url\()?\s*['\"]?(?P<url>[^)'\"\s;]+)", re.IGNORECASE
)
JS_DYNAMIC_RE = re.compile(r"import\(\s*['\"](?P<url>[^'\"]+)['\"]\s*\)")
JS_STATIC_ASSET_RE = re.compile(
    r"['\"](?P<url>[^'\"]+\.(?:js|mjs|css|png|jpe?g|gif|webp|svg|woff2?|ttf|otf|ico|map)(?:\?[^'\"]*)?)['\"]",
    re.IGNORECASE,
)
TEXT_TYPES = ("text/css", "javascript", "ecmascript", "application/json")


class AssetDownloader:
    def __init__(
        self,
        timeout: float = 30.0,
        max_bytes: int = 25_000_000,
        nested_depth: int = 2,
        max_assets: int = 5000,
    ) -> None:
        self.timeout = timeout
        self.max_bytes = max_bytes
        self.nested_depth = nested_depth
        self.max_assets = max_assets

    async def download_many(self, urls: list[str], output: Path) -> list[dict]:
        output.mkdir(parents=True, exist_ok=True)
        queue = deque((url, 0, None) for url in sorted(set(urls)))
        queued = {url for url in urls}
        processed: set[str] = set()
        results: list[dict] = []

        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=self.timeout,
            headers={"User-Agent": "REPO-ALFA/0.2 (+authorized-web-analysis)"},
        ) as client:
            while queue and len(processed) < self.max_assets:
                url, depth, discovered_from = queue.popleft()
                if url in processed:
                    continue
                processed.add(url)
                try:
                    response = await client.get(url)
                    response.raise_for_status()
                    body = response.content
                    if len(body) > self.max_bytes:
                        results.append(
                            {
                                "url": url,
                                "status": "skipped",
                                "reason": "max_bytes",
                                "bytes": len(body),
                                "depth": depth,
                                "discovered_from": discovered_from,
                            }
                        )
                        continue

                    content_type = response.headers.get("content-type")
                    final_url = str(response.url)
                    path = self._path_for(final_url, content_type, output)
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(body)
                    result = {
                        "url": url,
                        "final_url": final_url,
                        "status": "saved",
                        "path": str(path),
                        "relative_path": str(path.relative_to(output.parent)),
                        "sha256": hashlib.sha256(body).hexdigest(),
                        "bytes": len(body),
                        "content_type": content_type,
                        "depth": depth,
                        "discovered_from": discovered_from,
                    }
                    results.append(result)

                    if depth >= self.nested_depth:
                        continue
                    for nested in self._discover_nested(final_url, body, content_type, path.suffix):
                        if nested in queued or nested in processed:
                            continue
                        if len(queued) >= self.max_assets * 2:
                            break
                        queued.add(nested)
                        queue.append((nested, depth + 1, final_url))
                except (httpx.HTTPError, OSError, ValueError) as exc:
                    results.append(
                        {
                            "url": url,
                            "status": "failed",
                            "error": repr(exc),
                            "depth": depth,
                            "discovered_from": discovered_from,
                        }
                    )

        manifest = {
            item.get("final_url") or item["url"]: item["relative_path"]
            for item in results
            if item.get("status") == "saved" and item.get("relative_path")
        }
        for item in results:
            if item.get("status") == "saved" and item.get("relative_path"):
                manifest.setdefault(item["url"], item["relative_path"])

        (output / "manifest.json").write_text(
            json.dumps(
                {
                    "assets": results,
                    "url_to_local": manifest,
                    "processed": len(processed),
                    "truncated": bool(queue),
                    "nested_depth": self.nested_depth,
                    "max_assets": self.max_assets,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return results

    def _discover_nested(
        self,
        base_url: str,
        body: bytes,
        content_type: str | None,
        suffix: str,
    ) -> list[str]:
        kind = (content_type or "").lower()
        suffix = suffix.lower()
        is_css = "text/css" in kind or suffix == ".css"
        is_js = "javascript" in kind or "ecmascript" in kind or suffix in {".js", ".mjs", ".cjs"}
        if not (is_css or is_js):
            return []
        try:
            text = body.decode("utf-8", errors="ignore")
        except Exception:
            return []

        raw_urls: set[str] = set()
        if is_css:
            raw_urls.update(match.group("url") for match in CSS_URL_RE.finditer(text))
            raw_urls.update(match.group("url") for match in CSS_IMPORT_RE.finditer(text))
        if is_js:
            raw_urls.update(match.group("url") for match in JS_DYNAMIC_RE.finditer(text))
            raw_urls.update(match.group("url") for match in JS_STATIC_ASSET_RE.finditer(text))

        resolved: set[str] = set()
        for raw in raw_urls:
            raw = raw.strip()
            if not raw or raw.startswith(("data:", "blob:", "javascript:", "#")):
                continue
            absolute = urljoin(base_url, raw)
            parsed = urlparse(absolute)
            if parsed.scheme in {"http", "https"}:
                resolved.add(absolute)
        return sorted(resolved)

    def _path_for(self, url: str, content_type: str | None, root: Path) -> Path:
        parsed = urlparse(url)
        name = Path(parsed.path).name or "index"
        if "." not in name and content_type:
            ext = mimetypes.guess_extension(content_type.split(";", 1)[0].strip()) or ""
            name += ext
        digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]
        safe_host = parsed.netloc.replace(":", "_") or "unknown-host"
        return root / safe_host / f"{digest}-{name}"
