from repo_alfa.frameworks import analyze_frameworks


def test_nextjs_and_react_detection():
    html = '<script id="__NEXT_DATA__"></script><div data-reactroot></div>'
    urls = ["https://example.com/_next/static/chunks/app.js"]
    results = analyze_frameworks(html, urls)
    names = {item["name"] for item in results}
    assert "Next.js" in names
    assert "React" in names


def test_results_are_sorted_by_confidence():
    results = analyze_frameworks("__NEXT_DATA__ /_next/static/", [])
    confidences = [item["confidence"] for item in results]
    assert confidences == sorted(confidences, reverse=True)
