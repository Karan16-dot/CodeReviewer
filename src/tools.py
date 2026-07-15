import subprocess
import json
from pathlib import Path
from typing import Dict, Any, Callable, List, Optional
from reader import FileReader
from editor import FileEditor
from repository import RepositoryExplorer
from search import CodeSearcher

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
        try:
            return str(self.tools[name](**arguments))
        except TypeError as e:
            return f"Error invoking tool '{name}': {e}"
        except Exception as e:
            return f"Error executing tool '{name}': {e}"


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
    """Executes a terminal shell command on the host system and returns output."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        output = []
        if result.stdout:
            output.append(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            output.append(f"STDERR:\n{result.stderr}")
        if not output:
            output.append("Command executed with no output.")
        output.append(f"Exit Code: {result.returncode}")
        return "\n".join(output)
    except subprocess.TimeoutExpired:
        return "Error: Command execution timed out after 30 seconds."
    except Exception as e:
        return f"Error running command: {e}"


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

# Initialize and populate the global registry
tool_registry = ToolRegistry()
tool_registry.register("read_file", read_file, READ_FILE_SCHEMA)
tool_registry.register("write_file", write_file, WRITE_FILE_SCHEMA)
tool_registry.register("search_files", search_files, SEARCH_FILES_SCHEMA)
tool_registry.register("list_directory", list_directory, LIST_DIRECTORY_SCHEMA)
tool_registry.register("run_command", run_command, RUN_COMMAND_SCHEMA)
