from __future__ import annotations

from collections import Counter
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup


def _snapshot(html: str, base_url: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    tags = Counter(node.name for node in soup.find_all(True))
    links = {
        urljoin(base_url, node.get("href"))
        for node in soup.find_all("a", href=True)
        if node.get("href")
    }
    scripts = {
        urljoin(base_url, node.get("src"))
        for node in soup.find_all("script", src=True)
        if node.get("src")
    }
    styles = {
        urljoin(base_url, node.get("href"))
        for node in soup.find_all("link", href=True)
        if "stylesheet" in (node.get("rel") or [])
    }
    forms = []
    for form in soup.find_all("form"):
        forms.append(
            {
                "action": urljoin(base_url, form.get("action") or base_url),
                "method": (form.get("method") or "get").upper(),
                "fields": len(form.find_all(["input", "select", "textarea", "button"])),
            }
        )
    return {
        "tag_counts": dict(tags),
        "links": sorted(links),
        "scripts": sorted(scripts),
        "stylesheets": sorted(styles),
        "forms": forms,
        "text_length": len(soup.get_text(" ", strip=True)),
    }


def compare_static_and_rendered(static_html: str, rendered_html: str, base_url: str) -> dict:
    static = _snapshot(static_html, base_url)
    rendered = _snapshot(rendered_html, base_url)
    static_links = set(static["links"])
    rendered_links = set(rendered["links"])
    static_scripts = set(static["scripts"])
    rendered_scripts = set(rendered["scripts"])
    return {
        "static": static,
        "rendered": rendered,
        "delta": {
            "links_added_by_runtime": sorted(rendered_links - static_links),
            "links_removed_by_runtime": sorted(static_links - rendered_links),
            "scripts_added_by_runtime": sorted(rendered_scripts - static_scripts),
            "scripts_removed_by_runtime": sorted(static_scripts - rendered_scripts),
            "text_length_delta": rendered["text_length"] - static["text_length"],
        },
    }


def analyze_capture(root: Path, base_url: str) -> dict | None:
    static_path = root / "html" / "source.html"
    rendered_path = root / "dom" / "rendered.html"
    if not static_path.exists() or not rendered_path.exists():
        return None
    return compare_static_and_rendered(
        static_path.read_text(encoding="utf-8", errors="ignore"),
        rendered_path.read_text(encoding="utf-8", errors="ignore"),
        base_url,
    )
