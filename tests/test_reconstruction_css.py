import json
from pathlib import Path

from repo_alfa.reconstruction import ReconstructionEngine


def test_reconstruction_rewrites_nested_css_assets(tmp_path: Path):
    capture = tmp_path / "capture"
    css_dir = capture / "assets" / "example.com"
    css_dir.mkdir(parents=True)
    css_path = css_dir / "app.css"
    css_path.write_text(".hero{background:url('/img/hero.png')}", encoding="utf-8")
    image_path = css_dir / "hero.png"
    image_path.write_bytes(b"png")
    (capture / "dom").mkdir(parents=True)
    (capture / "dom" / "rendered.html").write_text(
        '<link rel="stylesheet" href="https://example.com/app.css">', encoding="utf-8"
    )
    (capture / "assets" / "manifest.json").write_text(
        json.dumps(
            {
                "url_to_local": {
                    "https://example.com/app.css": "assets/example.com/app.css",
                    "https://example.com/img/hero.png": "assets/example.com/hero.png",
                },
                "assets": [
                    {
                        "url": "https://example.com/app.css",
                        "final_url": "https://example.com/app.css",
                        "relative_path": "assets/example.com/app.css",
                        "status": "saved",
                    },
                    {
                        "url": "https://example.com/img/hero.png",
                        "final_url": "https://example.com/img/hero.png",
                        "relative_path": "assets/example.com/hero.png",
                        "status": "saved",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    destination = tmp_path / "reconstructed"
    result = ReconstructionEngine().reconstruct(
        capture, destination, "https://example.com/"
    )
    rewritten = (destination / "assets" / "example.com" / "app.css").read_text(
        encoding="utf-8"
    )
    assert "hero.png" in rewritten
    assert result["css_rewrite"]["css_references_rewritten"] == 1
