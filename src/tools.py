import subprocess
import json
from pathlib import Path
from typing import Dict, Any, Callable, List, Optional
from reader import FileReader
from editor import FileEditor
from repository import RepositoryExplorer
from search import CodeSearcher
from executor import CommandRunner
from git_manager import GitManager
from refactoring import RefactoringTransaction
from self_correction import SelfCorrectionOrchestrator
from finetuning import FineTuningDataPreparer, FineTuningManager
from github_client import GitHubManager, GitHubError

class ToolRegistry:
    """Registry that houses tool schemas and handles dispatch of tool invocations."""

    def __init__(self):
        self.tools: Dict[str, Callable] = {}
        self.schemas: List[Dict[str, Any]] = []

    def register(self, name: str, func: Callable, schema: Dict[str, Any]):
        self.tools[name] = func
        self.schemas.append({
            "type": "function",
            "function": schema
        })

    def execute(self, name: str, arguments: Dict[str, Any]) -> str:
        """Executes a registered function with arguments and returns result as string."""
        if name not in self.tools:
            return f"Error: Tool '{name}' is not registered."
        import time
        from telemetry import TelemetryTracker
        start_time = time.time()
        success = True
        try:
            res = str(self.tools[name](**arguments))
            return res
        except TypeError as e:
            success = False
            return f"Error invoking tool '{name}': {e}"
        except Exception as e:
            success = False
            return f"Error executing tool '{name}': {e}"
        finally:
            duration = time.time() - start_time
            TelemetryTracker.log_tool_call(
                tool_name=name,
                arguments=arguments,
                duration=duration,
                success=success
            )


# Instantiate global helper services
_reader = FileReader()
_editor = FileEditor()

# Core tool implementations
def read_file(path: str) -> str:
    """Reads the contents of a text file from the workspace."""
    try:
        return _reader.read_file(path)
    except Exception as e:
        return f"Error reading file: {e}"

def write_file(path: str, content: str) -> str:
    """Writes content to a file in the workspace, automatically creating backups."""
    try:
        _editor.write(Path(path), content)
        return f"Successfully wrote file to: {path}"
    except Exception as e:
        return f"Error writing file: {e}"

def search_files(query: str, is_regex: bool = False) -> str:
    """Searches workspace files for literal text keywords or regular expression patterns."""
    try:
        searcher = CodeSearcher()
        matches = searcher.search_text(query, is_regex=is_regex)
        if not matches:
            return "No matches found."

        output = []
        for m in matches:
            output.append(f"{m['file']}:{m['line']}: {m['content']}")
        return "\n".join(output)
    except Exception as e:
        return f"Error searching files: {e}"

def list_directory(path: str = ".") -> str:
    """Lists files and folders in a visual tree layout inside the workspace."""
    try:
        explorer = RepositoryExplorer(root_path=path)
        return explorer.build_tree()
    except Exception as e:
        return f"Error exploring directory: {e}"

def run_command(command: str) -> str:
    """Executes a terminal shell command on the host system, streaming output and returning it."""
    try:
        runner = CommandRunner()
        output = []
        # Run streaming, printing stdout live to the console
        for line in runner.run_streaming(command):
            print(line, end="", flush=True)
            output.append(line)
        return "".join(output)
    except Exception as e:
        return f"Error executing command: {e}"


# Define OpenAI tool schemas
READ_FILE_SCHEMA = {
    "name": "read_file",
    "description": "Reads the contents of a text file from the workspace.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "The path to the file to read (relative to the project root)."
            }
        },
        "required": ["path"]
    }
}

WRITE_FILE_SCHEMA = {
    "name": "write_file",
    "description": "Writes contents to a file in the workspace. Overwrites existing files, automatically creating backups.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "The path to the file to write to."
            },
            "content": {
                "type": "string",
                "description": "The full code/text content to write to the file."
            }
        },
        "required": ["path", "content"]
    }
}

SEARCH_FILES_SCHEMA = {
    "name": "search_files",
    "description": "Searches text files inside the workspace for keywords or regular expression patterns.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The text string or regex pattern to search for."
            },
            "is_regex": {
                "type": "boolean",
                "description": "Set to True if the query is a regular expression pattern. Default is False."
            }
        },
        "required": ["query"]
    }
}

LIST_DIRECTORY_SCHEMA = {
    "name": "list_directory",
    "description": "Lists all non-ignored files and subdirectories in a visual tree layout.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "The directory path to explore (defaults to project root '.')."
            }
        }
    }
}

RUN_COMMAND_SCHEMA = {
    "name": "run_command",
    "description": "Executes a terminal/shell command on the system and returns its output.",
    "parameters": {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The exact shell command line string to run (e.g. 'pytest')."
            }
        },
        "required": ["command"]
    }
}

