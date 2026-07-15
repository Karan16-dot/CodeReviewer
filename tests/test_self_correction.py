import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from self_correction import TracebackParser, SelfCorrectionOrchestrator

def test_traceback_parser():
    """Verify TracebackParser extracts files and lines while ignoring internal stdlib paths."""
    tb_output = """
Traceback (most recent call last):
  File "C:\\Python39\\lib\\unittest\\case.py", line 59, in test_something
    self.run()
  File "src\\calculator.py", line 12, in add
    result = a + b
  File "C:\\Projects\\CodeReviewer\\venv\\lib\\site-packages\\pytest.py", line 102, in main
    sys.exit(0)
TypeError: unsupported operand type(s) for +: 'int' and 'str'
"""
    results = TracebackParser.parse_traceback(tb_output)

    # Standard lib paths and site-packages should be filtered out.
    # Only "src/calculator.py" at line 12 should remain.
    assert len(results) == 1
    assert "calculator.py" in results[0]["file"]
    assert results[0]["line"] == 12

def test_self_correction_success_directly(tmp_path):
    """Verify orchestrator returns success directly if the initial command runs cleanly."""
    mock_client = MagicMock()
    orchestrator = SelfCorrectionOrchestrator(client=mock_client, workspace_root=str(tmp_path))

    with patch.object(orchestrator.runner, "run", return_value=("Tests Passed", "", 0)) as mock_run:
        res = orchestrator.run_command_with_correction("pytest", max_retries=3)

        assert res["status"] == "success"
        assert res["retries"] == 0
        assert "Tests Passed" in res["output"]
        mock_run.assert_called_once_with("pytest")
        mock_client.stream_chat.assert_not_called()

def test_self_correction_loop_fixes_error(tmp_path):
    """Verify orchestrator runs correction loops, applies LLM search-and-replaces, and succeeds on retry."""
    # Write a dummy script to modify
    script = tmp_path / "script.py"
    script.write_text("def run():\n    return 42\n", encoding="utf-8")

    mock_client = MagicMock()
    # LLM yields search-and-replace chunk
    mock_client.stream_chat.return_value = [
        "<<<<\nreturn 42\n====\nreturn 100\n>>>>"
    ]

    orchestrator = SelfCorrectionOrchestrator(client=mock_client, workspace_root=str(tmp_path))

    # Mock CommandRunner to:
    # 1. Fail first run, returning traceback pointing to script.py
    # 2. Succeed second run
    tb_error = f'File "{script.resolve()}", line 2, in run\nAssertionError: 42 != 100'
    mock_run = MagicMock(side_effect=[
        ("Error occurred", tb_error, 1),
        ("Success output", "", 0)
    ])

    with patch.object(orchestrator.runner, "run", mock_run):
        res = orchestrator.run_command_with_correction("python script.py", max_retries=2)

        assert res["status"] == "success"
        assert res["retries"] == 1
        assert "Success output" in res["output"]
        
        # Verify file on disk was modified by the correction patch
        assert "return 100" in script.read_text(encoding="utf-8")
        assert "return 42" not in script.read_text(encoding="utf-8")

def test_self_correction_loop_exhausts_retries(tmp_path):
    """Verify orchestrator returns failure and aborts when retries limit is exceeded."""
    script = tmp_path / "script.py"
    script.write_text("def run():\n    return 42\n", encoding="utf-8")

    mock_client = MagicMock()
    mock_client.stream_chat.return_value = [
        "<<<<\nreturn 42\n====\nreturn 100\n>>>>"
    ]

    orchestrator = SelfCorrectionOrchestrator(client=mock_client, workspace_root=str(tmp_path))
    orchestrator.editor = MagicMock()

    # Always return failure
    tb_error = f'File "{script.resolve()}", line 2, in run\nAssertionError: 42 != 100'
    mock_run = MagicMock(return_value=("Still broken", tb_error, 1))

    with patch.object(orchestrator.runner, "run", mock_run):
        res = orchestrator.run_command_with_correction("python script.py", max_retries=2)

        assert res["status"] == "failure"
        assert res["retries"] == 2
        assert "Failed after 2 self-correction retries" in res["output"]
