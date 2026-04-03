# tests/test_instructions.py
from puppet_ai.instructions import MCP_INSTRUCTIONS

def test_instructions_is_string():
    assert isinstance(MCP_INSTRUCTIONS, str) and len(MCP_INSTRUCTIONS) > 100

def test_instructions_contains_vision_tools():
    assert "vision_list_windows" in MCP_INSTRUCTIONS
    assert "vision_read_window" in MCP_INSTRUCTIONS
    assert "vision_screenshot" in MCP_INSTRUCTIONS

def test_instructions_contains_action_tools():
    assert "action_click" in MCP_INSTRUCTIONS
    assert "action_type_text" in MCP_INSTRUCTIONS
    assert "action_hotkey" in MCP_INSTRUCTIONS

def test_instructions_contains_workflow():
    assert "LOOK" in MCP_INSTRUCTIONS
    assert "ACT" in MCP_INSTRUCTIONS

def test_instructions_contains_coordinate_hint():
    assert "center" in MCP_INSTRUCTIONS.lower() or "bounding box" in MCP_INSTRUCTIONS.lower()