# Git tool implementations
def git_status() -> str:
    """Returns the current repository status (tracked, untracked, modified, staged)."""
    try:
        mgr = GitManager()
        status = mgr.get_status()
        output = []
        for key, files in status.items():
            if files:
                output.append(f"{key.upper()}:")
                for f in files:
                    output.append(f"  {f}")
        return "\n".join(output) if output else "Repository is clean (no changes)."
    except Exception as e:
        return f"Error fetching git status: {e}"

def git_commit(message: str) -> str:
    """Stages all changes and commits them with the given message."""
    try:
        mgr = GitManager()
        sha = mgr.commit(message)
        return f"Successfully committed changes. Hash: {sha}"
    except Exception as e:
        return f"Error executing git commit: {e}"

def git_diff(file_path: str = None) -> str:
    """Returns the unstaged unified diff of the workspace (or a specific file)."""
    try:
        mgr = GitManager()
        diff = mgr.get_diff(file_path)
        return diff if diff else "No unstaged changes found."
    except Exception as e:
        return f"Error fetching git diff: {e}"

def git_log(limit: int = 5) -> str:
    """Returns recent commit log messages."""
    try:
        mgr = GitManager()
        log = mgr.get_log(limit)
        output = []
        for entry in log:
            output.append(f"[{entry['hash']}] {entry['date']} - {entry['author']}: {entry['message']}")
        return "\n".join(output) if output else "No commit logs found."
    except Exception as e:
        return f"Error fetching git log: {e}"


# Git Schemas
GIT_STATUS_SCHEMA = {
    "name": "git_status",
    "description": "Returns the status of modified, untracked, staged, or deleted files in the git repository.",
    "parameters": {
        "type": "object",
        "properties": {}
    }
}

GIT_COMMIT_SCHEMA = {
    "name": "git_commit",
    "description": "Stages all modified/untracked files and commits them to git with the provided commit message.",
    "parameters": {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "The commit message describing the changes."
            }
        },
        "required": ["message"]
    }
}

GIT_DIFF_SCHEMA = {
    "name": "git_diff",
    "description": "Retrieves the unstaged unified diff of files in the workspace. Filters by file path if provided.",
    "parameters": {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Optional file path relative to repository root to restrict the diff query to."
            }
        }
    }
}

GIT_LOG_SCHEMA = {
    "name": "git_log",
    "description": "Retrieves recent commits from the git log showing hash, author, date, and messages.",
    "parameters": {
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "description": "The max number of commit records to fetch (defaults to 5)."
            }
        }
    }
}

# Memory recall tool implementation
_mem_index = None

def recall_memory(query: str, limit: int = 5) -> str:
    """Searches past conversation memory semantically for relevant user queries or details."""
    global _mem_index
    try:
        if _mem_index is None:
            from llm.openai_client import OpenAIClient
            from memory_index import MemoryIndex
            client = OpenAIClient()
            _mem_index = MemoryIndex(client=client)

        matches = _mem_index.search_semantic(query, limit)
        if not matches:
            return "No matching memories found."

        output = []
        for idx, m in enumerate(matches, 1):
            output.append(f"{idx}. (Score: {m['score']:.2f}) {m['text']}")
        return "\n".join(output)
    except Exception as e:
        return f"Error recalling memory: {e}"


RECALL_MEMORY_SCHEMA = {
    "name": "recall_memory",
    "description": "Searches the conversation history semantically for past topics, user names, preferences, or technical details.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The semantic search query (e.g. 'favorite color' or 'architecture pattern')."
            },
            "limit": {
                "type": "integer",
                "description": "The maximum number of search results to return (defaults to 5)."
            }
        },
        "required": ["query"]
    }
}

# Initialize and populate the global registry
tool_registry = ToolRegistry()
tool_registry.register("read_file", read_file, READ_FILE_SCHEMA)
tool_registry.register("write_file", write_file, WRITE_FILE_SCHEMA)
tool_registry.register("search_files", search_files, SEARCH_FILES_SCHEMA)
tool_registry.register("list_directory", list_directory, LIST_DIRECTORY_SCHEMA)
tool_registry.register("run_command", run_command, RUN_COMMAND_SCHEMA)
tool_registry.register("git_status", git_status, GIT_STATUS_SCHEMA)
tool_registry.register("git_commit", git_commit, GIT_COMMIT_SCHEMA)
tool_registry.register("git_diff", git_diff, GIT_DIFF_SCHEMA)
tool_registry.register("git_log", git_log, GIT_LOG_SCHEMA)
tool_registry.register("recall_memory", recall_memory, RECALL_MEMORY_SCHEMA)

