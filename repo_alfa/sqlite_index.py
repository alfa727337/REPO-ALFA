from __future__ import annotations

import json
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS artifacts(path TEXT PRIMARY KEY, kind TEXT, size INTEGER, sha256 TEXT);
CREATE TABLE IF NOT EXISTS routes(url TEXT PRIMARY KEY);
CREATE TABLE IF NOT EXISTS endpoints(url TEXT PRIMARY KEY, kind TEXT);
CREATE TABLE IF NOT EXISTS technologies(name TEXT PRIMARY KEY);
CREATE TABLE IF NOT EXISTS modules(name TEXT, status TEXT, recovered_failures INTEGER, errors_json TEXT);
CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY, value TEXT);
"""


def build_index(report: dict, root: Path, db_path: Path) -> Path:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA)
        conn.execute("DELETE FROM routes")
        conn.execute("DELETE FROM endpoints")
        conn.execute("DELETE FROM technologies")
        conn.execute("DELETE FROM modules")
        for route in report.get("routes", []):
            conn.execute("INSERT OR REPLACE INTO routes(url) VALUES (?)", (route,))
        for endpoint in report.get("observed_endpoints", []):
            conn.execute("INSERT OR REPLACE INTO endpoints(url, kind) VALUES (?, ?)", (endpoint, "observed"))
        for tech in report.get("technologies", []):
            name = tech if isinstance(tech, str) else tech.get("name", str(tech))
            conn.execute("INSERT OR REPLACE INTO technologies(name) VALUES (?)", (name,))
        for module in report.get("modules", []):
            conn.execute(
                "INSERT INTO modules(name,status,recovered_failures,errors_json) VALUES (?,?,?,?)",
                (
                    module.get("name"),
                    module.get("status"),
                    int(module.get("recovered_failures") or 0),
                    json.dumps(module.get("errors", []), ensure_ascii=False),
                ),
            )
        conn.execute("INSERT OR REPLACE INTO metadata(key,value) VALUES ('target', ?)", (report.get("target", ""),))
        conn.execute("INSERT OR REPLACE INTO metadata(key,value) VALUES ('mode', ?)", (report.get("mode", ""),))
        conn.commit()
    finally:
        conn.close()
    return db_path
