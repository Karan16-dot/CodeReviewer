import pytest
import sqlite3
import json
from pathlib import Path
from telemetry import TelemetryTracker

@pytest.fixture
def temp_telemetry_db(tmp_path):
    """Fixture to isolate the SQLite telemetry database file path for tests."""
    original_db = TelemetryTracker.db_path
    TelemetryTracker.db_path = tmp_path / "memory.db"
    yield TelemetryTracker.db_path
    # Restore original path
    TelemetryTracker.db_path = original_db

def test_telemetry_tracker_logging(temp_telemetry_db):
    """Verify TelemetryTracker logs events and calculates aggregate metrics correctly."""
    # Log some events
    TelemetryTracker.log_llm_call(
        model="gpt-4o-mini",
        prompt_tokens=40,
        completion_tokens=20,
        duration=1.5
    )
    TelemetryTracker.log_llm_call(
        model="gpt-4o-mini",
        prompt_tokens=100,
        completion_tokens=50,
        duration=2.5
    )

    TelemetryTracker.log_tool_call(
        tool_name="read_file",
        arguments={"path": "src/main.py"},
        duration=0.2,
        success=True
    )
    TelemetryTracker.log_tool_call(
        tool_name="run_command",
        arguments={"command": "pytest"},
        duration=1.8,
        success=False
    )

    TelemetryTracker.log_command(
        command="git status",
        duration=0.5,
        exit_code=0
    )

    metrics = TelemetryTracker.get_metrics()

    # Assert LLM metrics
    assert metrics["llm"]["total_calls"] == 2
    assert metrics["llm"]["prompt_tokens"] == 140
    assert metrics["llm"]["completion_tokens"] == 70
    assert metrics["llm"]["total_tokens"] == 210
    assert metrics["llm"]["average_duration"] == pytest.approx(2.0)

    # Assert Tool metrics
    assert metrics["tools"]["total_calls"] == 2
    assert metrics["tools"]["success_rate"] == 50.0
    assert metrics["tools"]["average_duration"] == pytest.approx(1.0)
    assert metrics["tools"]["frequencies"]["read_file"] == 1
    assert metrics["tools"]["frequencies"]["run_command"] == 1

    # Assert Command metrics
    assert metrics["commands"]["total_runs"] == 1
    assert metrics["commands"]["average_duration"] == pytest.approx(0.5)


def test_telemetry_tracker_sanitization(temp_telemetry_db):
    """Verify TelemetryTracker redacts sensitive attributes during event logs."""
    sensitive_args = {
        "api_key": "sk-ProjxyzABC123secret",
        "secret_token": "bearer-xyz-12345",
        "password": "super_secret_password",
        "normal_field": "public_data"
    }

    TelemetryTracker.log_tool_call(
        tool_name="auth_service",
        arguments=sensitive_args,
        duration=0.1,
        success=True
    )

    # Query SQLite database record directly to verify redaction on disk
    conn = sqlite3.connect(str(temp_telemetry_db))
    cursor = conn.cursor()
    cursor.execute("SELECT event_data FROM telemetry_events LIMIT 1")
    row = cursor.fetchone()
    conn.close()

    assert row is not None
    data = json.loads(row[0])
    args = data["arguments"]

    # Assert sensitive values are redacted
    assert args["api_key"] == "[REDACTED]"
    assert args["secret_token"] == "[REDACTED]"
    assert args["password"] == "[REDACTED]"
    assert args["normal_field"] == "public_data"


def test_telemetry_tracker_export_and_clear(temp_telemetry_db, tmp_path):
    """Verify exporting telemetry events to JSON and purging them work successfully."""
    # Write some logs
    TelemetryTracker.log_command("ls", 0.1, 0)
    TelemetryTracker.log_llm_call("gpt-4", 10, 10, 1.0)

    export_file = tmp_path / "telemetry_logs.json"

    # Export
    count = TelemetryTracker.export_telemetry(export_file)
    assert count == 2
    assert export_file.exists()

    # Verify JSON content
    with open(export_file, "r", encoding="utf-8") as f:
        records = json.load(f)
    assert len(records) == 2
    assert records[0]["event_type"] == "command"
    assert records[1]["event_type"] == "llm_call"

    # Clear
    TelemetryTracker.clear_telemetry()
    metrics = TelemetryTracker.get_metrics()
    assert metrics["llm"]["total_calls"] == 0
    assert metrics["tools"]["total_calls"] == 0
    assert metrics["commands"]["total_runs"] == 0
