import re
import ast
from pathlib import Path
from typing import List, Dict, Union
from repository import RepositoryExplorer
from reader import FileReader

class SymbolVisitor(ast.NodeVisitor):
    """AST visitor that indexes class and function definitions."""

    def __init__(self):
        self.symbols = []

    def visit_ClassDef(self, node):
        self.symbols.append({
            "type": "class",
            "name": node.name,
            "line": node.lineno
        })
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        self.symbols.append({
            "type": "function",
            "name": node.name,
            "line": node.lineno
        })
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        self.symbols.append({
            "type": "function",
            "name": node.name,
            "line": node.lineno
        })
        self.generic_visit(node)


class BugVisitor(ast.NodeVisitor):
    """AST visitor that flags potential issues (empty exceptions and unsafe eval/exec functions)."""

    def __init__(self):
        self.bugs = []

    def visit_Try(self, node):
        for handler in node.handlers:
            # Check if exception handler body is just a "pass" statement
            if len(handler.body) == 1 and isinstance(handler.body[0], ast.Pass):
                self.bugs.append({
                    "type": "empty_except",
                    "message": "Empty except block catches errors silently.",
                    "line": handler.lineno
                })
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            if node.func.id in ["eval", "exec"]:
                self.bugs.append({
                    "type": "unsafe_eval_exec",
                    "message": f"Use of unsafe function '{node.func.id}()'.",
                    "line": node.lineno
                })
        self.generic_visit(node)


class CodeSearcher:
    """Manages string keyword matching, regular expression searching, AST analysis, and bug audits."""

    def __init__(self, root_path: str = "."):
        self.root_path = Path(root_path).resolve()
        self.explorer = RepositoryExplorer(root_path=str(self.root_path))
        self.file_reader = FileReader()

    def search_text(self, query: str, is_regex: bool = False) -> List[Dict[str, Union[str, int]]]:
        """
        Searches files for literal keywords or regex patterns.

        Returns:
            A list of match details: [{"file": path, "line": num, "content": string}]
        """
        files = self.explorer.scan_files()
        matches = []

        if is_regex:
            try:
                # Compile case-insensitive to capture variations
                pattern = re.compile(query, re.IGNORECASE)
            except re.error as e:
                raise ValueError(f"Invalid regular expression: {e}")

        for f in files:
            try:
                content = self.file_reader.read_file(f)
                lines = content.splitlines()
                for idx, line in enumerate(lines, 1):
                    matched = False
                    if is_regex:
                        if pattern.search(line):
                            matched = True
                    else:
                        if query.lower() in line.lower():
                            matched = True

                    if matched:
                        matches.append({
                            "file": f.relative_to(self.root_path).as_posix(),
                            "line": idx,
                            "content": line.strip()
                        })
            except Exception:
                continue
        return matches

    def find_todos(self) -> List[Dict[str, Union[str, int]]]:
        """Queries the workspace for TODO, FIXME, HACK, and BUG comments."""
        query = r"\b(TODO|FIXME|HACK|BUG)\b"
        return self.search_text(query, is_regex=True)

    def find_symbols(self, file_path: Union[str, Path] = None) -> List[Dict[str, Union[str, int]]]:
        """Extracts Python classes and functions from a single target file or the workspace."""
        if file_path is not None:
            files = [Path(file_path).resolve()]
        else:
            files = [f for f in self.explorer.scan_files() if f.suffix == ".py"]

        symbols = []
        for f in files:
            if not f.exists() or f.suffix != ".py":
                continue
            try:
                content = self.file_reader.read_file(f)
                tree = ast.parse(content, filename=str(f))
                visitor = SymbolVisitor()
                visitor.visit(tree)
                for sym in visitor.symbols:
                    symbols.append({
                        "file": f.relative_to(self.root_path).as_posix(),
                        "type": sym["type"],
                        "name": sym["name"],
                        "line": sym["line"]
                    })
            except Exception:
                continue
        return symbols

    def find_bugs(self, file_path: Union[str, Path] = None) -> List[Dict[str, Union[str, int]]]:
        """Scans Python files to identify empty catch handlers or unsafe function evaluations."""
        if file_path is not None:
            files = [Path(file_path).resolve()]
        else:
            files = [f for f in self.explorer.scan_files() if f.suffix == ".py"]

        bugs = []
        for f in files:
            if not f.exists() or f.suffix != ".py":
                continue
            try:
                content = self.file_reader.read_file(f)
                tree = ast.parse(content, filename=str(f))
                visitor = BugVisitor()
                visitor.visit(tree)
                for bug in visitor.bugs:
                    bugs.append({
                        "file": f.relative_to(self.root_path).as_posix(),
                        "type": bug["type"],
                        "message": bug["message"],
                        "line": bug["line"]
                    })
            except Exception:
                continue
        return bugs
