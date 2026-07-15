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
- **File Editing & Refactoring**:
  - `/refactor` - Runs the interactive Multi-File Refactoring Wizard, enqueuing edit blocks for multiple files, generating combined diffs, running AST/imports code validation, and committing changes atomically.
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
- **Self-Correction Loop (Phase 13+)**:
  - `/correct <command>` - Runs a command. If execution fails, initiates an autonomous loop parsing tracebacks, reading line contexts, querying the LLM for corrections, applying updates, and retrying.
- **Model Fine-Tuning (Phase 15+)**:
  - `/finetune prepare <output_path>` - Exports structured SQLite database conversation histories to JSONL format.
  - `/finetune upload <file_path>` - Uploads a training dataset JSONL file to OpenAI.
  - `/finetune start <file_id>` - Initiates an OpenAI model fine-tuning job.
  - `/finetune status <job_id>` - Retrieves status and details of a fine-tuning job.
  - `/finetune list` - Lists recent OpenAI fine-tuning jobs.
- **Telemetry & Performance (Phase 16+)**:
  - `/telemetry show` - Prints aggregate usage and execution duration metrics.
  - `/telemetry export <dest_path>` - Saves telemetry events to a JSON file.
  - `/telemetry clear` - Purges the local telemetry database table.
- **Remote Repositories (Phase 18+)**:
  - `/github-clone <owner>/<repo> [dest_path] [branch]` - Clones a remote repository structure using the GitHub API.
  - `/github-pr <owner>/<repo> | <title> | <body> | <head> | [base]` - Submits a Pull Request to a remote GitHub repository.

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
11. **`apply_refactor(edits, validate)`**: Applies search-and-replace block changes across multiple files atomically. If validation checks fail, rolls back all changes.
12. **`run_with_self_correction(command, max_retries)`**: Runs a verification command (e.g. pytest). If it fails, parses the traceback, queries the LLM for corrections, applies patches, and retries.
13. **`prepare_finetuning_data(output_path)`**: Exports conversations from the SQLite log history to a JSON Lines (JSONL) file for model fine-tuning.
14. **`manage_finetuning(action, param)`**: Performs actions against the OpenAI Fine-Tuning endpoints (upload, start, status, list).
15. **`github_clone(repo_slug, dest_path, branch)`**: Clones a remote repository structure and downloads its files using the GitHub API.
16. **`github_create_pull_request(repo_slug, title, body, head, base)`**: Creates a Pull Request on a remote GitHub repository.

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

## Security Policies & Safety Constraints (Phase 14+)

To protect the host developer environment, all file writes and command executions pass through the `SecurityPolicy` validator:
1. **Configurable Policy File (`config/security_policy.json`)**:
   - `allowed_commands`: Whitelists permitted command binaries. If empty, all binaries except blacklisted ones are allowed.
   - `blocked_commands`: Blacklists unsafe binaries (e.g., `del`, `rmdir`, `mkfs`, `dd`, `shutdown`, `reboot`).
   - `require_user_confirmation`: If set to `true`, the CLI intercepts all agent tool executions (e.g. file writing, running tests) and prompts the user for confirmation: *"Allow agent tool call '<name>'? (y/N)"*.
   - `max_file_size_bytes`: Rejects modifications to files exceeding the size threshold (defaults to 1MB).
   - `blocked_file_extensions`: Rejects writing files with denied extensions (e.g., `.exe`, `.bin`, `.sh`, `.bat`, `.dll`).
2. **Path Traversal Constraints**: Strict containment check resolving all paths relative to the active workspace root using `resolved_path.relative_to(workspace_root)`. Any edits targeted outside the workspace are blocked.
3. **Recursive Deletion Check**: Blocks dangerous parameters such as root recursive folder deletions (`rm -rf /`).

Additionally, command execution prioritizes the local project virtual environment's bin folder (e.g. `venv/Scripts` or `venv/bin`) within the PATH, ensuring local developer CLI binaries execute cleanly.

---

## Multi-File Modification & AST Validation (Phase 12+)

The multi-file modification subsystem manages coordinated edits across files atomically:
1. **Refactoring Transactions (`RefactoringTransaction`)**: Edit actions (file path, search string, replace string) are queued and executed in-memory. Commit actions are atomic: targets are backed up beforehand, and any writing fault triggers a automatic restore pipeline to revert modified files to their original state.
2. **AST Parser Syntax Checks (`CodeValidator`)**: Evaluates the modified file's syntax tree using `ast.parse()`, intercepting formatting errors before writes occur.
3. **Workspace Imports Resolver**: Walks `Import` and `ImportFrom` AST blocks. Relative imports are resolved using file paths, while absolute imports are matched against local directories (`src/`, `.`) and python package indices, highlighting broken dependencies.

