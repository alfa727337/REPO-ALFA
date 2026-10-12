from __future__ import annotations

import shutil
from pathlib import Path


class ReconstructionEngine:
    """Builds a local preview from artifacts already captured by REPO ALFA.

    This intentionally reconstructs only resources the browser received and that
    were saved locally; it does not attempt to synthesize or access private server logic.
    """

    def reconstruct(self, capture_root: Path, destination: Path) -> dict:
        destination.mkdir(parents=True, exist_ok=True)
        source = capture_root / "dom" / "rendered.html"
        if not source.exists():
            source = capture_root / "html" / "source.html"
        if not source.exists():
            raise FileNotFoundError("no captured HTML/DOM found")

        index = destination / "index.html"
        shutil.copy2(source, index)

        copied: list[str] = [str(index)]
        for directory in ("assets", "css", "javascript", "fonts", "images", "svg"):
            src = capture_root / directory
            if not src.exists() or not src.is_dir():
                continue
            dst = destination / directory
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            copied.append(str(dst))

        return {
            "entrypoint": str(index),
            "copied": copied,
            "note": "Reconstruction contains captured observable frontend artifacts only.",
        }
