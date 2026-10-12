from repo_alfa.css_analysis import analyze_css_text
from repo_alfa.dom_analysis import compare_static_and_rendered


def test_css_analysis_extracts_design_tokens_and_media():
    css = """
    :root { --brand: #123456; }
    @font-face { font-family: 'Alpha'; src: url('/alpha.woff2'); }
    @media (max-width: 600px) { .x { display:none; } }
    @keyframes pulse { from { opacity: 0 } to { opacity: 1 } }
    """
    result = analyze_css_text(css, "app.css")
    assert result["custom_properties"]["--brand"] == "#123456"
    assert any("Alpha" in item for item in result["font_families"])
    assert "(max-width: 600px)" in result["media_queries"]
    assert "pulse" in result["keyframes"]


def test_dom_comparison_detects_runtime_link():
    static = '<html><body><a href="/a">A</a></body></html>'
    rendered = '<html><body><a href="/a">A</a><a href="/b">B</a></body></html>'
    result = compare_static_and_rendered(static, rendered, "https://example.com/")
    assert "https://example.com/b" in result["delta"]["links_added_by_runtime"]
