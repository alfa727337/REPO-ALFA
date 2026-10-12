from __future__ import annotations

from collections import deque
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import httpx
from bs4 import BeautifulSoup

TRACKING_QUERY_PREFIXES = ("utm_", "fbclid", "gclid", "mc_", "ref_")


def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith(TRACKING_QUERY_PREFIXES)
    ]
    query.sort()
    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    return urlunparse(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            path,
            "",
            urlencode(query, doseq=True),
            "",
        )
    )


class Crawler:
    def __init__(
        self,
        max_depth: int = 2,
        timeout: float = 20.0,
        same_origin_only: bool = True,
        max_pages: int = 1000,
        max_links_per_page: int = 5000,
    ) -> None:
        self.max_depth = max_depth
        self.timeout = timeout
        self.same_origin_only = same_origin_only
        self.max_pages = max_pages
        self.max_links_per_page = max_links_per_page

    async def crawl(self, start_url: str) -> dict:
        start = normalize_url(start_url)
        origin = urlparse(start).netloc
        queue = deque([(start, 0)])
        queued = {start}
        visited: set[str] = set()
        discovered: set[str] = set()
        failures: dict[str, str] = {}
        pages: list[dict] = []
        edges: list[dict] = []

        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=self.timeout,
            headers={"User-Agent": "REPO-ALFA/0.2 (+authorized-web-analysis)"},
        ) as client:
            while queue and len(visited) < self.max_pages:
                url, depth = queue.popleft()
                if url in visited or depth > self.max_depth:
                    continue
                visited.add(url)
                try:
                    response = await client.get(url)
                    final_url = normalize_url(str(response.url))
                    content_type = response.headers.get("content-type", "")
                    page_record = {
                        "requested_url": url,
                        "final_url": final_url,
                        "depth": depth,
                        "status": response.status_code,
                        "content_type": content_type,
                        "bytes": len(response.content),
                    }
                    pages.append(page_record)
                    if "text/html" not in content_type.lower():
                        continue

                    soup = BeautifulSoup(response.text, "lxml")
                    seen_on_page: set[str] = set()
                    for anchor in soup.find_all("a", href=True)[: self.max_links_per_page]:
                        raw = anchor.get("href")
                        if not isinstance(raw, str) or not raw.strip():
                            continue
                        candidate = normalize_url(urljoin(final_url, raw))
                        parsed = urlparse(candidate)
                        if parsed.scheme not in {"http", "https"}:
                            continue
                        if self.same_origin_only and parsed.netloc != origin:
                            continue
                        if candidate in seen_on_page:
                            continue
                        seen_on_page.add(candidate)
                        discovered.add(candidate)
                        edges.append({"from": final_url, "to": candidate, "depth": depth + 1})
                        if (
                            candidate not in visited
                            and candidate not in queued
                            and depth < self.max_depth
                            and len(visited) + len(queue) < self.max_pages
                        ):
                            queue.append((candidate, depth + 1))
                            queued.add(candidate)
                except (httpx.HTTPError, OSError, ValueError) as exc:
                    failures[url] = repr(exc)

        return {
            "start_url": start,
            "visited": sorted(visited),
            "discovered": sorted(discovered),
            "failures": failures,
            "pages": pages,
            "edges": edges,
            "limits": {
                "max_depth": self.max_depth,
                "max_pages": self.max_pages,
                "max_links_per_page": self.max_links_per_page,
            },
            "truncated": bool(queue),
        }
