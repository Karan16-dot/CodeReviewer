import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from safety import SecurityPolicy, SecurityError
from executor import CommandRunner
from editor import FileEditor

def test_security_policy_command_blacklist():
    """Verify SecurityPolicy blocks blacklisted command names."""
    policy = SecurityPolicy()
    # "del" is in default blocked commands
    with pytest.raises(SecurityError) as exc_info:
        policy.validate_command("del file.txt")
    assert "explicitly blocked" in str(exc_info.value)

    # Clean commands should pass validation
    policy.validate_command("git status")

def test_security_policy_command_whitelist():
    """Verify SecurityPolicy blocks non-whitelisted commands when active."""
    policy = SecurityPolicy()
    policy.allowed_commands = ["git", "pytest"]

    # "git status" is whitelisted
    policy.validate_command("git status")

    # "python main.py" is not whitelisted, should fail
    with pytest.raises(SecurityError) as exc_info:
        policy.validate_command("python main.py")
    assert "not whitelisted" in str(exc_info.value)

def test_security_policy_dangerous_args():
    """Verify SecurityPolicy catches dangerous parameter pattern combinations."""
    policy = SecurityPolicy()
    with pytest.raises(SecurityError) as exc_info:
        policy.validate_command("rm -rf /")
    assert "recursive root deletion" in str(exc_info.value)

def test_security_policy_file_traversal(tmp_path):
    """Verify SecurityPolicy detects and blocks path traversal attempts outside workspace."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    
    policy = SecurityPolicy(workspace_root=str(workspace))

    # Path inside workspace should pass
    policy.validate_file_modification(workspace / "src" / "code.py")

    # Path outside workspace should fail
    outside_file = tmp_path / "outside.py"
    with pytest.raises(SecurityError) as exc_info:
        policy.validate_file_modification(outside_file)
    assert "outside the workspace root" in str(exc_info.value)

def test_security_policy_file_extensions():
    """Verify SecurityPolicy blocks changes to denied file extensions."""
    policy = SecurityPolicy()
    with pytest.raises(SecurityError) as exc_info:
        policy.validate_file_modification(Path("src/exploit.exe"))
    assert "extension '.exe' is blocked" in str(exc_info.value)

def test_security_policy_file_size(tmp_path):
    """Verify SecurityPolicy blocks modifications to files exceeding size limit thresholds."""
    policy = SecurityPolicy(workspace_root=str(tmp_path))
    policy.max_file_size_bytes = 100  # Set low limit

    large_file = tmp_path / "large.py"
    large_file.write_text("a" * 200, encoding="utf-8")

    with pytest.raises(SecurityError) as exc_info:
        policy.validate_file_modification(large_file)
    assert "exceeds the maximum allowed size" in str(exc_info.value)

def test_file_editor_enforces_safety(tmp_path):
    """Verify FileEditor uses SecurityPolicy checks to block invalid writes."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    editor = FileEditor()
    editor.policy = SecurityPolicy(workspace_root=str(workspace))

    # Should raise error for traversal
    outside = tmp_path / "outside.py"
    with pytest.raises(SecurityError):
        editor.write(outside, "content")

    # Should raise error for size limit
    editor.policy.max_file_size_bytes = 5
    with pytest.raises(SecurityError):
        editor.write(workspace / "large.py", "too_large_content")

def test_command_runner_enforces_safety(tmp_path):
    """Verify CommandRunner uses SecurityPolicy to block command runs."""
    runner = CommandRunner(workspace_root=str(tmp_path))
    
    # Executing blocked command raises SecurityError during streaming setup or run
    stdout, stderr, exit_code = runner.run("del test.py")
    assert exit_code == 1
    assert "Security Error" in stderr
