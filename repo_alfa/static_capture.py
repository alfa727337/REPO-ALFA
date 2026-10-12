from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

SENSITIVE_HEADERS = {"set-cookie", "authorization", "proxy-authorization"}


def _safe_headers(headers: httpx.Headers) -> dict[str, str]:
    result: dict[str, str] = {}
    for key, value in headers.items():
        result[key] = "<redacted>" if key.lower() in SENSITIVE_HEADERS else value
    return result


class StaticCapture:
    def __init__(self, timeout: float = 30.0) -> None:
        self.timeout = timeout

    async def fetch(self, url: str, output: Path) -> dict:
        output.mkdir(parents=True, exist_ok=True)
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=self.timeout,
            headers={"User-Agent": "REPO-ALFA/0.2 (+authorized-web-analysis)"},
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

        html = response.text
        (output / "html").mkdir(exist_ok=True)
        (output / "html" / "source.html").write_text(html, encoding="utf-8")

        soup = BeautifulSoup(html, "lxml")
        base_url = str(response.url)
        base_host = urlparse(base_url).netloc
        links: set[str] = set()
        assets: set[str] = set()
        forms: list[dict] = []

        for tag in soup.find_all(["a", "link", "script", "img", "source", "video", "audio"]):
            raw = tag.get("href") or tag.get("src") or tag.get("poster")
            if not raw:
                continue
            absolute = urljoin(base_url, raw)
            parsed = urlparse(absolute)
            if parsed.scheme not in {"http", "https"}:
                continue
            if tag.name == "a" and parsed.netloc == base_host:
                links.add(absolute.split("#", 1)[0])
            else:
                assets.add(absolute)

        for form in soup.find_all("form"):
            fields = []
            for field in form.find_all(["input", "select", "textarea", "button"]):
                fields.append(
                    {
                        "tag": field.name,
                        "name": field.get("name"),
                        "type": field.get("type"),
                        "required": field.has_attr("required"),
                        "autocomplete": field.get("autocomplete"),
                    }
                )
            forms.append(
                {
                    "action": urljoin(base_url, form.get("action") or base_url),
                    "method": (form.get("method") or "get").upper(),
                    "fields": fields,
                }
            )

        meta = {
            "title": soup.title.string.strip() if soup.title and soup.title.string else None,
            "canonical": None,
            "manifest": None,
            "generator": None,
            "forms": forms,
        }
        canonical = soup.find("link", rel=lambda value: value and "canonical" in value)
        if canonical and canonical.get("href"):
            meta["canonical"] = urljoin(base_url, canonical.get("href"))
        manifest = soup.find("link", rel=lambda value: value and "manifest" in value)
        if manifest and manifest.get("href"):
            meta["manifest"] = urljoin(base_url, manifest.get("href"))
        generator = soup.find("meta", attrs={"name": "generator"})
        if generator:
            meta["generator"] = generator.get("content")

        headers = _safe_headers(response.headers)
        (output / "headers").mkdir(exist_ok=True)
        (output / "headers" / "initial-response.json").write_text(
            json.dumps(headers, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (output / "html" / "metadata.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        return {
            "url": base_url,
            "status_code": response.status_code,
            "headers": headers,
            "links": sorted(links),
            "assets": sorted(assets),
            "title": meta["title"],
            "canonical": meta["canonical"],
            "manifest": meta["manifest"],
            "generator": meta["generator"],
            "forms": forms,
        }
