from repo_alfa.framework_details import extract_framework_details


def test_nextjs_metadata_is_extracted():
    html = """
    <html><body>
    <div id="__next"></div>
    <script id="__NEXT_DATA__" type="application/json">
    {"buildId":"build-123","page":"/products","query":{"id":"42"},"gsp":true}
    </script>
    </body></html>
    """
    details = extract_framework_details(html)
    assert details["Next.js"]["build_id"] == "build-123"
    assert details["Next.js"]["page"] == "/products"
    assert details["Next.js"]["query_keys"] == ["id"]


def test_angular_version_is_extracted():
    details = extract_framework_details('<app-root ng-version="21.0.0"></app-root>')
    assert details["Angular"]["version"] == "21.0.0"