# Refactoring tool implementation
def apply_refactor(edits: List[Dict[str, str]], validate: bool = True) -> str:
    """Applies search-and-replace changes to multiple files simultaneously in an atomic transaction."""
    try:
        transaction = RefactoringTransaction()
        for edit in edits:
            file_path = edit.get("file_path")
            search_block = edit.get("search_block")
            replace_block = edit.get("replace_block")
            if not file_path or search_block is None or replace_block is None:
                return "Error: Each edit must contain 'file_path', 'search_block', and 'replace_block'."
            transaction.add_edit(file_path, search_block, replace_block)

        result = transaction.execute(validate=validate)
        modified_list = ", ".join(Path(p).name for p in result["modified_files"])
        return f"Successfully applied refactoring to: {modified_list}"
    except Exception as e:
        return f"Refactoring transaction failed and rolled back: {e}"


APPLY_REFACTOR_SCHEMA = {
    "name": "apply_refactor",
    "description": "Applies search-and-replace block changes across multiple files atomically. If validation checks fail, rolls back all changes.",
    "parameters": {
        "type": "object",
        "properties": {
            "edits": {
                "type": "array",
                "description": "The list of edits to apply across files.",
                "items": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "The relative path to the file to modify."
                        },
                        "search_block": {
                            "type": "string",
                            "description": "The exact string block to search for."
                        },
                        "replace_block": {
                            "type": "string",
                            "description": "The replacement string block."
                        }
                    },
                    "required": ["file_path", "search_block", "replace_block"]
                }
            },
            "validate": {
                "type": "boolean",
                "description": "If True, runs AST syntax checks and verifies local module imports (defaults to True)."
            }
        },
        "required": ["edits"]
    }
}

tool_registry.register("apply_refactor", apply_refactor, APPLY_REFACTOR_SCHEMA)

# Self-Correction tool implementation
def run_with_self_correction(command: str, max_retries: int = 3) -> str:
    """Runs a shell verification command and self-corrects any errors that arise during execution."""
    try:
        from llm.openai_client import OpenAIClient
        client = OpenAIClient()
        orchestrator = SelfCorrectionOrchestrator(client=client)
        result = orchestrator.run_command_with_correction(command, max_retries=max_retries)

        status = result["status"]
        retries_used = result["retries"]
        output = result["output"]

        summary = f"Run status: {status}\nRetries used: {retries_used}\n"
        if result.get("steps"):
            steps_log = []
            for step in result["steps"]:
                steps_log.append(f" - Step {step['retry']}: Cmd: '{step['command']}' Exit: {step['exit_code']}")
                if "applied_fix" in step:
                    fix = step["applied_fix"]
                    steps_log.append(f"   Applied Fix to {fix['file']}:\n   Search: {fix['search'][:60]}...\n   Replace: {fix['replace'][:60]}...")
            summary += "Correction Steps:\n" + "\n".join(steps_log) + "\n"

        summary += f"\nLast Output:\n{output}"
        return summary
    except Exception as e:
        return f"Self-Correction engine failed: {e}"


RUN_WITH_SELF_CORRECTION_SCHEMA = {
    "name": "run_with_self_correction",
    "description": "Runs a verification command (e.g., pytest, script.py). If it fails, reads the traceback logs, queries the LLM for fixes, applies patches, and retries.",
    "parameters": {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The command string to execute in the workspace."
            },
            "max_retries": {
                "type": "integer",
                "description": "Maximum number of self-correction loop attempts (defaults to 3)."
            }
        },
        "required": ["command"]
    }
}

tool_registry.register("run_with_self_correction", run_with_self_correction, RUN_WITH_SELF_CORRECTION_SCHEMA)

# Fine-Tuning tools implementation
def prepare_finetuning_data(output_path: str) -> str:
    """Exports structured SQLite database conversation histories to JSONL format for model fine-tuning."""
    try:
        db_path = Path("logs/memory.db")
        out_path = Path(output_path)
        count = FineTuningDataPreparer.export_to_jsonl(db_path, out_path)
        return f"Successfully exported {count} conversations for fine-tuning to: {out_path.name}"
    except Exception as e:
        return f"Failed to prepare fine-tuning data: {e}"


