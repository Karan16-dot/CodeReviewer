import pytest
import json
from memory import ConversationMemory

def test_save_and_load(tmp_path):
    """Verify that ConversationMemory saves and loads messages correctly."""
    file_path = tmp_path / "messages.json"
    memory = ConversationMemory(file_path=str(file_path))

    messages = [
        {"role": "system", "content": "You are an agent."},
        {"role": "user", "content": "Hello!"},
        {"role": "assistant", "content": "Hi there!"}
    ]

    # Save the messages
    memory.save(messages)
    assert file_path.exists()

    # Load and assert they are identical
    loaded = memory.load()
    assert loaded == messages

def test_load_missing_file(tmp_path):
    """Verify that loading a non-existent memory file returns an empty list."""
    file_path = tmp_path / "non_existent.json"
    memory = ConversationMemory(file_path=str(file_path))

    assert memory.load() == []

def test_delete_file(tmp_path):
    """Verify that delete successfully removes the memory file."""
    file_path = tmp_path / "messages.json"
    memory = ConversationMemory(file_path=str(file_path))

    # Pre-populate and save file
    memory.save([{"role": "user", "content": "hi"}])
    assert file_path.exists()

    # Delete
    memory.delete()
    assert not file_path.exists()

def test_delete_non_existent(tmp_path):
    """Verify that delete does not raise errors if the file doesn't exist."""
    file_path = tmp_path / "non_existent.json"
    memory = ConversationMemory(file_path=str(file_path))

    # Calling delete on non-existent file should complete silently
    memory.delete()
    assert not file_path.exists()

def test_corrupted_json(tmp_path):
    """Verify that loading corrupted JSON raises a ValueError."""
    file_path = tmp_path / "corrupt.json"
    memory = ConversationMemory(file_path=str(file_path))

    # Write invalid json content
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("{invalid-json-content: :}")

    with pytest.raises(ValueError) as exc_info:
        memory.load()
    assert "corrupted" in str(exc_info.value)
