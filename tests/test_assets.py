from repo_alfa.assets import AssetDownloader


def test_css_nested_asset_discovery():
    downloader = AssetDownloader()
    css = b"@import './theme.css'; .hero{background:url('../img/hero.webp')}"
    urls = downloader._discover_nested(
        "https://example.com/css/app.css",
        css,
        "text/css",
        ".css",
    )
    assert "https://example.com/css/theme.css" in urls
    assert "https://example.com/img/hero.webp" in urls


def test_js_dynamic_chunk_discovery():
    downloader = AssetDownloader()
    js = b"import('./chunk.js'); const logo='/images/logo.svg';"
    urls = downloader._discover_nested(
        "https://example.com/assets/app.js",
        js,
        "application/javascript",
        ".js",
    )
    assert "https://example.com/assets/chunk.js" in urls
    assert "https://example.com/images/logo.svg" in urls
