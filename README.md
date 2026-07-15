# Claude Code Agent

Claude Code Agent is a robust, modular AI coding assistant built feature-by-feature. It is designed to run locally, interact with LLM APIs, explore workspace repositories, read and search files, edit code safely, run test suites, manage git versioning, and plan actions autonomously.

## Project Structure

```text
claude-code-agent/
├── config/             # App configuration schemas/configs
├── docs/               # Technical documentation
├── examples/           # Code examples and usage recipes
├── logs/               # Application runtime log files
├── prompts/            # Prompts templates (system/user)
├── src/                # Core Python package modules
│   ├── llm/            # LLM API clients
│   │   ├── client.py   # Base client interface
│   │   └── openai_client.py # OpenAI SDK client implementation
│   ├── cli.py          # Interactive console chat interface
│   ├── memory.py       # Conversation memory storage
│   ├── reader.py       # File reader and token counter
│   └── repository.py   # Repository filesystem walker
├── tests/              # Pytest unit testing suite
│   ├── test_main.py    # Main script tests
│   ├── test_memory.py  # Memory manager tests
│   ├── test_openai_client.py # OpenAI client tests
│   ├── test_reader.py  # File reader tests
│   └── test_repository.py # Repository walker tests
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

You can manage your session, view statistics, scan directory trees, and read/explain files using built-in slash commands in the CLI chat prompt:

- **Help Menu**:
  - `/help` - Show all available CLI instructions.
- **Session Memory**:
  - `/history` - Print a styled log of past exchanges.
  - `/clear` or `/delete` - Unlink current cache file and start a fresh session.
- **Repository Explorer**:
  - `/scan [path]` - Scan directory contents, ignore development directories (`.git`, `venv`, `node_modules`), show file statistics, and detect language breakdown.
  - `/tree [path]` - Generate and print a text-based visual tree diagram of the directories and files (ignores system and cache directories).
- **Code Reader**:
  - `/read <file>` - Reads a file and prints its contents with line numbers and token stats.
  - `/explain <file>` - Sends a file to the LLM to get a structured explanation (handles large files using token chunking).
  - `/summarize` - Bundles project tree structure and documentation to get an architectural summary from the LLM.
  - `/entrypoint` - Analyses the project and suggests candidate application starting points.

---

### Running Tests

Execute the test suite using `pytest`:
```bash
pytest
```
