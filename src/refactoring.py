import ast
import sys
import importlib.util
from pathlib import Path
from typing import List, Dict, Any, Optional
from editor import FileEditor

class CodeValidator:
    """Provides syntax parsing and local imports validation using AST analysis."""

    @staticmethod
    def validate_syntax(code: str) -> Optional[str]:
        """Parses Python code using AST. Returns syntax error message if invalid, else None."""
        try:
            ast.parse(code)
            return None
        except SyntaxError as e:
            return f"SyntaxError at line {e.lineno}, offset {e.offset}: {e.msg}"
        except Exception as e:
            return f"Parsing Error: {e}"

    @staticmethod
    def validate_imports(code: str, file_path: Path, workspace_root: Path) -> List[str]:
        """
        Parses AST to find import statements and checks if they are resolvable.
        Returns a list of unresolved import statements.
        """
        try:
            tree = ast.parse(code)
        except Exception:
            return ["Syntax error prevents import validation."]

        unresolved = []
        workspace_root = Path(workspace_root).resolve()
        file_path = Path(file_path).resolve()
        
        # Search paths for local imports
        search_paths = [workspace_root, workspace_root / "src"]
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name
                    if not CodeValidator._is_resolvable(name, search_paths):
                        unresolved.append(f"import {name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module
                level = node.level
                
                # Check relative import (level > 0)
                if level > 0:
                    current_dir = file_path.parent.resolve()
                    rel_origin = current_dir
                    for _ in range(level - 1):
                        rel_origin = rel_origin.parent
                    
                    if module:
                        mod_parts = module.split('.')
                        target_path = rel_origin.joinpath(*mod_parts)
                    else:
                        target_path = rel_origin
                        
                    # Check file.py or folder exists
                    if not (target_path.with_suffix(".py").exists() or target_path.is_dir()):
                        unresolved.append(f"from {'.' * level}{module or ''} import ...")
                else:
                    # Absolute import
                    if module:
                        if not CodeValidator._is_resolvable(module, search_paths):
                            unresolved.append(f"from {module} import ...")

        return unresolved

    @staticmethod
    def _is_resolvable(module_name: str, search_paths: List[Path]) -> bool:
        """Helper checking if a module resolves via standard sys.path or local search_paths."""
        base_name = module_name.split('.')[0]
        
        # 1. Try standard library or installed packages
        try:
            spec = importlib.util.find_spec(base_name)
            if spec is not None:
                return True
        except Exception:
            pass

        # 2. Check local workspace search paths
        for path in search_paths:
            candidate_file = path / f"{base_name}.py"
            candidate_dir = path / base_name
            if candidate_file.exists() or candidate_dir.is_dir():
                return True

        return False


class RefactoringTransaction:
    """Manages refactoring edits across multiple files in a single validated atomic transaction."""

    def __init__(self, workspace_root: str = "."):
        self.workspace_root = Path(workspace_root).resolve()
        self.editor = FileEditor()
        self.edits: Dict[str, List[Dict[str, str]]] = {}
        self.applied_backups: Dict[str, Optional[Path]] = {}

    def add_edit(self, file_path: str, search_block: str, replace_block: str):
        """Adds a search-and-replace block edit for a file."""
        abs_path = str(Path(self.workspace_root / file_path).resolve())
        if abs_path not in self.edits:
            self.edits[abs_path] = []
        self.edits[abs_path].append({
            "search": search_block,
            "replace": replace_block
        })

    def dry_run(self, validate: bool = True) -> Dict[str, Any]:
        """
        Evaluates enqueued edits in-memory and validates them.
        Returns a dictionary containing proposed_contents, diffs, and list of modified files.
        """
        if not self.edits:
            return {"proposed_contents": {}, "diffs": {}, "modified_files": []}

        proposed_contents = {}
        diffs = {}

        # 1. Evaluate modifications in-memory
        for path_str, file_edits in self.edits.items():
            path = Path(path_str)
            if not path.exists():
                raise FileNotFoundError(f"File to refactor does not exist: {path_str}")

            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()

                for edit in file_edits:
                    count = content.count(edit["search"])
                    if count == 0:
                        raise ValueError(f"Search block not found in {path.name}.")
                    if count > 1:
                        raise ValueError(f"Search block matches {count} occurrences in {path.name}.")
                    content = content.replace(edit["search"], edit["replace"])

                proposed_contents[path_str] = content
                diffs[path_str] = self.editor.get_diff(path, content)
            except Exception as e:
                raise RuntimeError(f"Refactoring dry-run failed for {path.name}: {e}")

        # 2. Validate proposed modifications
        if validate:
            for path_str, proposed_code in proposed_contents.items():
                path = Path(path_str)
                
                # Check syntax
                syntax_err = CodeValidator.validate_syntax(proposed_code)
                if syntax_err:
                    raise ValueError(f"Validation failed for {path.name}: {syntax_err}")

                # Check imports (Python files only)
                if path.suffix == ".py":
                    unresolved = CodeValidator.validate_imports(proposed_code, path, self.workspace_root)
                    if unresolved:
                        raise ValueError(
                            f"Validation failed for {path.name}: Unresolved imports:\n" +
                            "\n".join(f"  - {imp}" for imp in unresolved)
                        )

        return {
            "proposed_contents": proposed_contents,
            "diffs": diffs,
            "modified_files": list(proposed_contents.keys())
        }

    def commit(self, proposed_contents: Dict[str, str]) -> List[str]:
        """
        Writes proposed contents to disk atomically, with backup safety and automatic rollback.
        """
        written_paths = []
        try:
            for path_str, content in proposed_contents.items():
                path = Path(path_str)
                # Create backup
                self.editor.backup(path)
                self.applied_backups[path_str] = self.editor.backups.get(path_str)

                # Write content
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                written_paths.append(path_str)
            return written_paths
        except Exception as e:
            # Transaction roll back!
            for path_str in written_paths:
                path = Path(path_str)
                backup_path = self.applied_backups.get(path_str)
                if backup_path and backup_path.exists():
                    import shutil
                    shutil.copy2(backup_path, path)
            raise RuntimeError(f"Failed to commit transaction changes. Rolled back. Error: {e}")

    def execute(self, validate: bool = True) -> Dict[str, Any]:
        """
        Executes and commits all enqueued edits atomically.
        """
        res = self.dry_run(validate=validate)
        self.commit(res["proposed_contents"])
        return {
            "status": "success",
            "modified_files": res["modified_files"],
            "diffs": res["diffs"]
        }
