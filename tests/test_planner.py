import pytest
from unittest.mock import patch, MagicMock
from cli import InteractiveCLI

@patch("cli.MemoryIndex")
@patch("cli.OpenAIClient")
def test_plan_command_react_loop(mock_client_class, mock_memory_index_class):
    """Verify that /plan parses the goal, formats ReAct instructions, and executes tool calls recursively."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    mock_memory_index = MagicMock()
    mock_memory_index_class.return_value = mock_memory_index
    mock_memory_index.load_messages.return_value = []

    cli = InteractiveCLI()
    cli.client = mock_client

    # Turn 1: yield a tool call to create plan.md
    # Turn 2: yield final text content
    mock_client.stream_chat.side_effect = [
        [
            {
                "type": "tool_calls",
                "calls": [
                    {
                        "id": "call-plan",
                        "name": "write_file",
                        "arguments": '{"path": "plan.md", "content": "# Plan\\n- [ ] Task 1"}'
                    }
                ]
            }
        ],
        [
            "Plan created and goal completed!"
        ]
    ]
    mock_client.get_embedding.return_value = [0.1, 0.2]

    # Mock tool registry execution
    cli.tool_registry = MagicMock()
    cli.tool_registry.schemas = [{"type": "function", "function": {"name": "write_file"}}]
    cli.tool_registry.execute.return_value = "Successfully wrote file to: plan.md"

    # Mock memory manager to avoid file writes
    cli.memory = MagicMock()
    cli.memory.load.return_value = None

    # Mock input to run "/plan Build file" and then exit the CLI shell
    with patch("builtins.input", side_effect=["/plan Build file", "exit"]):
        try:
            cli.run()
        except SystemExit:
            pass

    # Assert stream_chat was called twice (once for initial plan, once for result followup)
    assert mock_client.stream_chat.call_count == 2

    # Assert tool was executed
    cli.tool_registry.execute.assert_called_once_with(
        "write_file",
        {"path": "plan.md", "content": "# Plan\n- [ ] Task 1"}
    )

    # Check conversation history has user plan instruction, assistant tool call request, and tool output
    history = cli.messages
    assert any("Goal: \"Build file\"" in msg["content"] for msg in history if msg.get("content"))
    assert any(msg["role"] == "tool" and msg["content"] == "Successfully wrote file to: plan.md" for msg in history)
    assert any("Plan created and goal completed!" in msg["content"] for msg in history if msg.get("content"))
