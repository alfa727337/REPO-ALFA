from repo_alfa.javascript_analysis import aggregate, analyze_text


def test_analyze_text_extracts_imports_urls_and_sourcemap():
    text = """
    import x from 'pkg-a';
    const y = require('pkg-b');
    import('/lazy/chunk.js');
    fetch('/api/users');
    //# sourceMappingURL=app.js.map
    """
    finding = analyze_text(text, "app.js", "https://example.com/app.js")
    assert "pkg-a" in finding.imports
    assert "pkg-b" in finding.imports
    assert "/lazy/chunk.js" in finding.dynamic_imports
    assert "https://example.com/api/users" in finding.urls
    assert "app.js.map" in finding.source_maps


def test_aggregate_merges_findings():
    one = analyze_text("import 'a'; fetch('/api/a')", "a.js", "https://example.com").to_dict()
    two = analyze_text("import 'b'; fetch('/api/b')", "b.js", "https://example.com").to_dict()
    result = aggregate([one, two])
    assert result["files_analyzed"] == 2
    assert "a" in result["imports"]
    assert "b" in result["imports"]
