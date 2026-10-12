from repo_alfa.api_classification import classify_url, summarize_network


def test_classification():
    assert classify_url("wss://example.com/socket") == "websocket"
    assert classify_url("https://example.com/graphql") == "graphql"
    assert classify_url("https://example.com/app.js") == "static"
    assert classify_url("https://example.com/users", "fetch") == "api"


def test_network_summary_counts_requests():
    events = [
        {"type": "request", "url": "https://example.com/api/users", "method": "GET", "resource_type": "fetch"},
        {"type": "request", "url": "https://cdn.example.com/app.js", "method": "GET", "resource_type": "script"},
        {"type": "response", "url": "https://example.com/api/users", "status": 200},
    ]
    result = summarize_network(events)
    assert result["counts"]["api"] == 1
    assert result["counts"]["static"] == 1
    assert result["methods"]["GET"] == 2
