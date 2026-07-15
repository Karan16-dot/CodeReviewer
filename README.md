# Claude Code Agent

Claude Code Agent is a robust, modular AI coding assistant built feature-by-feature. It is designed to run locally, interact with LLM APIs, explore workspace repositories, read and search files, edit code safely, run test suites, manage git versioning, and plan actions autonomously.

## Project Structure

```text
claude-code-agent/
├── .backup/            # Local temporary file backups for undos
├── config/             # App configuration schemas/configs
├── docs/               # Technical documentation
├── examples/           # Code examples and usage recipes
├── logs/               # Application runtime log files
│   ├── memory.db       # SQLite relational database storage
│   └── chroma_db/      # ChromaDB persistent vector collection
├── prompts/            # Prompts templates (system/user)
├── src/                # Core Python package modules
│   ├── llm/            # LLM API clients
│   │   ├── client.py   # Base client interface
│   │   └── openai_client.py # OpenAI SDK client implementation
│   ├── cli.py          # Interactive console chat interface
│   ├── editor.py       # Safe file modification manager
│   ├── executor.py     # Safe shell command execution engine
│   ├── git_manager.py  # Git repository interaction manager
│   ├── memory.py       # Conversation memory storage (legacy)
│   ├── memory_index.py # Relational/vector context storage
│   ├── reader.py       # File reader and token counter
│   ├── repository.py   # Repository filesystem walker
│   ├── search.py       # Code base search and static analyzer
│   └── tools.py        # Workspace agent tools and registry
├── tests/              # Pytest unit testing suite
│   ├── test_editor.py  # Editor modification tests
│   ├── test_executor.py # Command execution runner tests
│   ├── test_git_manager.py # Git manager tests
│   ├── test_main.py    # Main script tests
│   ├── test_memory.py  # Memory manager tests
│   ├── test_memory_index.py # SQLite/vector memory index tests
│   ├── test_openai_client.py # OpenAI client tests
│   ├── test_planner.py # ReAct planning loops tests
│   ├── test_reader.py  # File reader tests
│   ├── test_repository.py # Repository walker tests
│   ├── test_search.py  # Code base search tests
│   └── test_tools.py   # Workspace agent tools tests
├── .env.example        # Environment variable configuration template
├── .gitignore          # Git exclusion rules
├── main.py             # CLI entry point
├── README.md           # Project overview and roadmap
└── requirements.txt    # Project dependencies
```

## Getting Started

### Prerequisites

- Python 3.8+
- Git

### Installation

1. Create a virtual environment:
   ```bash
   python -m venv venv
   ```

2. Activate the virtual environment:
   - **Windows (PowerShell)**:
     ```powershell
     .\venv\Scripts\Activate.ps1
     ```
   - **macOS / Linux**:
     ```bash
     source venv/bin/activate
     ```

3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create your local `.env` file from the template:
   ```bash
   cp .env.example .env
   ```

### Configuration

To interact with OpenAI, configure your API key in the `.env` file in the project root:
```env
OPENAI_API_KEY=sk-proj-...
```

### Running the CLI

Start the interactive terminal session:
```bash
python main.py
```

### CLI Slash Commands

You can manage your session, view statistics, scan directory trees, and edit/explain files using built-in slash commands in the CLI chat prompt:

- **Help Menu**:
  - `/help` - Show all available CLI instructions.
- **Session Memory**:
  - `/history` - Print a styled log of past exchanges.
  - `/clear` or `/delete` - Clear current context history in SQLite database and start a fresh session.
- **Repository Explorer**:
  - `/scan [path]` - Scan directory contents, ignore development directories (`.git`, `venv`, `node_modules`), show file statistics, and detect language breakdown.
  - `/tree [path]` - Generate and print a text-based visual tree diagram of the directories and files.
- **Code Reader**:
  - `/read <file>` - Reads a file and prints its contents with line numbers and token stats.
  - `/explain <file>` - Sends a file to the LLM to get a structured explanation.
  - `/summarize` - Bundles project tree structure and documentation to get an architectural summary from the LLM.
  - `/entrypoint` - Analyses the project and suggests candidate application starting points.
