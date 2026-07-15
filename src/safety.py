import json
import shlex
from pathlib import Path
from typing import Dict, Any, List, Optional

class SecurityError(Exception):
    """Raised when an operation violates security policies."""
    pass

class SecurityPolicy:
    """Manages agent execution safety policies, thresholds, and confirmations."""

    def __init__(self, policy_path: str = "config/security_policy.json", workspace_root: str = "."):
        self.policy_path = Path(policy_path)
        self.workspace_root = Path(workspace_root).resolve()
        
        # Default policy configurations
        self.allowed_commands: List[str] = []
        self.blocked_commands: List[str] = [
            "del", "rmdir", "mkfs", "dd", "shutdown", "reboot",
            "format", "chown", "chmod", "kill", "poweroff"
        ]
        self.require_user_confirmation: bool = False
        self.max_file_size_bytes: int = 1048576  # 1MB limit
        self.blocked_file_extensions: List[str] = [
            ".exe", ".dll", ".bin", ".sh", ".bat", ".cmd", ".so", ".dylib"
        ]
        
        self.load_policy()

    def load_policy(self):
        """Loads safety configurations from config file if it exists."""
        if self.policy_path.exists():
            try:
                with open(self.policy_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                self.allowed_commands = data.get("allowed_commands", self.allowed_commands)
                self.blocked_commands = data.get("blocked_commands", self.blocked_commands)
                self.require_user_confirmation = data.get("require_user_confirmation", self.require_user_confirmation)
                self.max_file_size_bytes = data.get("max_file_size_bytes", self.max_file_size_bytes)
                self.blocked_file_extensions = data.get("blocked_file_extensions", self.blocked_file_extensions)
            except Exception:
                pass

    def save_policy(self):
        """Persists the current security configuration back to the JSON file."""
        self.policy_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.policy_path, "w", encoding="utf-8") as f:
                json.dump({
                    "allowed_commands": self.allowed_commands,
                    "blocked_commands": self.blocked_commands,
                    "require_user_confirmation": self.require_user_confirmation,
                    "max_file_size_bytes": self.max_file_size_bytes,
                    "blocked_file_extensions": self.blocked_file_extensions
                }, f, indent=4)
        except Exception:
            pass

    def validate_command(self, command: str):
        """
        Validates command safety. Checks against blacklist, whitelist, and dangerous parameters.
        Raises SecurityError if blocked.
        """
        cmd = command.strip()
        if not cmd:
            raise SecurityError("Command string is empty.")

        try:
            parts = shlex.split(cmd)
        except ValueError:
            parts = cmd.split()

        if not parts:
            raise SecurityError("Command parses to empty parts.")

        binary = Path(parts[0]).name.lower()
        for ext in [".exe", ".bat", ".cmd", ".ps1"]:
            if binary.endswith(ext):
                binary = binary[:-len(ext)]
                break

        # Check blacklist
        if binary in self.blocked_commands or parts[0].lower() in self.blocked_commands:
            raise SecurityError(f"Security Policy: Execution of command binary '{parts[0]}' is explicitly blocked.")

        # Check whitelist (if active)
        if self.allowed_commands:
            if not (binary in self.allowed_commands or parts[0] in self.allowed_commands):
                raise SecurityError(f"Security Policy: Command binary '{parts[0]}' is not whitelisted.")

        # Check dangerous parameter patterns (like rm -rf /)
        cmd_lower = cmd.lower()
        if "rm " in cmd_lower and "-rf" in cmd_lower and "/" in cmd_lower:
            raise SecurityError("Security Policy: recursive root deletion attempt ('rm -rf /') blocked.")

    def validate_file_modification(self, file_path: Path):
        """
        Enforces safe file boundaries:
        1. Paths must remain strictly within workspace root (prevent traversal).
        2. File extension must not be in blocked extensions list.
        3. File size must not exceed max threshold.
        """
        resolved_path = Path(file_path).resolve()
        
        # 1. Workspace containment check (prevents path traversals)
        try:
            resolved_path.relative_to(self.workspace_root)
        except ValueError:
            raise SecurityError(f"Security Policy: Path traversal detected. '{file_path}' is outside the workspace root.")

        # 2. Blocked file extensions
        if resolved_path.suffix.lower() in self.blocked_file_extensions:
            raise SecurityError(f"Security Policy: Modification of files with extension '{resolved_path.suffix}' is blocked.")

        # 3. File size constraints (only checks existing files)
        if resolved_path.exists():
            try:
                size = resolved_path.stat().st_size
                if size > self.max_file_size_bytes:
                    raise SecurityError(
                        f"Security Policy: File '{resolved_path.name}' exceeds the maximum allowed size limit "
                        f"({size} > {self.max_file_size_bytes} bytes)."
                    )
            except SecurityError:
                raise
            except Exception as e:
                raise SecurityError(f"Security Policy: Failed to query file stats for '{resolved_path.name}': {e}")
