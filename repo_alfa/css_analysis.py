from __future__ import annotations

import re
from pathlib import Path

CUSTOM_PROPERTY_RE = re.compile(r"(?P<name>--[A-Za-z0-9_-]+)\s*:\s*(?P<value>[^;}]+)")
FONT_FACE_RE = re.compile(r"@font-face\s*\{(?P<body>.*?)\}", re.IGNORECASE | re.DOTALL)
FONT_FAMILY_RE = re.compile(r"font-family\s*:\s*(?P<value>[^;}]+)", re.IGNORECASE)
MEDIA_RE = re.compile(r"@media\s*(?P<query>[^\{]+)\{", re.IGNORECASE)
URL_RE = re.compile(r"url\(\s*['\"]?(?P<url>[^)'\"]+)['\"]?\s*\)", re.IGNORECASE)
KEYFRAMES_RE = re.compile(r"@(?:-webkit-)?keyframes\s+(?P<name>[A-Za-z0-9_-]+)", re.IGNORECASE)


def analyze_css_text(text: str, source: str = "<memory>") -> dict:
    properties = {}
    for match in CUSTOM_PROPERTY_RE.finditer(text):
        properties[match.group("name")] = match.group("value").strip()
    font_faces = []
    for match in FONT_FACE_RE.finditer(text):
        body = match.group("body")
        families = [m.group("value").strip() for m in FONT_FAMILY_RE.finditer(body)]
        urls = [m.group("url") for m in URL_RE.finditer(body)]
        font_faces.append({"families": families, "urls": urls})
    return {
        "source": source,
        "custom_properties": properties,
        "font_faces": font_faces,
        "font_families": sorted({m.group("value").strip() for m in FONT_FAMILY_RE.finditer(text)}),
        "media_queries": sorted({m.group("query").strip() for m in MEDIA_RE.finditer(text)}),
        "urls": sorted({m.group("url") for m in URL_RE.finditer(text)}),
        "keyframes": sorted({m.group("name") for m in KEYFRAMES_RE.finditer(text)}),
    }


def analyze_directory(root: Path) -> dict:
    files: list[dict] = []
    all_props: dict[str, str] = {}
    all_fonts: set[str] = set()
    all_media: set[str] = set()
    all_urls: set[str] = set()
    all_keyframes: set[str] = set()
    if not root.exists():
        return {
            "files": [], "custom_properties": {}, "font_families": [],
            "media_queries": [], "urls": [], "keyframes": []
        }
    for path in sorted(root.rglob("*.css")):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        result = analyze_css_text(text, str(path))
        files.append(result)
        all_props.update(result["custom_properties"])
        all_fonts.update(result["font_families"])
        all_media.update(result["media_queries"])
        all_urls.update(result["urls"])
        all_keyframes.update(result["keyframes"])
    return {
        "files": files,
        "custom_properties": all_props,
        "font_families": sorted(all_fonts),
        "media_queries": sorted(all_media),
        "urls": sorted(all_urls),
        "keyframes": sorted(all_keyframes),
    }
