import json
from pathlib import Path

from repo_alfa.reconstruction import ReconstructionEngine


def test_reconstruction_rewrites_captured_asset(tmp_path: Path):
    capture = tmp_path / "capture"
    (capture / "dom").mkdir(parents=True)
    (capture / "assets" / "example.com").mkdir(parents=True)
    local_asset = capture / "assets" / "example.com" / "abc-app.js"
    local_asset.write_text("console.log('ok')", encoding="utf-8")
    (capture / "dom" / "rendered.html").write_text(
        '<html><body><script src="https://example.com/app.js"></script></body></html>',
        encoding="utf-8",
    )
    (capture / "assets" / "manifest.json").write_text(
        json.dumps({"url_to_local": {"https://example.com/app.js": "assets/example.com/abc-app.js"}}),
        encoding="utf-8",
    )
    (capture / "full-report.json").write_text(
        json.dumps({"target": "https://example.com/"}), encoding="utf-8"
    )

    destination = tmp_path / "reconstructed"
    result = ReconstructionEngine().reconstruct(capture, destination)
    html = (destination / "index.html").read_text(encoding="utf-8")
    assert "assets/example.com/abc-app.js" in html
    assert result["rewritten_assets"] == 1
    assert (destination / "serve.py").exists()