- **Search Engine**:
  - `/find <query>` - Searches all non-ignored files for keyword matches.
  - `/grep <regex>` - Searches files for lines matching regular expression patterns.
  - `/todo` - Scans all project files for `TODO`, `FIXME`, `HACK`, or `BUG` comments.
  - `/symbols [file]` - Uses AST parsing to list Python class and function definitions.
  - `/bugs` - Performs static analysis on Python files using AST traversal to flag empty `except` handlers or unsafe dynamic execution functions (`eval`/`exec`).
- **File Editing**:
  - `/replace <file>` - Launches interactive search-and-replace prompts, displays a color-coded unified diff preview, and asks for confirmation before writing changes.
  - `/diff <file>` - Shows current modifications made to `file` in this session compared to its original backup.
  - `/undo <file>` - Rolls back session changes and restores `file` to its original backed-up state.
- **Command Runner**:
  - `/run <command>` - Runs a custom shell command in the workspace, streaming the stdout/stderr live to the terminal.
  - `/test` - Shortcut to execute the Pytest unit testing suite and stream outputs.
- **Git Integration**:
  - `/git-status` - Print repository file status (modified, staged, untracked, deleted) highlighted with colors.
  - `/git-commit <message>` - Stages all current modifications and commits them to git.
  - `/git-diff [file]` - Shows unified unstaged diff of files in the workspace.
  - `/git-branch [name]` - Lists branches, highlighting the active branch, or creates a new branch named `name` and checks out.
  - `/git-log [limit]` - Prints the recent commit log history.
- **Planning Agent**:
  - `/plan <goal>` - Instructs the agent to recursively analyze a goal, layout a task list in `plan.md` in the root workspace, and execute it autonomously using the ReAct framework.
- **Memory Index (Phase 11+)**:
  - `/memory <query>` - Searches long-term session database and vector embeddings index semantically, returning matched entries.

---

## Agent Function Calling

When typing normal messages (without slash commands) in the chat prompt, the agent has access to several local tools. The model can automatically choose to call one or more of these functions to fulfill your request:

1. **`read_file(path)`**: Retrieves text content from a file.
2. **`write_file(path, content)`**: Writes code/text to a file, making a session rollback backup.
3. **`search_files(query, is_regex)`**: Searches the project files for strings or patterns.
4. **`list_directory(path)`**: Lists files and folders in a tree format.
5. **`run_command(command)`**: Runs a shell command securely (restricted by safety blocklists).
6. **`git_status()`**: Returns current repository file status.
7. **`git_commit(message)`**: Stages all modified files and commits them.
8. **`git_diff(file_path)`**: Returns unstaged diffs.
9. **`git_log(limit)`**: Lists recent repository commits.
10. **`recall_memory(query, limit)`**: Programmatically recall past conversation history or user preferences semantically.

---

## Memory Index Architecture (Phase 11+)

The Memory Index features a hybrid vector database layer:
1. **Relational Context Store (SQLite)**: Conversation history messages and metadata are saved incrementally to relational tables in `logs/memory.db`.
2. **Semantic Search Store (ChromaDB / NumPy fallback)**:
   - Uses ChromaDB's persistent vector collection when available.
   - If binary dependencies are missing on the target host, it seamlessly runs a fallback vector database using NumPy matrices to calculate cosine similarity:
     $$\text{Similarity} = \frac{\mathbf{A} \cdot \mathbf{B}}{\|\mathbf{A}\| \|\mathbf{B}\|}$$
   - Both layers query OpenAI's `text-embedding-3-small` embeddings API to vectorize text inputs dynamically.

---

## Security Policies

To protect the host environment during automated command execution, all commands processed by the agent pass through the `CommandRunner` sanitizer:
- **Blocked Commands**: Destructive binaries are explicitly blocked from executing (includes `del`, `rmdir`, `mkfs`, `dd`, `shutdown`, `reboot`, `format`, `chown`, `chmod`). Attempting to run them raises a `SecurityError`.
- **Blocked Parameters**: Dangerous command flag patterns, such as root recursive deletions (`rm -rf /`), are identified and blocked immediately.

Additionally, command execution prioritizes the local project virtual environment's bin folder (e.g. `venv/Scripts` or `venv/bin`) within the PATH, ensuring local developer CLI binaries execute cleanly.

---

### Running Tests

Execute the test suite using `pytest`:
```bash
pytest
```
