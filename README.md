# Claude Code Agent

Claude Code Agent is a robust, modular AI coding assistant built feature-by-feature. It is designed to run locally, interact with LLM APIs, explore workspace repositories, read and search files, edit code safely, run test suits, manage git versioning, and plan actions autonomously.

## Project Structure

```text
claude-code-agent/
├── config/             # App configuration schemas/configs
├── docs/               # Technical documentation
├── examples/           # Code examples and usage recipes
├── logs/               # Application runtime log files
├── prompts/            # Prompts templates (system/user)
├── src/                # Core Python package modules
├── tests/              # Pytest unit testing suite
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

### Running the CLI

Run the entry point script:
```bash
python main.py
```

Expected output:
```text
Claude Code Agent v0.1
```

### Running Tests

Execute the test suite using `pytest`:
```bash
pytest
```
