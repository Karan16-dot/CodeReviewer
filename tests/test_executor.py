import pytest
from executor import CommandRunner, SecurityError

def test_sanitize_command_valid():
    """Verify that safe commands pass sanitization successfully."""
    runner = CommandRunner()
    parts = runner.sanitize_command("git status")
    assert parts == ["git", "status"]

    parts_arg = runner.sanitize_command("echo 'Hello World'")
    assert parts_arg == ["echo", "Hello World"]

def test_sanitize_command_blocked():
    """Verify that unsafe/destructive command binaries raise a SecurityError."""
    runner = CommandRunner()

    with pytest.raises(SecurityError) as exc_info:
        runner.sanitize_command("del file.txt")
    assert "blocked" in str(exc_info.value)

    with pytest.raises(SecurityError) as exc_info:
        runner.sanitize_command("rmdir mydir")
    assert "blocked" in str(exc_info.value)

    # Test blocked binary with extension (Windows style)
    with pytest.raises(SecurityError) as exc_info:
        runner.sanitize_command("shutdown.exe /s")
    assert "blocked" in str(exc_info.value)

def test_sanitize_command_unsafe_args():
    """Verify that dangerous argument signatures raise a SecurityError."""
    runner = CommandRunner()

    with pytest.raises(SecurityError) as exc_info:
        runner.sanitize_command("rm -rf /")
    assert "recursive root deletion" in str(exc_info.value)

def test_run_streaming_success():
    """Verify that running a command yields correct stream outputs and exit status."""
    runner = CommandRunner()
    output = list(runner.run_streaming("echo Hello"))

    # Output list should contain "Hello" and exit status info
    joined = "".join(output)
    assert "Hello" in joined
    assert "Exit Code: 0" in joined

def test_run_streaming_security_block():
    """Verify that blocked commands trigger security error yields without spawning subprocesses."""
    runner = CommandRunner()
    output = list(runner.run_streaming("del hello.txt"))

    joined = "".join(output)
    assert "Error: Security Policy" in joined
    assert "Exit Code" not in joined
