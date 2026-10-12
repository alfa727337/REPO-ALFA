from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path

try:
    from PIL import Image, ImageChops, ImageStat
except ImportError:  # optional until visual diff is requested
    Image = ImageChops = ImageStat = None


@dataclass(slots=True)
class VisualDiffResult:
    similarity: float
    different_pixels_ratio: float
    diff_path: str | None
    width: int
    height: int

    def to_dict(self) -> dict:
        return asdict(self)


def compare_images(left: Path, right: Path, diff_output: Path | None = None) -> VisualDiffResult:
    if Image is None:
        raise RuntimeError("Pillow is required for visual diff: pip install pillow")
    a = Image.open(left).convert("RGBA")
    b = Image.open(right).convert("RGBA")
    width = max(a.width, b.width)
    height = max(a.height, b.height)
    if a.size != (width, height):
        canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        canvas.paste(a, (0, 0))
        a = canvas
    if b.size != (width, height):
        canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        canvas.paste(b, (0, 0))
        b = canvas

    diff = ImageChops.difference(a, b)
    grayscale = diff.convert("L")
    hist = grayscale.histogram()
    total_pixels = width * height
    equal_pixels = hist[0] if hist else 0
    different_ratio = 1 - (equal_pixels / total_pixels if total_pixels else 1)
    stat = ImageStat.Stat(grayscale)
    mean = float(stat.mean[0]) if stat.mean else 0.0
    similarity = max(0.0, 1.0 - mean / 255.0)

    written = None
    if diff_output is not None:
        diff_output.parent.mkdir(parents=True, exist_ok=True)
        diff.save(diff_output)
        written = str(diff_output)

    return VisualDiffResult(
        similarity=round(similarity * 100, 4),
        different_pixels_ratio=round(different_ratio * 100, 4),
        diff_path=written,
        width=width,
        height=height,
    )
