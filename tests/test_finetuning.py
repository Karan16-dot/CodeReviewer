import pytest
import sqlite3
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
from finetuning import FineTuningDataPreparer, FineTuningManager

def test_export_to_jsonl_valid_sessions(tmp_path):
    """Verify that export_to_jsonl writes correct JSONL files and filters invalid sessions."""
    db_path = tmp_path / "memory.db"
    output_file = tmp_path / "train.jsonl"

    # Create dummy schema
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            role TEXT,
            content TEXT,
            tool_calls TEXT,
            timestamp TEXT
        )
    """)

    # Session 1: Valid (User + Assistant)
    cursor.execute(
        "INSERT INTO messages (session_id, role, content, tool_calls) VALUES (?, ?, ?, ?)",
        ("session_1", "user", "Hello there", None)
    )
    cursor.execute(
        "INSERT INTO messages (session_id, role, content, tool_calls) VALUES (?, ?, ?, ?)",
        ("session_1", "assistant", "Hi! How can I help you?", None)
    )

    # Session 2: Invalid (User only - should be skipped)
    cursor.execute(
        "INSERT INTO messages (session_id, role, content, tool_calls) VALUES (?, ?, ?, ?)",
        ("session_2", "user", "I am alone here", None)
    )

    # Session 3: Valid (User + Assistant with tool calls and tool role)
    cursor.execute(
        "INSERT INTO messages (session_id, role, content, tool_calls) VALUES (?, ?, ?, ?)",
        ("session_3", "user", "Search for index.py", None)
    )
    cursor.execute(
        "INSERT INTO messages (session_id, role, content, tool_calls) VALUES (?, ?, ?, ?)",
        ("session_3", "assistant", "", '[{"id": "call-1", "name": "search_files"}]')
    )
    cursor.execute(
        "INSERT INTO messages (session_id, role, content, tool_calls) VALUES (?, ?, ?, ?)",
        ("session_3", "tool", "Found 1 match", '[{"id": "call-1", "name": "search_files"}]')
    )
    cursor.execute(
        "INSERT INTO messages (session_id, role, content, tool_calls) VALUES (?, ?, ?, ?)",
        ("session_3", "assistant", "I found it.", None)
    )

    conn.commit()
    conn.close()

    # Run exporter
    count = FineTuningDataPreparer.export_to_jsonl(db_path, output_file)
    assert count == 2  # session_1 and session_3 (session_2 is skipped)

    assert output_file.exists()
    lines = output_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2

    # Verify session_1 line
    s1_data = json.loads(lines[0])
    assert "messages" in s1_data
    assert len(s1_data["messages"]) == 2
    assert s1_data["messages"][0]["role"] == "user"
    assert s1_data["messages"][0]["content"] == "Hello there"
    assert s1_data["messages"][1]["role"] == "assistant"
    assert s1_data["messages"][1]["content"] == "Hi! How can I help you?"

    # Verify session_3 line
    s3_data = json.loads(lines[1])
    assert len(s3_data["messages"]) == 4
    assert s3_data["messages"][1]["role"] == "assistant"
    assert s3_data["messages"][1]["tool_calls"] == [{"id": "call-1", "name": "search_files"}]
    assert s3_data["messages"][2]["role"] == "tool"
    assert s3_data["messages"][2]["tool_call_id"] == "call-1"
    assert s3_data["messages"][2]["name"] == "search_files"


def test_fine_tuning_manager_operations(tmp_path):
    """Verify that FineTuningManager wraps OpenAI client endpoints properly."""
    # Create fake training file
    train_file = tmp_path / "train.jsonl"
    train_file.write_text("{}", encoding="utf-8")

    # Mock raw OpenAI SDK client
    mock_raw_client = MagicMock()
    
    # Mock upload
    mock_file = MagicMock()
    mock_file.id = "file-12345"
    mock_raw_client.files.create.return_value = mock_file

    # Mock job creation
    mock_job = MagicMock()
    mock_job.id = "ftjob-67890"
    mock_raw_client.fine_tuning.jobs.create.return_value = mock_job

    # Mock job retrieval
    mock_retrieve = MagicMock()
    mock_retrieve.id = "ftjob-67890"
    mock_retrieve.status = "succeeded"
    mock_retrieve.model = "gpt-3.5-turbo"
    mock_retrieve.fine_tuned_model = "ft:gpt-3.5-turbo:custom-model-suffix"
    mock_retrieve.trained_tokens = 500
    mock_retrieve.created_at = 123456789
    mock_raw_client.fine_tuning.jobs.retrieve.return_value = mock_retrieve

    # Mock job listing
    mock_list_item = MagicMock()
    mock_list_item.id = "ftjob-67890"
    mock_list_item.status = "succeeded"
    mock_list_item.model = "gpt-3.5-turbo"
    mock_list_item.fine_tuned_model = "ft:gpt-3.5-turbo:custom-model-suffix"
    mock_list_item.created_at = 123456789
    mock_list = MagicMock()
    mock_list.data = [mock_list_item]
    mock_raw_client.fine_tuning.jobs.list.return_value = mock_list

    # Initialize manager
    manager = FineTuningManager(client=mock_raw_client)

    # Test file upload
    file_id = manager.upload_file(train_file)
    assert file_id == "file-12345"
    mock_raw_client.files.create.assert_called_once()

    # Test start job
    job_id = manager.start_job("file-12345")
    assert job_id == "ftjob-67890"
    mock_raw_client.fine_tuning.jobs.create.assert_called_once_with(
        training_file="file-12345",
        model="gpt-3.5-turbo"
    )

    # Test job status
    status = manager.get_job_status("ftjob-67890")
    assert status["id"] == "ftjob-67890"
    assert status["status"] == "succeeded"
    assert status["fine_tuned_model"] == "ft:gpt-3.5-turbo:custom-model-suffix"
    assert status["trained_tokens"] == 500

    # Test list jobs
    jobs = manager.list_jobs()
    assert len(jobs) == 1
    assert jobs[0]["id"] == "ftjob-67890"
    assert jobs[0]["status"] == "succeeded"
