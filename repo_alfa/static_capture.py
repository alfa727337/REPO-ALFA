from __future__ import annotations

from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup


class StaticCapture:
    def __init__(self, timeout: float = 30.0) -> None:
        self.timeout = timeout

    async def fetch(self, url: str, output: Path) -> dict:
        output.mkdir(parents=True, exist_ok=True)
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=self.timeout,
            headers={"User-Agent": "REPO-ALFA/0.1 (+authorized-web-analysis)"},
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

        html = response.text
        (output / "html").mkdir(exist_ok=True)
        (output / "html" / "source.html").write_text(html, encoding="utf-8")

        soup = BeautifulSoup(html, "lxml")
        base_host = urlparse(str(response.url)).netloc
        links: set[str] = set()
        assets: set[str] = set()

        for tag in soup.find_all(["a", "link", "script", "img", "source"]):
            raw = tag.get("href") or tag.get("src")
            if not raw:
                continue
            absolute = urljoin(str(response.url), raw)
            parsed = urlparse(absolute)
            if parsed.scheme not in {"http", "https"}:
                continue
            if tag.name == "a" and parsed.netloc == base_host:
                links.add(absolute.split("#", 1)[0])
            else:
                assets.add(absolute)

        headers = dict(response.headers)
        return {
            "url": str(response.url),
            "status_code": response.status_code,
            "headers": headers,
            "links": sorted(links),
            "assets": sorted(assets),
            "title": soup.title.string.strip() if soup.title and soup.title.string else None,
        }
