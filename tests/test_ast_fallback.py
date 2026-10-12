from pathlib import Path

from repo_alfa.javascript_analysis import analyze_directory, analyze_text


def test_secret_hint_is_hashed_not_exposed():
    secret = "super-secret-api-value-123"
    result = analyze_text(f"const api_key='{secret}'", "app.js")
    assert result.secret_hints
    hint = result.secret_hints[0]
    assert hint["length"] == len(secret)
    assert hint["sha256"]
    assert secret not in str(hint)


def test_directory_ast_metadata_is_always_structured(tmp_path: Path):
    script = tmp_path / "app.js"
    script.write_text("import x from 'x'; fetch('/api/a')", encoding="utf-8")
    findings = analyze_directory(tmp_path, "https://example.com/")
    assert len(findings) == 1
    assert "ast" in findings[0]
    assert isinstance(findings[0]["ast"], dict)
