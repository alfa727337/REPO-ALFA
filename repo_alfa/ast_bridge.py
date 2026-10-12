from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


def ast_available() -> bool:
    script = Path(__file__).parent / "node" / "js_ast.mjs"
    repo_root = Path(__file__).parent.parent
    babel_parser = repo_root / "node_modules" / "@babel" / "parser"
    return bool(shutil.which("node") and script.exists() and babel_parser.exists())


def analyze_with_babel(path: Path, timeout_seconds: float = 20.0) -> dict:
    script = Path(__file__).parent / "node" / "js_ast.mjs"
    if not shutil.which("node"):
        return {"available": False, "reason": "node-not-found"}
    if not script.exists():
        return {"available": False, "reason": "analyzer-script-not-found"}
    try:
        process = subprocess.run(
            ["node", str(script), str(path)],
            cwd=str(Path(__file__).parent.parent),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"available": True, "parsed": False, "error": repr(exc)}
    if process.returncode != 0:
        return {
            "available": True,
            "parsed": False,
            "error": process.stderr[-8000:],
            "returncode": process.returncode,
        }
    try:
        data = json.loads(process.stdout)
    except json.JSONDecodeError as exc:
        return {
            "available": True,
            "parsed": False,
            "error": f"invalid analyzer JSON: {exc}",
        }
    data["available"] = True
    return data
