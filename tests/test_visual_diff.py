from pathlib import Path

from PIL import Image

from repo_alfa.visual_diff import compare_images


def test_visual_diff_identical_images(tmp_path: Path):
    left = tmp_path / "left.png"
    right = tmp_path / "right.png"
    Image.new("RGB", (10, 10), (255, 255, 255)).save(left)
    Image.new("RGB", (10, 10), (255, 255, 255)).save(right)
    result = compare_images(left, right, tmp_path / "diff.png")
    assert result.similarity == 100.0
    assert result.different_pixels_ratio == 0.0
    assert Path(result.diff_path).exists()
