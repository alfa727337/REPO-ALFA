from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urljoin

from .ast_bridge import analyze_with_babel, ast_available

URL_RE = re.compile(r"(?P<q>['\"])(?P<url>(?:https?:)?//[^'\"]+|/[^'\"]{1,300})(?P=q)")
IMPORT_RE = re.compile(
    r"(?:import\s+(?:[^;]+?\s+from\s+)?|require\()(?P<q>['\"])(?P<mod>[^'\"]+)(?P=q)"
)
DYNAMIC_IMPORT_RE = re.compile(r"import\(\s*['\"](?P<mod>[^'\"]+)['\"]\s*\)")
SOURCE_MAP_RE = re.compile(r"//#\s*sourceMappingURL=(?P<url>\S+)")
SECRET_HINT_RE = re.compile(
    r"(?i)(api[_-]?key|client[_-]?secret|access[_-]?token|authorization)\s*[:=]\s*['\"]([^'\"]{8,})['\"]"
)


@dataclass(slots=True)
class JavaScriptFinding:
    file: str
    imports: list[str]
    dynamic_imports: list[str]
    urls: list[str]
    source_maps: list[str]
    secret_hints: list[dict[str, str | int]]

    def to_dict(self) -> dict:
        return asdict(self)


def _secret_fingerprint(kind: str, value: str) -> dict[str, str | int]:
    return {
        "kind": kind,
        "length": len(value),
        "sha256": hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest(),
    }


def analyze_text(
    text: str,
    source_name: str = "<memory>",
    base_url: str | None = None,
) -> JavaScriptFinding:
    imports = sorted({m.group("mod") for m in IMPORT_RE.finditer(text)})
    dynamic = sorted({m.group("mod") for m in DYNAMIC_IMPORT_RE.finditer(text)})
    urls = {m.group("url") for m in URL_RE.finditer(text)}
    if base_url:
        urls = {urljoin(base_url, u) for u in urls}
    maps = [m.group("url") for m in SOURCE_MAP_RE.finditer(text)]
    hints = [
        _secret_fingerprint(m.group(1), m.group(2))
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


def analyze_directory(
    root: Path,
    base_url: str | None = None,
    ast_limit: int = 100,
) -> list[dict]:
    findings: list[dict] = []
    if not root.exists():
        return findings
    use_ast = ast_available()
    ast_count = 0
    for path in sorted(root.rglob("*")):
        if path.suffix.lower() not in {".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        item = analyze_text(text, str(path), base_url).to_dict()
        if use_ast and ast_count < ast_limit:
            item["ast"] = analyze_with_babel(path)
            ast_count += 1
        else:
            item["ast"] = {
                "available": use_ast,
                "skipped": True,
                "reason": "ast-limit" if use_ast else "optional-babel-toolchain-not-installed",
            }
        findings.append(item)
    return findings


def aggregate(findings: list[dict]) -> dict:
    imports: set[str] = set()
    dynamic: set[str] = set()
    urls: set[str] = set()
    maps: set[str] = set()
    hints: list[dict] = []
    ast_parsed = 0
    ast_available_count = 0
    ast_imports: set[str] = set()
    ast_fetches: set[str] = set()
    ast_websockets: set[str] = set()
    for item in findings:
        imports.update(item.get("imports", []))
        dynamic.update(item.get("dynamic_imports", []))
        urls.update(item.get("urls", []))
        maps.update(item.get("source_maps", []))
        hints.extend(item.get("secret_hints", []))
        ast = item.get("ast") or {}
        if ast.get("available"):
            ast_available_count += 1
        if ast.get("parsed"):
            ast_parsed += 1
            ast_imports.update(ast.get("imports", []))
            ast_imports.update(ast.get("requires", []))
            ast_fetches.update(ast.get("fetchCalls", []))
            ast_websockets.update(ast.get("websocketConstructors", []))
    return {
        "files_analyzed": len(findings),
        "imports": sorted(imports),
        "dynamic_imports": sorted(dynamic),
        "urls": sorted(urls),
        "source_maps": sorted(maps),
        "secret_hints": hints,
        "ast": {
            "available_files": ast_available_count,
            "parsed_files": ast_parsed,
            "imports": sorted(ast_imports),
            "fetch_calls": sorted(ast_fetches),
            "websocket_constructors": sorted(ast_websockets),
        },
    }
