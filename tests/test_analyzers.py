from repo_alfa.analyzers import discover_endpoints, fingerprint, same_origin


def test_fingerprint_detects_next_and_webpack():
    text = '<script>self.webpackChunk_N_E=[]</script><script src="/_next/app.js"></script>'
    result = fingerprint(text)
    assert "Next.js" in result
    assert "Webpack" in result


def test_endpoint_discovery_merges_observed_and_static():
    result = discover_endpoints(
        ['fetch("/api/users")', 'https://api.example.com/v1/items'],
        ["https://example.com/graphql"],
    )
    assert "/api/users" in result
    assert "https://api.example.com/v1/items" in result
    assert "https://example.com/graphql" in result


def test_same_origin():
    assert same_origin("https://example.com/a", "https://example.com/b")
    assert not same_origin("https://cdn.example.com/a", "https://example.com/b")
