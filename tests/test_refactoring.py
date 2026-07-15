import pytest
import os
from pathlib import Path
from unittest.mock import patch
from refactoring import CodeValidator, RefactoringTransaction

def test_code_validator_syntax():
    """Verify CodeValidator flags syntax errors but passes valid code."""
    valid_code = "def add(a, b):\n    return a + b\n"
    invalid_code = "def add(a, b:\n    return a + b\n"

    assert CodeValidator.validate_syntax(valid_code) is None
    assert CodeValidator.validate_syntax(invalid_code) is not None
    assert "SyntaxError" in CodeValidator.validate_syntax(invalid_code)

def test_code_validator_imports(tmp_path):
    """Verify CodeValidator resolves absolute/relative imports and reports unresolved ones."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    src_dir = workspace / "src"
    src_dir.mkdir()

    # Create dummy modules
    (src_dir / "helper.py").write_text("class Helper: pass", encoding="utf-8")
    (src_dir / "llm").mkdir()
    (src_dir / "llm" / "client.py").write_text("class Client: pass", encoding="utf-8")
    (src_dir / "llm" / "openai.py").write_text("from .client import Client", encoding="utf-8")

    # Code under test
    test_code = """
import sys
import os
from helper import Helper
from llm.client import Client
from .openai import OpenAI
from unresolved_module import Broken
"""

    file_path = src_dir / "llm" / "openai.py"
    unresolved = CodeValidator.validate_imports(test_code, file_path, workspace)

    # Check findings: unresolved_module should be reported as unresolved
    # Whereas sys, os, helper, llm.client, and .openai should resolve successfully
    assert len(unresolved) == 1
    assert "unresolved_module" in unresolved[0]

def test_refactoring_transaction_success(tmp_path):
    """Verify RefactoringTransaction commits edits to multiple files atomically."""
    # Setup temp files
    file1 = tmp_path / "file1.py"
    file2 = tmp_path / "file2.py"
    file1.write_text("def first():\n    return 'original'\n", encoding="utf-8")
    file2.write_text("def second():\n    return 'original'\n", encoding="utf-8")

    transaction = RefactoringTransaction(workspace_root=str(tmp_path))
    transaction.add_edit("file1.py", "'original'", "'modified1'")
    transaction.add_edit("file2.py", "'original'", "'modified2'")

    res = transaction.execute(validate=True)
    assert res["status"] == "success"
    assert "file1.py" in res["modified_files"][0] or "file1.py" in res["modified_files"][1]

    # Verify content changes committed to disk
    assert "modified1" in file1.read_text(encoding="utf-8")
    assert "modified2" in file2.read_text(encoding="utf-8")

    # Clean up backups
    transaction.editor.undo(file1)
    transaction.editor.undo(file2)

def test_refactoring_transaction_validation_error(tmp_path):
    """Verify that validation errors abort the transaction and do not modify disk files."""
    file1 = tmp_path / "file1.py"
    file1.write_text("def first():\n    return 'original'\n", encoding="utf-8")

    transaction = RefactoringTransaction(workspace_root=str(tmp_path))
    # Add edit that introduces syntax error (missing quote)
    transaction.add_edit("file1.py", "'original'", "'modified")

    with pytest.raises(ValueError) as exc_info:
        transaction.execute(validate=True)

    assert "Validation failed" in str(exc_info.value)
    # File content on disk must remain unchanged
    assert "original" in file1.read_text(encoding="utf-8")
    assert "modified" not in file1.read_text(encoding="utf-8")

def test_refactoring_transaction_rollback_on_write_error(tmp_path):
    """Verify that a write error mid-transaction rolls back already written files."""
    file1 = tmp_path / "file1.py"
    file2 = tmp_path / "file2.py"
    file1.write_text("original1", encoding="utf-8")
    file2.write_text("original2", encoding="utf-8")

    transaction = RefactoringTransaction(workspace_root=str(tmp_path))
    transaction.add_edit("file1.py", "original1", "modified1")
    transaction.add_edit("file2.py", "original2", "modified2")

    # Mock python open to raise error when writing to file2, but succeed for file1
    original_open = open
    def mock_open(file, mode='r', *args, **kwargs):
        if str(Path(file).name) == "file2.py" and 'w' in mode:
            raise IOError("Simulated disk error writing file2")
        return original_open(file, mode, *args, **kwargs)

    with patch("builtins.open", side_effect=mock_open):
        with pytest.raises(RuntimeError) as exc_info:
            transaction.execute(validate=False)

    assert "Rolled back" in str(exc_info.value)
    # Verify both files are in their original state on disk
    assert file1.read_text(encoding="utf-8") == "original1"
    assert file2.read_text(encoding="utf-8") == "original2"
