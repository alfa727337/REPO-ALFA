from repo_alfa.browser_capture import _safe_state_id


def test_ui_state_id_is_deterministic_and_bounded():
    one = _safe_state_id("tab", 3, "Settings")
    two = _safe_state_id("tab", 3, "Settings")
    assert one == two
    assert one.startswith("tab-003-")
    assert len(one.rsplit("-", 1)[-1]) == 8
