import pytest
from unittest.mock import patch, MagicMock
from tools import ToolRegistry, read_file, write_file, search_files, list_directory, run_command

def test_tool_registry_execution():
    """Verify that ToolRegistry registers functions and executes them correctly."""
    registry = ToolRegistry()

    def add(a: int, b: int) -> int:
        return a + b

    schema = {
        "name": "add",
        "description": "adds two numbers",
        "parameters": {}
    }

    registry.register("add", add, schema)

    # Test successful execution
    assert registry.execute("add", {"a": 10, "b": 5}) == "15"

    # Test unregistered tool
    assert "not registered" in registry.execute("subtract", {"a": 10, "b": 5})

    # Test bad arguments
    assert "Error invoking tool" in registry.execute("add", {"wrong_arg": 1})

@patch("tools._reader")
def test_read_file_tool(mock_reader):
    """Verify read_file tool delegates correctly to FileReader."""
    mock_reader.read_file.return_value = "file contents"
    res = read_file("test.txt")
    assert res == "file contents"
    mock_reader.read_file.assert_called_once_with("test.txt")

@patch("tools._editor")
def test_write_file_tool(mock_editor):
    """Verify write_file tool delegates correctly to FileEditor."""
    res = write_file("test.txt", "hello")
    assert "Successfully wrote" in res
    mock_editor.write.assert_called_once()

def test_run_command_tool():
    """Verify run_command executes standard system shell calls."""
    res = run_command("echo Hello")
    assert "Hello" in res
    assert "Exit Code: 0" in res
