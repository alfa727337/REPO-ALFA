from repo_alfa.doctor import run_doctor


def test_doctor_returns_structured_checks():
    result = run_doctor()
    assert isinstance(result["ok"], bool)
    assert result["python_executable"]
    names = {item["name"] for item in result["checks"]}
    assert "python" in names
    assert "filesystem" in names
    assert "module:httpx" in names
