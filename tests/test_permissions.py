# tests/test_permissions.py
from puppet_ai.core.permissions import check_accessibility

def test_check_accessibility_returns_dict():
    result = check_accessibility()
    assert "accessible" in result
    assert isinstance(result["accessible"], bool)

def test_check_accessibility_has_instructions():
    result = check_accessibility()
    if not result["accessible"]:
        assert "instructions" in result
