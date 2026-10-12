from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from pathlib import Path
from urllib.parse import urljoin

URL_RE = re.compile(r"(?P<q>['\"])(?P<url>(?:https?:)?//[^'\"]+|/[^'\"]{1,300})(?P=q)")
IMPORT_RE = re.compile(r"(?:import\s+(?:[^;]+?\s+from\s+)?|require\()(?P<q>['\"])(?P<mod>[^'\"]+)(?P=q)")
DYNAMIC_IMPORT_RE = re.compile(r"import\(\s*['\"](?P<mod>[^'\"]+)['\"]\s*\)")
SOURCE_MAP_RE = re.compile(r"//#\s*sourceMappingURL=(?P<url>\S+)")
SECRET_HINT_RE = re.compile(r"(?i)(api[_-]?key|client[_-]?secret|access[_-]?token|authorization)\s*[:=]\s*['\"]([^'\"]{8,})['\"]")


@dataclass(slots=True)
class JavaScriptFinding:
    file: str
    imports: list[str]
    dynamic_imports: list[str]
    urls: list[str]
    source_maps: list[str]
    secret_hints: list[dict[str, str]]

    def to_dict(self) -> dict:
        return asdict(self)


def analyze_text(text: str, source_name: str = "<memory>", base_url: str | None = None) -> JavaScriptFinding:
    imports = sorted({m.group("mod") for m in IMPORT_RE.finditer(text)})
    dynamic = sorted({m.group("mod") for m in DYNAMIC_IMPORT_RE.finditer(text)})
    urls = {m.group("url") for m in URL_RE.finditer(text)}
    if base_url:
        urls = {urljoin(base_url, u) for u in urls}
    maps = [m.group("url") for m in SOURCE_MAP_RE.finditer(text)]
    hints = [
        {"kind": m.group(1), "value_preview": m.group(2)[:6] + "…"}
        for m in SECRET_HINT_RE.finditer(text)
    ]
    return JavaScriptFinding(
        file=source_name,
        imports=imports,
        dynamic_imports=dynamic,
        urls=sorted(urls),
        source_maps=sorted(set(maps)),
        secret_hints=hints,
    )


def analyze_directory(root: Path, base_url: str | None = None) -> list[dict]:
    findings: list[dict] = []
    if not root.exists():
        return findings
    for path in sorted(root.rglob("*")):
        if path.suffix.lower() not in {".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        findings.append(analyze_text(text, str(path), base_url).to_dict())
    return findings


def aggregate(findings: list[dict]) -> dict:
    imports: set[str] = set()
    dynamic: set[str] = set()
    urls: set[str] = set()
    maps: set[str] = set()
    hints: list[dict] = []
    for item in findings:
        imports.update(item.get("imports", []))
        dynamic.update(item.get("dynamic_imports", []))
        urls.update(item.get("urls", []))
        maps.update(item.get("source_maps", []))
        hints.extend(item.get("secret_hints", []))
    return {
        "files_analyzed": len(findings),
        "imports": sorted(imports),
        "dynamic_imports": sorted(dynamic),
        "urls": sorted(urls),
        "source_maps": sorted(maps),
        "secret_hints": hints,
    }
