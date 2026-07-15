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
│   └── memory.py       # Conversation memory storage
├── tests/              # Pytest unit testing suite
│   ├── test_main.py    # Main script tests
│   ├── test_memory.py  # Memory manager tests
│   └── test_openai_client.py # OpenAI client tests
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

### Conversation Memory (Phase 2+)

The CLI maintains a persistent session cache inside a local file named `messages.json` in the project root directory.

- **Startup Resume**: If a previous conversation history is found in `messages.json`, the CLI will prompt you whether to resume:
  ```text
  Found previous conversation. Resume? (y/N):
  ```
- **Slash Commands**: You can enter special inline commands in the CLI chat prompt:
  - `/help` - Show available instructions
  - `/history` - Display styled transcripts of the current chat
  - `/clear` or `/delete` - Remove conversation cache from the disk and start a new chat session

---

### Running Tests

Execute the test suite using `pytest`:
```bash
pytest
```