---

## Self-Correction Loop (Phase 13+)

The autonomous self-correction loop is designed to automatically detect and repair runtime failures:
1. **Traceback Parsing (`TracebackParser`)**: Scans console output logs (stdout/stderr) for Python traceback markers (`File "...", line ...`). It isolates the source file path and line number of the error location while automatically skipping external standard library modules.
2. **Context Gathering & LLM Correction**: Reads a line context window (e.g. 10 lines) around the error location. It presents the error trace and code window to the LLM, prompting it to produce a targeted search-and-replace patch.
3. **Execution Retries (`SelfCorrectionOrchestrator`)**: Applies the search-and-replace edit to the file on disk and re-runs the verification command. The loop repeats (up to 3 retries) until the exit code is 0 (success) or retries are exhausted.

---

## Model Fine-Tuning & Custom Models (Phase 15+)

The fine-tuning framework allows exporting local agent knowledge to optimize custom models on OpenAI:
1. **Training Data Prep (`FineTuningDataPreparer`)**: Exports relational conversation logs stored in SQLite to OpenAI's JSON Lines (JSONL) training format. It filters incomplete sessions (requiring at least one user and one assistant message) and maps tool call properties.
2. **Lifecycle Manager (`FineTuningManager`)**: Interfaces with the OpenAI API files and fine-tuning endpoints to handle training file uploads, start training jobs, retrieve live progress metrics, and list job histories.
3. **Custom Model Inference**: Set the environment variable `OPENAI_MODEL` in your `.env` (e.g. `OPENAI_MODEL=ft:gpt-3.5-turbo-0125:your-org:custom-suffix:model`) to redirect agent queries to utilize your custom fine-tuned model.

---

## Telemetry Logging & Performance Monitoring (Phase 16+)

The telemetry engine records operational metrics of the agent execution lifecycle:
1. **Telemetry Tracker (`TelemetryTracker`)**: Inserts performance metrics inside relational tables in `logs/memory.db`. It logs LLM chat query durations, tool call executions (duration, success status, and parameters), and shell command executions (duration, exit code).
2. **PII and Key Redactions**: Recursively sanitizes logged event arguments by identifying keys containing `"key"`, `"password"`, `"secret"`, `"token"`, or `"auth"` and replacing their values with `"[REDACTED]"`. Metric counters containing `"prompt_tokens"` or `"completion_tokens"` are explicitly preserved.
3. **Analytics Dashboard & Log Exports**: Exposes operations to calculate token usage aggregates, command averages, tool call frequencies, and tool success rates. Enables exporting logs as pretty JSON outputs.

---

## Plugin Extensibility Architecture (Phase 17+)

The agent supports custom features via third-party plugins loaded dynamically at runtime:
1. **Plugin Interface (`BasePlugin`)**: Plugins extend the agent by subclassing `BasePlugin` and overriding:
   - `get_commands()`: Returns a dictionary mapping custom CLI slash commands (e.g. `/my-cmd`) to python execution callbacks.
   - `get_tools()`: Returns custom agent tool functions and parameters schemas to register into the global `tool_registry`.
2. **Dynamic Loader (`PluginManager`)**: Scans the workspace `plugins/` directory on CLI startup. It loads standalone python files (`my_plugin.py`) or python packages containing `__init__.py` using importlib spec loaders, discovers `BasePlugin` subclasses, and instantiates them dynamically.

---

## Remote Repositories & GitHub API Sync (Phase 18+)

The GitHub client provides API-driven automation for remote repository checkouts and pull requests:
1. **GitHub Integrations (`GitHubManager`)**: Connects to the GitHub API using Personal Access Tokens (PATs) configured via `GITHUB_TOKEN` or `GITHUB_PAT`. It handles recursive directory tree requests, blob downloads, and PR publishing using standard `urllib` calls.
2. **API-driven Directory Clones**: Re-creates remote directory structure templates locally and fetches content blobs using the GitHub database API, bypassing standard Git CLI requirements.
3. **Workspace Path Containment**: Runs workspace containment checks preventing downloads from mapping outside the destination folder (directory traversals).

---

### Running Tests

Execute the test suite using `pytest`:
```bash
pytest
```
