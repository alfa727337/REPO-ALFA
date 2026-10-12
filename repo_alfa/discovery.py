from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET

import httpx


class PublicDiscovery:
    def __init__(self, timeout: float = 20.0, max_sitemaps: int = 20, max_urls: int = 5000) -> None:
        self.timeout = timeout
        self.max_sitemaps = max_sitemaps
        self.max_urls = max_urls

    async def discover(self, target: str, output: Path) -> dict:
        parsed = urlparse(target)
        origin = f"{parsed.scheme}://{parsed.netloc}/"
        robots_url = urljoin(origin, "robots.txt")
        robots_text = ""
        sitemap_urls: list[str] = []
        discovered: set[str] = set()
        failures: list[dict] = []

        async with httpx.AsyncClient(follow_redirects=True, timeout=self.timeout) as client:
            try:
                robots = await client.get(robots_url)
                if robots.status_code < 400:
                    robots_text = robots.text
                    for line in robots_text.splitlines():
                        if line.lower().startswith("sitemap:"):
                            sitemap_urls.append(line.split(":", 1)[1].strip())
            except Exception as exc:
                failures.append({"url": robots_url, "error": repr(exc)})

            if not sitemap_urls:
                sitemap_urls = [urljoin(origin, "sitemap.xml")]

            queue = list(dict.fromkeys(sitemap_urls))[: self.max_sitemaps]
            seen_sitemaps: set[str] = set()
            while queue and len(seen_sitemaps) < self.max_sitemaps and len(discovered) < self.max_urls:
                sitemap_url = queue.pop(0)
                if sitemap_url in seen_sitemaps:
                    continue
                seen_sitemaps.add(sitemap_url)
                try:
                    response = await client.get(sitemap_url)
                    if response.status_code >= 400:
                        failures.append({"url": sitemap_url, "status": response.status_code})
                        continue
                    root = ET.fromstring(response.content)
                    locations = [
                        node.text.strip()
                        for node in root.iter()
                        if node.tag.endswith("loc") and node.text
                    ]
                    if root.tag.endswith("sitemapindex"):
                        for loc in locations:
                            if len(seen_sitemaps) + len(queue) >= self.max_sitemaps:
                                break
                            queue.append(loc)
                    else:
                        for loc in locations:
                            if len(discovered) >= self.max_urls:
                                break
                            if urlparse(loc).netloc == parsed.netloc:
                                discovered.add(loc)
                except Exception as exc:
                    failures.append({"url": sitemap_url, "error": repr(exc)})

        output.mkdir(parents=True, exist_ok=True)
        if robots_text:
            (output / "robots.txt").write_text(robots_text, encoding="utf-8", errors="ignore")
        result = {
            "robots_url": robots_url,
            "robots_found": bool(robots_text),
            "sitemaps": sorted(seen_sitemaps),
            "urls": sorted(discovered),
            "failures": failures,
        }
        (output / "discovery.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return result
