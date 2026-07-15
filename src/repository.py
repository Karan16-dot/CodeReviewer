from pathlib import Path
from typing import Set, Dict, List

class RepositoryExplorer:
    """Explores directory hierarchies, detects file languages, and constructs text trees."""

    # Standard mapping of file extensions to programming languages
    LANGUAGE_MAP = {
        ".py": "Python",
        ".js": "JavaScript",
        ".ts": "TypeScript",
        ".html": "HTML",
        ".css": "CSS",
        ".json": "JSON",
        ".md": "Markdown",
        ".txt": "Plain Text",
        ".sh": "Shell Script",
        ".bat": "Batch File",
        ".ps1": "PowerShell Script",
        ".yaml": "YAML",
        ".yml": "YAML",
        ".ini": "Configuration",
        ".toml": "TOML",
        ".xml": "XML",
        ".sql": "SQL",
        ".rs": "Rust",
        ".go": "Go",
        ".c": "C",
        ".cpp": "C++",
        ".h": "C Header",
        ".java": "Java"
    }

    def __init__(self, root_path: str = ".", ignore_patterns: Set[str] = None):
        self.root_path = Path(root_path).resolve()
        # Default ignore patterns
        self.ignore_patterns = ignore_patterns if ignore_patterns is not None else {
            ".git", "node_modules", "venv", ".venv", "__pycache__",
            ".pytest_cache", ".idea", ".vscode", "build", "dist"
        }

    def is_ignored(self, path: Path) -> bool:
        """Determines if a path should be ignored based on ignore patterns."""
        try:
            relative = path.relative_to(self.root_path)
        except ValueError:
            relative = path

        for part in relative.parts:
            if part in self.ignore_patterns:
                return True
        return False

    def scan_files(self) -> List[Path]:
        """Scans the repository and returns a list of non-ignored files."""
        if not self.root_path.exists():
            raise FileNotFoundError(f"Directory not found: {self.root_path}")
        if not self.root_path.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {self.root_path}")

        files = []
        for path in self.root_path.rglob("*"):
            if path.is_file() and not self.is_ignored(path):
                files.append(path)
        return sorted(files)

    def count_files_by_language(self) -> Dict[str, int]:
        """Counts files and aggregates them by detected language."""
        counts = {}
        files = self.scan_files()
        for f in files:
            ext = f.suffix.lower()
            lang = self.LANGUAGE_MAP.get(ext, "Unknown")
            counts[lang] = counts.get(lang, 0) + 1
        return counts

    def get_summary_stats(self) -> Dict[str, any]:
        """Returns statistics of the repository."""
        files = self.scan_files()
        lang_counts = self.count_files_by_language()
        return {
            "total_files": len(files),
            "languages": lang_counts
        }

    def build_tree(self) -> str:
        """Generates a text-based visual tree structure of the repository."""
        if not self.root_path.exists():
            raise FileNotFoundError(f"Directory not found: {self.root_path}")
        if not self.root_path.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {self.root_path}")

        tree_str = []

        def _recurse(dir_path: Path, prefix: str = ""):
            contents = []
            try:
                for path in dir_path.iterdir():
                    if not self.is_ignored(path):
                        contents.append(path)
            except PermissionError:
                return

            # Sort contents: directories first, then files alphabetically
            contents.sort(key=lambda x: (not x.is_dir(), x.name.lower()))

            count = len(contents)
            for i, path in enumerate(contents):
                is_last = (i == count - 1)
                connector = "└── " if is_last else "├── "

                tree_str.append(f"{prefix}{connector}{path.name}{'/' if path.is_dir() else ''}")

                if path.is_dir():
                    next_prefix = prefix + ("    " if is_last else "│   ")
                    _recurse(path, next_prefix)

        tree_str.append(f"{self.root_path.name}/")
        _recurse(self.root_path)
        return "\n".join(tree_str)
