from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup

CSS_URL_RE = re.compile(r"url\((?P<q>['\"]?)(?P<url>[^)'\"]+)(?P=q)\)")


class ReconstructionEngine:
    """Build a local preview from frontend artifacts already captured by REPO ALFA.

    The engine rewrites references only to resources that were actually captured.
    It never fabricates private server behavior or bypasses authentication.
    """

    def _load_manifest(self, capture_root: Path) -> dict[str, str]:
        manifest_path = capture_root / "assets" / "manifest.json"
        if not manifest_path.exists():
            return {}
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        return dict(data.get("url_to_local", {}))

    def _rewrite_html(self, html: str, base_url: str, mapping: dict[str, str]) -> str:
        soup = BeautifulSoup(html, "lxml")
        attrs = ("src", "href", "poster", "data-src")
        for node in soup.find_all(True):
            for attr in attrs:
                raw = node.get(attr)
                if not isinstance(raw, str) or not raw:
                    continue
                absolute = urljoin(base_url, raw)
                local = mapping.get(absolute)
                if local:
                    node[attr] = local.replace("\\", "/")

            srcset = node.get("srcset")
            if isinstance(srcset, str):
                rewritten: list[str] = []
                for part in srcset.split(","):
                    fields = part.strip().split()
                    if not fields:
                        continue
                    absolute = urljoin(base_url, fields[0])
                    fields[0] = mapping.get(absolute, fields[0]).replace("\\", "/")
                    rewritten.append(" ".join(fields))
                node["srcset"] = ", ".join(rewritten)

            style = node.get("style")
            if isinstance(style, str) and "url(" in style:
                def replace(match: re.Match[str]) -> str:
                    raw = match.group("url")
                    absolute = urljoin(base_url, raw)
                    local = mapping.get(absolute)
                    return f"url('{local.replace('\\', '/') if local else raw}')"
                node["style"] = CSS_URL_RE.sub(replace, style)

        return str(soup)

    def reconstruct(
        self,
        capture_root: Path,
        destination: Path,
        base_url: str | None = None,
    ) -> dict:
        destination.mkdir(parents=True, exist_ok=True)
        source = capture_root / "dom" / "rendered.html"
        if not source.exists():
            source = capture_root / "html" / "source.html"
        if not source.exists():
            raise FileNotFoundError("no captured HTML/DOM found")

        mapping = self._load_manifest(capture_root)
        if base_url is None:
            report_path = capture_root / "full-report.json"
            if report_path.exists():
                base_url = json.loads(report_path.read_text(encoding="utf-8")).get("target")
        base_url = base_url or "http://localhost/"

        copied: list[str] = []
        for directory in ("assets", "css", "javascript", "fonts", "images", "svg"):
            src = capture_root / directory
            if not src.exists() or not src.is_dir():
                continue
            dst = destination / directory
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            copied.append(str(dst))

        rewritten = self._rewrite_html(
            source.read_text(encoding="utf-8", errors="ignore"),
            base_url,
            mapping,
        )
        index = destination / "index.html"
        index.write_text(rewritten, encoding="utf-8")
        copied.insert(0, str(index))

        serve = destination / "serve.py"
        serve.write_text(
            "from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler\n"
            "ThreadingHTTPServer(('127.0.0.1', 8000), SimpleHTTPRequestHandler).serve_forever()\n",
            encoding="utf-8",
        )
        metadata = {
            "entrypoint": str(index),
            "copied": copied,
            "rewritten_assets": len(mapping),
            "base_url": base_url,
            "serve_command": "python serve.py",
            "scope": "captured observable frontend artifacts only",
        }
        (destination / "reconstruction.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return metadata
