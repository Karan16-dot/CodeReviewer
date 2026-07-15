import shutil
import hashlib
import difflib
from pathlib import Path
from typing import Dict, Optional
from safety import SecurityPolicy, SecurityError

class FileEditor:
    """Manages file edits with automatic backups, diffing, search-and-replace patches, and undos."""

    def __init__(self, backup_dir: str = ".backup", workspace_root: str = "."):
        self.backup_dir = Path(backup_dir).resolve()
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.backups: Dict[str, Optional[Path]] = {}
        self.policy = SecurityPolicy(workspace_root=workspace_root)

    def get_backup_path(self, file_path: Path) -> Path:
        """Generates a unique backup filename using the target path's MD5 hash."""
        path_hash = hashlib.md5(str(file_path.resolve()).encode("utf-8")).hexdigest()
        return self.backup_dir / f"{file_path.name}_{path_hash}.bak"

    def backup(self, file_path: Path) -> bool:
        """Copies the target file to the backup directory. Returns True if successful."""
        file_path = Path(file_path).resolve()
        if not file_path.exists():
            return False

        backup_path = self.get_backup_path(file_path)
        try:
            shutil.copy2(file_path, backup_path)
            self.backups[str(file_path)] = backup_path
            return True
        except Exception as e:
            raise IOError(f"Failed to create backup of {file_path}: {e}")

    def write(self, file_path: Path, content: str) -> None:
        """Safely writes content to a file, making a backup if it exists beforehand."""
        file_path = Path(file_path).resolve()

        # Enforce safety constraints
        self.policy.validate_file_modification(file_path)
        content_size = len(content.encode("utf-8"))
        if content_size > self.policy.max_file_size_bytes:
            raise SecurityError(
                f"Security Policy: Proposed write content size ({content_size} bytes) exceeds limit "
                f"({self.policy.max_file_size_bytes} bytes)."
            )

        if file_path.exists():
            self.backup(file_path)
        else:
            # If the file didn't exist, record None so undo can delete it
            self.backups[str(file_path)] = None

        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            raise IOError(f"Failed to write content to file {file_path}: {e}")

    def get_diff(self, file_path: Path, new_content: str) -> str:
        """Generates a unified diff comparing the current file content to the proposed content."""
        file_path = Path(file_path).resolve()
        original_content = ""

        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    original_content = f.read()
            except Exception:
                pass

        original_lines = original_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)

        diff = difflib.unified_diff(
            original_lines,
            new_lines,
            fromfile=f"a/{file_path.name}",
            tofile=f"b/{file_path.name}",
            lineterm=""
        )
        return "\n".join(diff)

    def apply_replacement(self, file_path: Path, search_block: str, replace_block: str) -> str:
        """
        Loads the file and replaces search_block with replace_block.
        Does not save to disk, returns modified content string.

        Raises:
            ValueError: If search block is not found or matches multiple segments.
        """
        file_path = Path(file_path).resolve()

        # Enforce safety constraints
        self.policy.validate_file_modification(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found for editing: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        count = content.count(search_block)
        if count == 0:
            raise ValueError("Target search block not found in the file.")
        if count > 1:
            raise ValueError(
                f"Target search block matches {count} occurrences in the file. "
                "Make the search block more specific."
            )

        return content.replace(search_block, replace_block)

    def undo(self, file_path: Path) -> bool:
        """
        Rolls back the target file to its backed-up state.
        Deletes the file if it was created during the session.
        """
        file_path = Path(file_path).resolve()
        if str(file_path) not in self.backups:
            return False

        backup_path = self.backups[str(file_path)]

        # If backup path is None, it means the file was created anew. Undo means deleting it.
        if backup_path is None:
            try:
                if file_path.exists():
                    file_path.unlink()
                self.backups.pop(str(file_path))
                return True
            except Exception as e:
                raise IOError(f"Failed to delete newly created file {file_path}: {e}")

        if not backup_path.exists():
            return False

        try:
            shutil.copy2(backup_path, file_path)
            backup_path.unlink()
            self.backups.pop(str(file_path))
            return True
        except Exception as e:
            raise IOError(f"Failed to restore file {file_path} from backup: {e}")