def manage_finetuning(action: str, param: str = "") -> str:
    """Manages model fine-tuning jobs (actions: upload, start, status, list)."""
    try:
        from llm.openai_client import OpenAIClient
        client = OpenAIClient()
        manager = FineTuningManager(client=client)

        act = action.lower().strip()
        if act == "upload":
            file_id = manager.upload_file(Path(param))
            return f"Successfully uploaded file. OpenAI File ID: {file_id}"
        elif act == "start":
            job_id = manager.start_job(param)
            return f"Successfully started fine-tuning job. Job ID: {job_id}"
        elif act == "status":
            info = manager.get_job_status(param)
            return (f"Job ID: {info['id']}\n"
                    f"Status: {info['status']}\n"
                    f"Base Model: {info['base_model']}\n"
                    f"Fine-Tuned Model: {info['fine_tuned_model']}\n"
                    f"Trained Tokens: {info['trained_tokens']}")
        elif act == "list":
            jobs = manager.list_jobs()
            if not jobs:
                return "No fine-tuning jobs found."
            output = []
            for j in jobs:
                output.append(f"Job: {j['id']} - Status: {j['status']} - Model: {j['fine_tuned_model']}")
            return "\n".join(output)
        else:
            return f"Unknown fine-tuning action: {action}"
    except Exception as e:
        return f"Fine-tuning action failed: {e}"


PREPARE_FINETUNING_DATA_SCHEMA = {
    "name": "prepare_finetuning_data",
    "description": "Exports conversations from the SQLite log history to a JSON Lines (JSONL) file for model fine-tuning.",
    "parameters": {
        "type": "object",
        "properties": {
            "output_path": {
                "type": "string",
                "description": "The destination path inside the workspace to save the JSONL file."
            }
        },
        "required": ["output_path"]
    }
}

MANAGE_FINETUNING_SCHEMA = {
    "name": "manage_finetuning",
    "description": "Performs actions against the OpenAI Fine-Tuning endpoints (upload, start, status, list).",
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "The target API action: 'upload' (upload file), 'start' (initiate job), 'status' (query status), or 'list' (query jobs)."
            },
            "param": {
                "type": "string",
                "description": "The parameter corresponding to the action (e.g. file path for upload, file ID for start, job ID for status)."
            }
        },
        "required": ["action"]
    }
}

tool_registry.register("prepare_finetuning_data", prepare_finetuning_data, PREPARE_FINETUNING_DATA_SCHEMA)
tool_registry.register("manage_finetuning", manage_finetuning, MANAGE_FINETUNING_SCHEMA)

# GitHub Remote Repository tools implementation
def github_clone(repo_slug: str, dest_path: str, branch: str = "main") -> str:
    """Clones a remote repository structure and files locally using the GitHub API."""
    try:
        manager = GitHubManager()
        count = manager.clone_repository(repo_slug, dest_path, branch)
        return f"Successfully checked out remote repository '{repo_slug}' ({branch}) and downloaded {count} files to: {dest_path}"
    except Exception as e:
        return f"GitHub Checkout failed: {e}"


def github_create_pull_request(repo_slug: str, title: str, body: str, head: str, base: str = "main") -> str:
    """Creates a Pull Request on a remote GitHub repository."""
    try:
        parts = repo_slug.split("/")
        if len(parts) != 2:
            return "Error: Repository slug must be 'owner/repo'."
        owner, repo = parts
        manager = GitHubManager()
        pr_info = manager.create_pull_request(owner, repo, title, body, head, base)
        return f"Successfully created PR #{pr_info.get('number')}! PR URL: {pr_info.get('html_url')}"
    except Exception as e:
        return f"Failed to create PR: {e}"


GITHUB_CLONE_SCHEMA = {
    "name": "github_clone",
    "description": "Clones a remote repository structure and downloads its files using the GitHub API.",
    "parameters": {
        "type": "object",
        "properties": {
            "repo_slug": {
                "type": "string",
                "description": "The GitHub repository slug in the format 'owner/repo'."
            },
            "dest_path": {
                "type": "string",
                "description": "The local path inside the workspace to download files to."
            },
            "branch": {
                "type": "string",
                "description": "The target repository branch name (defaults to 'main')."
            }
        },
        "required": ["repo_slug", "dest_path"]
    }
}

GITHUB_CREATE_PR_SCHEMA = {
    "name": "github_create_pull_request",
    "description": "Creates a Pull Request on a remote GitHub repository.",
    "parameters": {
        "type": "object",
        "properties": {
            "repo_slug": {
                "type": "string",
                "description": "The GitHub repository slug in the format 'owner/repo'."
            },
            "title": {
                "type": "string",
                "description": "The title of the Pull Request."
            },
            "body": {
                "type": "string",
                "description": "The description body text of the Pull Request."
            },
            "head": {
                "type": "string",
                "description": "The branch containing your proposed changes."
            },
            "base": {
                "type": "string",
                "description": "The branch you want to merge your changes into (defaults to 'main')."
            }
        },
        "required": ["repo_slug", "title", "body", "head"]
    }
}

tool_registry.register("github_clone", github_clone, GITHUB_CLONE_SCHEMA)
tool_registry.register("github_create_pull_request", github_create_pull_request, GITHUB_CREATE_PR_SCHEMA)
