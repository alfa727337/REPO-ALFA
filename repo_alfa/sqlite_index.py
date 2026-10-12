from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS artifacts(
    path TEXT PRIMARY KEY,
    kind TEXT,
    size INTEGER,
    sha256 TEXT
);
CREATE TABLE IF NOT EXISTS routes(url TEXT PRIMARY KEY);
CREATE TABLE IF NOT EXISTS endpoints(url TEXT PRIMARY KEY, kind TEXT);
CREATE TABLE IF NOT EXISTS technologies(name TEXT PRIMARY KEY);
CREATE TABLE IF NOT EXISTS frameworks(
    name TEXT PRIMARY KEY,
    confidence REAL,
    evidence_json TEXT,
    details_json TEXT
);
CREATE TABLE IF NOT EXISTS modules(
    name TEXT,
    status TEXT,
    recovered_failures INTEGER,
    errors_json TEXT
);
CREATE TABLE IF NOT EXISTS coverage(
    layer TEXT PRIMARY KEY,
    status TEXT,
    reason TEXT
);
CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY, value TEXT);
"""


def _sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError:
        return None
    return digest.hexdigest()


def _artifact_kind(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".html", ".htm"}:
        return "html"
    if suffix in {".js", ".mjs", ".cjs"}:
        return "javascript"
    if suffix == ".css":
        return "css"
    if suffix in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}:
        return "image"
    if suffix in {".woff", ".woff2", ".ttf", ".otf"}:
        return "font"
    if suffix in {".json", ".har"}:
        return "structured-data"
    if suffix in {".sqlite", ".sqlite3", ".db"}:
        return "database"
    return "other"


def build_index(report: dict, root: Path, db_path: Path) -> Path:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA)
        for table in (
            "artifacts",
            "routes",
            "endpoints",
            "technologies",
            "frameworks",
            "modules",
            "coverage",
            "metadata",
        ):
            conn.execute(f"DELETE FROM {table}")

        for route in report.get("routes", []):
            conn.execute("INSERT OR REPLACE INTO routes(url) VALUES (?)", (route,))

        for endpoint in report.get("observed_endpoints", []):
            conn.execute(
                "INSERT OR REPLACE INTO endpoints(url, kind) VALUES (?, ?)",
                (endpoint, "observed"),
            )

        for tech in report.get("technologies", []):
            name = tech if isinstance(tech, str) else tech.get("name", str(tech))
            conn.execute("INSERT OR REPLACE INTO technologies(name) VALUES (?)", (name,))

        for framework in report.get("framework_matches", []):
            conn.execute(
                """
                INSERT OR REPLACE INTO frameworks(
                    name, confidence, evidence_json, details_json
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    framework.get("name"),
                    float(framework.get("confidence") or 0),
                    json.dumps(framework.get("evidence", []), ensure_ascii=False),
                    json.dumps(framework.get("details", {}), ensure_ascii=False),
                ),
            )

        for module in report.get("modules", []):
            conn.execute(
                """
                INSERT INTO modules(
                    name, status, recovered_failures, errors_json
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    module.get("name"),
                    module.get("status"),
                    int(module.get("recovered_failures") or 0),
                    json.dumps(module.get("errors", []), ensure_ascii=False),
                ),
            )

        for layer, data in (report.get("coverage") or {}).get("matrix", {}).items():
            conn.execute(
                "INSERT OR REPLACE INTO coverage(layer,status,reason) VALUES (?,?,?)",
                (layer, data.get("status"), data.get("reason")),
            )

        db_resolved = db_path.resolve()
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            try:
                if path.resolve() == db_resolved:
                    continue
                size = path.stat().st_size
            except OSError:
                continue
            relative = str(path.relative_to(root))
            conn.execute(
                """
                INSERT OR REPLACE INTO artifacts(path,kind,size,sha256)
                VALUES (?, ?, ?, ?)
                """,
                (relative, _artifact_kind(path), size, _sha256(path)),
            )

        metadata = {
            "target": report.get("target", ""),
            "mode": report.get("mode", ""),
            "started_at": report.get("started_at", ""),
            "finished_at": report.get("finished_at", ""),
            "coverage_score": (report.get("coverage") or {}).get("score", ""),
        }
        for key, value in metadata.items():
            conn.execute(
                "INSERT OR REPLACE INTO metadata(key,value) VALUES (?, ?)",
                (key, str(value)),
            )
        conn.commit()
    finally:
        conn.close()
    return db_path
