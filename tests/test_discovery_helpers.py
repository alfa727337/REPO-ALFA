from repo_alfa.crawler import normalize_url
from repo_alfa.graphql_capture import detect_graphql


def test_normalize_url_removes_fragment_tracking_and_sorts_query():
    url = "HTTPS://Example.COM/path/?utm_source=x&b=2&a=1#section"
    assert normalize_url(url) == "https://example.com/path?a=1&b=2"


def test_graphql_operation_name_from_observed_get_url():
    events = [
        {
            "type": "request",
            "method": "GET",
            "url": "https://api.example.com/graphql?operationName=Viewer&query=query%20Viewer",
            "resource_type": "fetch",
        },
        {
            "type": "response",
            "status": 200,
            "url": "https://api.example.com/graphql?operationName=Viewer&query=query%20Viewer",
        },
    ]
    result = detect_graphql(events)
    assert result["detected"] is True
    endpoint = result["endpoints"][0]
    assert endpoint["url"] == "https://api.example.com/graphql"
    assert "Viewer" in endpoint["operation_names"]
    assert "GET" in endpoint["methods"]
    assert 200 in endpoint["statuses"]
