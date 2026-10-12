from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urljoin

import httpx

SOURCE_MAP_RE = re.compile(r"[#@]\s*sourceMappingURL\s*=\s*([^\s*]+)")


def _safe_source_path(source: str, root: Path) -> Path:
    cleaned = source.replace("\\", "/").lstrip("/")
    parts = [part for part in cleaned.split("/") if part not in {"", ".", ".."}]
    if not parts:
        parts = [hashlib.sha1(source.encode("utf-8")).hexdigest() + ".txt"]
    return root.joinpath(*parts)


class SourceMapAnalyzer:
    def __init__(self, timeout: float = 20.0, max_bytes: int = 50_000_000) -> None:
        self.timeout = timeout
        self.max_bytes = max_bytes

    async def inspect(self, script_url: str, output: Path) -> dict:
        async with httpx.AsyncClient(follow_redirects=True, timeout=self.timeout) as client:
            js = await client.get(script_url)
            js.raise_for_status()
            matches = SOURCE_MAP_RE.findall(js.text)
            if not matches:
                return {"script": script_url, "published": False}

            map_url = urljoin(str(js.url), matches[-1].strip())
            try:
                sm = await client.get(map_url)
                sm.raise_for_status()
            except Exception as exc:
                return {
                    "script": script_url,
                    "published": False,
                    "map_url": map_url,
                    "error": repr(exc),
                }

        if len(sm.content) > self.max_bytes:
            return {
                "script": script_url,
                "published": True,
                "map_url": map_url,
                "saved": False,
                "reason": "max_bytes",
                "bytes": len(sm.content),
            }

        output.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha1(map_url.encode("utf-8")).hexdigest()[:12]
        safe_name = Path(map_url.split("?", 1)[0]).name or "source.map"
        path = output / f"{digest}-{safe_name}"
        path.write_bytes(sm.content)

        parsed = None
        sources: list[str] = []
        extracted: list[str] = []
        try:
            parsed = sm.json()
            sources = [str(item) for item in parsed.get("sources", [])]
            contents = parsed.get("sourcesContent") or []
            source_root = output / "sources" / digest
            for index, source in enumerate(sources):
                if index >= len(contents) or contents[index] is None:
                    continue
                destination = _safe_source_path(source, source_root)
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(str(contents[index]), encoding="utf-8", errors="ignore")
                extracted.append(str(destination))
        except (ValueError, TypeError, json.JSONDecodeError):
            parsed = None

        return {
            "script": script_url,
            "published": True,
            "map_url": map_url,
            "path": str(path),
            "bytes": len(sm.content),
            "version": parsed.get("version") if isinstance(parsed, dict) else None,
            "sources": sources,
            "sources_count": len(sources),
            "sources_content_extracted": len(extracted),
            "extracted_paths": extracted,
        }
