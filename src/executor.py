import subprocess
import shlex
import os
from pathlib import Path
from typing import Generator, List

class SecurityError(Exception):
    """Raised when a command violates execution security policies."""
    pass

class CommandRunner:
    """Handles command execution with security restrictions and real-time streaming output."""

    # Unsafe command keywords/sub-commands we want to restrict for safety
    BLOCKED_COMMANDS = {
        "rmdir", "del", "mkfs", "dd", "shutdown", "reboot",
        "format", "chown", "chmod"
    }

    def __init__(self, workspace_root: str = "."):
        self.workspace_root = Path(workspace_root).resolve()

    def sanitize_command(self, command: str) -> List[str]:
        """
        Parses and verifies command security safety.
        Raises SecurityError if command tries to execute blocked binaries or dangerous parameters.
        """
        try:
            parts = shlex.split(command)
        except ValueError:
            parts = command.split()

        if not parts:
            raise SecurityError("Command is empty.")

        # Check blocked executable binary names (e.g. rmdir)
        binary = Path(parts[0]).name.lower()
        if binary.endswith((".exe", ".bat", ".cmd", ".ps1")):
            binary = binary.rsplit(".", 1)[0]

        if binary in self.BLOCKED_COMMANDS:
            raise SecurityError(f"Security Policy: Execution of '{parts[0]}' is blocked.")

        # Specific dangerous argument patterns check (like rm -rf /)
        cmd_lower = command.lower()
        if "rm " in cmd_lower and "-rf" in cmd_lower and "/" in cmd_lower:
            raise SecurityError("Security Policy: Blocked recursive root deletion.")

        return parts

    def run_streaming(self, command: str, timeout: float = 60.0) -> Generator[str, None, None]:
        """
        Executes a command and yields stdout/stderr in real-time.

        Yields:
            Lines of output as they are printed by the subprocess.
        """
        try:
            self.sanitize_command(command)
        except SecurityError as e:
            yield f"Error: {e}"
            return

        cwd = str(self.workspace_root)

        # Set up env path to prioritize virtualenv venv/Scripts or venv/bin
        env = os.environ.copy()
        venv_bin = self.workspace_root / "venv" / "Scripts"
        if not venv_bin.exists():
            venv_bin = self.workspace_root / "venv" / "bin"

        if venv_bin.exists():
            env["PATH"] = str(venv_bin) + os.pathsep + env.get("PATH", "")

        try:
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=cwd,
                env=env,
                bufsize=1  # Line buffered
            )

            # Read stdout line by line
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    yield line

            process.stdout.close()
            return_code = process.wait(timeout=timeout)
            yield f"\nExit Code: {return_code}"

        except subprocess.TimeoutExpired:
            process.kill()
            yield "\nError: Process timed out and was terminated after exceeding limits."
        except Exception as e:
            yield f"\nError running process: {e}"
