from __future__ import annotations

import importlib.util
import os
import platform
import shutil
import sys
import tempfile
from pathlib import Path


def run_doctor() -> dict:
    checks: list[dict] = []

    def add(name: str, ok: bool, detail: str) -> None:
        checks.append({"name": name, "ok": ok, "detail": detail})

    add("python", sys.version_info >= (3, 11), sys.version.split()[0])
    add("platform", True, f"{platform.system()} {platform.release()}")

    for module in ("httpx", "bs4", "lxml", "playwright", "pydantic", "networkx", "PIL"):
        add(f"module:{module}", importlib.util.find_spec(module) is not None, module)

    add("git", shutil.which("git") is not None, shutil.which("git") or "not found")

    try:
        with tempfile.TemporaryDirectory(prefix="repo-alfa-doctor-") as directory:
            probe = Path(directory) / "write-test"
            probe.write_text("ok", encoding="utf-8")
            writable = probe.read_text(encoding="utf-8") == "ok"
        add("filesystem", writable, tempfile.gettempdir())
    except OSError as exc:
        add("filesystem", False, repr(exc))

    playwright_home = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    add(
        "playwright-browser-path",
        True,
        playwright_home or "managed by Playwright default cache",
    )

    required_ok = all(
        item["ok"]
        for item in checks
        if item["name"] not in {"platform", "playwright-browser-path"}
    )
    return {
        "ok": required_ok,
        "python_executable": sys.executable,
        "checks": checks,
    }
