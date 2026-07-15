import subprocess
import shlex
import os
from pathlib import Path
from typing import Generator, List, Tuple

from safety import SecurityPolicy, SecurityError

class CommandRunner:
    """Handles command execution with security restrictions and real-time streaming output."""

    def __init__(self, workspace_root: str = "."):
        self.workspace_root = Path(workspace_root).resolve()
        self.policy = SecurityPolicy(workspace_root=str(self.workspace_root))

    def sanitize_command(self, command: str) -> List[str]:
        """
        Parses and verifies command security safety.
        Raises SecurityError if command tries to execute blocked binaries or dangerous parameters.
        """
        self.policy.validate_command(command)
        try:
            return shlex.split(command)
        except ValueError:
            return command.split()

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

    def run(self, command: str, timeout: float = 60.0) -> Tuple[str, str, int]:
        """
        Executes a command synchronously and returns (stdout, stderr, exit_code).
        Raises SecurityError if command is unsafe.
        """
        try:
            self.sanitize_command(command)
        except SecurityError as e:
            return "", f"Security Error: {e}", 1

        cwd = str(self.workspace_root)
        env = os.environ.copy()
        venv_bin = self.workspace_root / "venv" / "Scripts"
        if not venv_bin.exists():
            venv_bin = self.workspace_root / "venv" / "bin"

        if venv_bin.exists():
            env["PATH"] = str(venv_bin) + os.pathsep + env.get("PATH", "")

        import time
        from telemetry import TelemetryTracker
        start_time = time.time()
        exit_code = 0
        try:
            res = subprocess.run(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=cwd,
                env=env,
                timeout=timeout
            )
            exit_code = res.returncode
            return res.stdout, res.stderr, res.returncode
        except subprocess.TimeoutExpired as e:
            exit_code = 1
            stdout = e.stdout if isinstance(e.stdout, str) else ""
            stderr = e.stderr if isinstance(e.stderr, str) else ""
            return stdout, stderr + "\nError: Process timed out.", 1
        except Exception as e:
            exit_code = 1
            return "", f"Error running command: {e}", 1
        finally:
            duration = time.time() - start_time
            TelemetryTracker.log_command(command, duration=duration, exit_code=exit_code)
