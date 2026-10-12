from repo_alfa.browser_capture import _payload_metadata, _redact_text


def test_console_redaction_removes_bearer_and_jwt():
    jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjMifQ.signaturevalue"
    text = f"Authorization Bearer abc.def.ghi token={jwt}"
    result = _redact_text(text)
    assert "abc.def.ghi" not in result
    assert jwt not in result
    assert "<redacted" in result


def test_websocket_payload_metadata_has_no_payload_value():
    result = _payload_metadata("private-message")
    assert result["kind"] == "text"
    assert result["bytes"] == len(b"private-message")
    assert "sha256" in result
    assert "private-message" not in str(result)
