from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urljoin

import httpx

SOURCE_MAP_RE = re.compile(r"[#@]\s*sourceMappingURL\s*=\s*([^\s*]+)")


class SourceMapAnalyzer:
    def __init__(self, timeout: float = 20.0) -> None:
        self.timeout = timeout

    async def inspect(self, script_url: str, output: Path) -> dict:
        async with httpx.AsyncClient(follow_redirects=True, timeout=self.timeout) as client:
            js = await client.get(script_url)
            js.raise_for_status()
            matches = SOURCE_MAP_RE.findall(js.text)
            if not matches:
                return {"script": script_url, "published": False}

            map_url = urljoin(str(js.url), matches[-1])
            try:
                sm = await client.get(map_url)
                sm.raise_for_status()
            except Exception as exc:
                return {"script": script_url, "published": False, "map_url": map_url, "error": repr(exc)}

        output.mkdir(parents=True, exist_ok=True)
        safe_name = Path(map_url.split("?", 1)[0]).name or "source.map"
        path = output / safe_name
        path.write_bytes(sm.content)
        return {
            "script": script_url,
            "published": True,
            "map_url": map_url,
            "path": str(path),
            "bytes": len(sm.content),
        }
