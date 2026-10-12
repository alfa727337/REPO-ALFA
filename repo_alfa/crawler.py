from __future__ import annotations

from collections import deque
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup


class Crawler:
    def __init__(self, max_depth: int = 2, timeout: float = 20.0, same_origin_only: bool = True) -> None:
        self.max_depth = max_depth
        self.timeout = timeout
        self.same_origin_only = same_origin_only

    async def crawl(self, start_url: str) -> dict:
        origin = urlparse(start_url).netloc
        queue = deque([(start_url, 0)])
        visited: set[str] = set()
        discovered: set[str] = set()
        failures: dict[str, str] = {}

        async with httpx.AsyncClient(follow_redirects=True, timeout=self.timeout) as client:
            while queue:
                url, depth = queue.popleft()
                if url in visited or depth > self.max_depth:
                    continue
                visited.add(url)
                try:
                    response = await client.get(url)
                    if "text/html" not in response.headers.get("content-type", ""):
                        continue
                    soup = BeautifulSoup(response.text, "lxml")
                    for anchor in soup.find_all("a", href=True):
                        candidate = urljoin(str(response.url), anchor["href"]).split("#", 1)[0]
                        parsed = urlparse(candidate)
                        if parsed.scheme not in {"http", "https"}:
                            continue
                        if self.same_origin_only and parsed.netloc != origin:
                            continue
                        discovered.add(candidate)
                        if candidate not in visited and depth < self.max_depth:
                            queue.append((candidate, depth + 1))
                except Exception as exc:
                    failures[url] = repr(exc)

        return {
            "visited": sorted(visited),
            "discovered": sorted(discovered),
            "failures": failures,
        }
