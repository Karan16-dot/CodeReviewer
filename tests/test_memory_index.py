import pytest
import sqlite3
import json
from unittest.mock import MagicMock
from memory_index import MemoryIndex

def test_memory_index_init(tmp_path):
    """Verify MemoryIndex initializes database and creates tables successfully."""
    db_file = tmp_path / "test_memory.db"
    mgr = MemoryIndex(db_path=str(db_file))

    assert db_file.exists()

    # Query tables in SQLite to confirm schema exists
    conn = sqlite3.connect(str(db_file))
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()

    assert "messages" in tables
    assert "embeddings" in tables

def test_memory_index_messages(tmp_path):
    """Verify storing, loading, and clearing message context from SQLite database."""
    db_file = tmp_path / "test_memory.db"
    mgr = MemoryIndex(db_path=str(db_file))
    session = "sess_123"

    # Store messages
    mgr.store_message(session, "system", "Sys prompt")
    mgr.store_message(session, "user", "User prompt")
    mgr.store_message(session, "assistant", "Agent prompt", [{"id": "tc1", "name": "tool"}])

    # Load messages
    messages = mgr.load_messages(session)
    assert len(messages) == 3
    assert messages[0] == {"role": "system", "content": "Sys prompt"}
    assert messages[2] == {
        "role": "assistant",
        "content": "Agent prompt",
        "tool_calls": [{"id": "tc1", "name": "tool"}]
    }

    # Clear session
    mgr.clear_session(session)
    assert len(mgr.load_messages(session)) == 0

def test_memory_index_semantic_search_numpy(tmp_path):
    """Verify fallback NumPy cosine-similarity search calculations ranking vectors correctly."""
    db_file = tmp_path / "test_memory.db"

    # Setup mock LLM client returning deterministic static embeddings
    mock_client = MagicMock()
    mock_client.get_embedding.side_effect = lambda text: {
        "apple": [1.0, 0.0, 0.0],
        "banana": [0.0, 1.0, 0.0],
        "fruit query": [0.9, 0.1, 0.0]
    }.get(text, [0.0, 0.0, 1.0])

    # Disable Chroma explicitly to test fallback NumPy pipeline
    with patch("memory_index.CHROMA_AVAILABLE", False):
        mgr = MemoryIndex(db_path=str(db_file), client=mock_client)

        # Store embeddings
        mgr.store_embedding("apple", {"category": "fruit"})
        mgr.store_embedding("banana", {"category": "fruit"})

        # Search query matching "apple" closely
        results = mgr.search_semantic("fruit query", limit=2)

        assert len(results) == 2
        # Apple should rank first since [1.0, 0.0, 0.0] is closer to [0.9, 0.1, 0.0] than [0.0, 1.0, 0.0]
        assert results[0]["text"] == "apple"
        assert results[0]["score"] > results[1]["score"]
        assert results[0]["metadata"] == {"category": "fruit"}

# Import patch helper inside fixture/scope
from unittest.mock import patch
