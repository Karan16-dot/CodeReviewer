import sys
from pathlib import Path
from colorama import init, Fore, Style
from llm.openai_client import OpenAIClient
from llm.client import LLMError
from memory import ConversationMemory
from repository import RepositoryExplorer
from reader import FileReader
from search import CodeSearcher
from editor import FileEditor
from tools import tool_registry

# Initialize colorama for colored CLI output
init(autoreset=True)

class InteractiveCLI:
    """Manages the console interactive chat loop for the AI Coding Agent."""

    def __init__(self):
        self.messages = []
        self.client = None
        self.memory = ConversationMemory()
        self.file_reader = FileReader()
        self.file_editor = FileEditor()
        self.tool_registry = tool_registry
        self.system_prompt = "You are Claude Code Agent, a helpful AI programming assistant."

    def initialize_client(self):
        """Initializes the LLM client, exiting gracefully if the API key is missing."""
        try:
            self.client = OpenAIClient()
        except LLMError as e:
            print(f"{Fore.RED}Configuration Error: {e}")
            print(f"{Fore.YELLOW}Please configure your OPENAI_API_KEY in the environment or a .env file.")
            sys.exit(1)

    def get_multiline_input(self, prompt_label: str) -> str:
        """Helper to collect multi-line text input from the console, terminated by 'END'."""
        print(f"{Fore.YELLOW}{prompt_label} (Type 'END' on a line by itself to finish):")
        lines = []
        while True:
            try:
                line = input()
                if line.strip() == "END":
                    break
                lines.append(line)
            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}Input cancelled.")
                raise KeyboardInterrupt()
        return "\n".join(lines)

    def print_help(self):
        """Prints available slash commands."""
        print(f"\n{Fore.YELLOW}{Style.BRIGHT}Available Commands:")
        print(f"  {Fore.CYAN}/help{Fore.RESET}               - Show this help message")
        print(f"  {Fore.CYAN}/scan [path]{Fore.RESET}        - Scan directory statistics (defaults to .)")
        print(f"  {Fore.CYAN}/tree [path]{Fore.RESET}        - Print visual directory tree (defaults to .)")
        print(f"  {Fore.CYAN}/read <file>{Fore.RESET}        - Read file contents with line numbers and token stats")
        print(f"  {Fore.CYAN}/explain <file>{Fore.RESET}     - Stream an LLM explanation of the specified file")
        print(f"  {Fore.CYAN}/summarize{Fore.RESET}          - Stream an LLM summary of the repository architecture")
        print(f"  {Fore.CYAN}/entrypoint{Fore.RESET}         - Search and suggest main application entry points")
        print(f"  {Fore.CYAN}/find <query>{Fore.RESET}       - Search for a keyword across workspace files")
        print(f"  {Fore.CYAN}/grep <regex>{Fore.RESET}       - Search for regex matches across workspace files")
        print(f"  {Fore.CYAN}/todo{Fore.RESET}               - List all TODO, FIXME, HACK, and BUG comments")
        print(f"  {Fore.CYAN}/symbols [file]{Fore.RESET}     - Extract classes and functions in Python files")
        print(f"  {Fore.CYAN}/bugs{Fore.RESET}               - Audit Python AST for empty catches or unsafe evals")
        print(f"  {Fore.CYAN}/replace <file>{Fore.RESET}     - Interactively replace a block of code in a file")
        print(f"  {Fore.CYAN}/diff <file>{Fore.RESET}        - Show the session changes made to a file")
        print(f"  {Fore.CYAN}/undo <file>{Fore.RESET}        - Roll back session changes made to a file")
        print(f"  {Fore.CYAN}/run <command>{Fore.RESET}      - Run shell command asynchronously with real-time output")
        print(f"  {Fore.CYAN}/test{Fore.RESET}               - Shortcut to execute pytest unit test suite")
        print(f"  {Fore.CYAN}/git-status{Fore.RESET}         - Shortcut to execute git status command")
        print(f"  {Fore.CYAN}/history{Fore.RESET}            - Print current conversation history")
        print(f"  {Fore.CYAN}/clear{Fore.RESET}              - Delete memory and start a new chat")
        print(f"  {Fore.CYAN}/delete{Fore.RESET}             - Same as /clear")
        print(f"  {Fore.CYAN}exit{Fore.RESET} or {Fore.CYAN}quit{Fore.RESET}        - Exit the agent shell\n")

    def print_history(self):
        """Displays the loaded conversation history."""
        print(f"\n{Fore.YELLOW}{Style.BRIGHT}--- Conversation History ---")
        for msg in self.messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                print(f"{Fore.MAGENTA}[System] {content}")
            elif role == "user":
                print(f"{Fore.CYAN}{Style.BRIGHT}User: {Style.RESET_ALL}{content}")
            elif role == "assistant":
                print(f"{Fore.GREEN}{Style.BRIGHT}Agent: {Style.RESET_ALL}{content}")
        print(f"{Fore.YELLOW}{Style.BRIGHT}----------------------------\n")

    def run(self):
        """Starts the interactive CLI prompt loop."""
        print(f"{Fore.GREEN}{Style.BRIGHT}==========================================")
        print(f"{Fore.GREEN}{Style.BRIGHT}        Claude Code Agent CLI v0.1        ")
        print(f"{Fore.GREEN}{Style.BRIGHT}==========================================")
        print(f"{Fore.YELLOW}Type 'exit' or 'quit' to close the chat. Type '/help' for options.\n")

        self.initialize_client()

        # Handle conversation memory resume
        try:
            saved_messages = self.memory.load()
            if saved_messages:
                resume = input(f"{Fore.YELLOW}Found previous conversation. Resume? (y/N): ").strip().lower()
                if resume in ["y", "yes"]:
                    self.messages = saved_messages
                    print(f"{Fore.GREEN}Resumed conversation. Showing history:")
                    self.print_history()
                else:
                    self.memory.delete()
                    self.messages = [{"role": "system", "content": self.system_prompt}]
                    print(f"{Fore.GREEN}Started new conversation session.\n")
            else:
                self.messages = [{"role": "system", "content": self.system_prompt}]
        except Exception as e:
            print(f"{Fore.RED}Warning: Failed to load memory: {e}. Starting fresh session.")
            self.messages = [{"role": "system", "content": self.system_prompt}]

        while True:
            try:
                # Prompt user
                user_input = input(f"{Fore.CYAN}{Style.BRIGHT}User > {Style.RESET_ALL}").strip()

                if not user_input:
                    continue

                if user_input.lower() in ["exit", "quit"]:
                    print(f"{Fore.YELLOW}Goodbye!")
                    break

                # Handle slash commands
                if user_input.startswith("/"):
                    parts = user_input.split(maxsplit=1)
                    cmd = parts[0].lower()
                    path_arg = parts[1].strip() if len(parts) > 1 else "."

                    if cmd == "/help":
                        self.print_help()
                        continue
                    elif cmd in ["/clear", "/delete"]:
                        try:
                            self.memory.delete()
                            self.messages = [{"role": "system", "content": self.system_prompt}]
                            print(f"{Fore.GREEN}Conversation memory cleared.")
                        except Exception as e:
                            print(f"{Fore.RED}Failed to clear memory: {e}")
                        continue
                    elif cmd == "/history":
                        self.print_history()
                        continue
                    elif cmd == "/scan":
                        try:
                            explorer = RepositoryExplorer(root_path=path_arg)
                            stats = explorer.get_summary_stats()
                            total = stats["total_files"]
                            languages = stats["languages"]

                            print(f"\n{Fore.GREEN}{Style.BRIGHT}Repository Scan Summary for: {explorer.root_path}")
                            print(f"{Fore.GREEN}Total Files: {total}")
                            if total > 0:
                                print(f"{Fore.YELLOW}{Style.BRIGHT}Breakdown by Language:")
                                for lang, count in sorted(languages.items(), key=lambda x: x[1], reverse=True):
                                    pct = (count / total) * 100
                                    print(f"  {Fore.CYAN}{lang:<18}: {count:<3} ({pct:.1f}%)")
                            print()
                        except Exception as e:
                            print(f"{Fore.RED}Scan failed: {e}")
                        continue
                    elif cmd == "/tree":
                        try:
                            explorer = RepositoryExplorer(root_path=path_arg)
                            tree_visual = explorer.build_tree()
                            print(f"\n{Fore.GREEN}{Style.BRIGHT}Directory Tree for: {explorer.root_path}")
                            print(f"{Fore.WHITE}{tree_visual}\n")
                        except Exception as e:
                            print(f"{Fore.RED}Failed to build tree: {e}")
                        continue
                    elif cmd == "/read":
                        try:
                            content = self.file_reader.read_file(path_arg)
                            tokens = self.file_reader.count_tokens(content)

                            print(f"\n{Fore.GREEN}{Style.BRIGHT}File: {path_arg} ({len(content)} characters, {tokens} tokens)")
                            print(f"{Fore.GREEN}{'-' * 50}")

                            lines = content.splitlines()
                            for idx, line in enumerate(lines, 1):
                                print(f"{Fore.YELLOW}{idx:4}│ {Fore.WHITE}{line}")

                            print(f"{Fore.GREEN}{'-' * 50}\n")
                        except Exception as e:
                            print(f"{Fore.RED}Failed to read file: {e}")
                        continue
                    elif cmd == "/explain":
                        try:
                            content = self.file_reader.read_file(path_arg)
                            tokens = self.file_reader.count_tokens(content)

                            print(f"\n{Fore.YELLOW}Reading {path_arg} ({len(content)} chars, {tokens} tokens) for explanation...")

                            if tokens > 3000:
                                print(f"{Fore.YELLOW}File is large ({tokens} tokens). Explaining in chunks...")
                                chunks = self.file_reader.chunk_text(content, max_tokens=3000)
                            else:
                                chunks = [content]

                            response_content = ""
                            for i, chunk in enumerate(chunks, 1):
                                if len(chunks) > 1:
                                    print(f"\n{Fore.YELLOW}[Part {i}/{len(chunks)}]")

                                prompt = f"Explain the following code from the file '{path_arg}':\n\n```\n{chunk}\n```"
                                query_messages = self.messages + [{"role": "user", "content": prompt}]

                                print(f"{Fore.GREEN}{Style.BRIGHT}Agent (Explaining {path_arg}) > {Style.RESET_ALL}", end="", flush=True)

                                for chunk_res in self.client.stream_chat(query_messages):
                                    print(chunk_res, end="", flush=True)
                                    response_content += chunk_res
                                print()

                            self.messages.append({"role": "user", "content": f"Explain the file {path_arg}"})
                            self.messages.append({"role": "assistant", "content": response_content})
                            print()

                            self.memory.save(self.messages)
                        except Exception as e:
                            print(f"{Fore.RED}Failed to explain file: {e}")
                        continue
                    elif cmd == "/summarize":
                        try:
                            explorer = RepositoryExplorer()
                            tree = explorer.build_tree()

                            readme_content = ""
                            try:
                                readme_path = explorer.root_path / "README.md"
                                readme_content = self.file_reader.read_file(readme_path)
                            except Exception:
                                pass

                            print(f"\n{Fore.YELLOW}Compiling repository metadata for summarization...")

                            prompt = f"Provide a comprehensive architectural summary of this repository.\n\n"
                            prompt += f"Directory Structure:\n```\n{tree}\n```\n\n"
                            if readme_content:
                                readme_summary = readme_content[:1500] + "..." if len(readme_content) > 1500 else readme_content
                                prompt += f"README.md Content (truncated if long):\n```\n{readme_summary}\n```\n"

                            query_messages = self.messages + [{"role": "user", "content": prompt}]

                            print(f"{Fore.GREEN}{Style.BRIGHT}Agent (Repository Summary) > {Style.RESET_ALL}", end="", flush=True)

                            response_content = ""
                            for chunk in self.client.stream_chat(query_messages):
                                print(chunk, end="", flush=True)
                                response_content += chunk
                            print()

                            self.messages.append({"role": "user", "content": "Summarize the repository structure and purpose."})
                            self.messages.append({"role": "assistant", "content": response_content})
                            print()

                            self.memory.save(self.messages)
                        except Exception as e:
                            print(f"{Fore.RED}Failed to summarize repository: {e}")
                        continue
                    elif cmd == "/entrypoint":
                        try:
                            explorer = RepositoryExplorer()
                            files = explorer.scan_files()
                            detected = []

                            for f in files:
                                name = f.name.lower()
                                if name in ["main.py", "app.py", "index.js", "index.ts", "server.js", "main.go"]:
                                    detected.append(f)
                                    continue

                                if f.suffix == ".py":
                                    try:
                                        content = self.file_reader.read_file(f)
                                        if '__name__ == "__main__"' in content or "__name__ == '__main__'" in content:
                                            if f not in detected:
                                                detected.append(f)
                                    except Exception:
                                        pass

                            print(f"\n{Fore.GREEN}{Style.BRIGHT}Suggested Repository Entry Points:")
                            if detected:
                                for path in detected:
                                    rel = path.relative_to(explorer.root_path)
                                    print(f"  {Fore.CYAN}★ {rel}")
                            else:
                                print(f"  {Fore.YELLOW}No obvious entry point detected.")
                            print()
                        except Exception as e:
                            print(f"{Fore.RED}Failed to scan for entry points: {e}")
                        continue
                    elif cmd == "/find":
                        if path_arg == "." or not path_arg:
                            print(f"{Fore.RED}Please provide a search term. Usage: /find <query>")
                            continue
                        try:
                            searcher = CodeSearcher()
                            matches = searcher.search_text(path_arg, is_regex=False)
                            print(f"\n{Fore.GREEN}{Style.BRIGHT}Found {len(matches)} matches for keyword: '{path_arg}'")
                            for m in matches:
                                print(f"  {Fore.CYAN}{m['file']}:{m['line']} {Fore.WHITE}│ {m['content']}")
                            print()
                        except Exception as e:
                            print(f"{Fore.RED}Search failed: {e}")
                        continue
                    elif cmd == "/grep":
                        if path_arg == "." or not path_arg:
                            print(f"{Fore.RED}Please provide a regular expression pattern. Usage: /grep <pattern>")
                            continue
                        try:
                            searcher = CodeSearcher()
                            matches = searcher.search_text(path_arg, is_regex=True)
                            print(f"\n{Fore.GREEN}{Style.BRIGHT}Found {len(matches)} matches for regex pattern: '{path_arg}'")
                            for m in matches:
                                print(f"  {Fore.CYAN}{m['file']}:{m['line']} {Fore.WHITE}│ {m['content']}")
                            print()
                        except Exception as e:
                            print(f"{Fore.RED}Regex search failed: {e}")
                        continue
                    elif cmd == "/todo":
                        try:
                            searcher = CodeSearcher()
                            matches = searcher.find_todos()
                            print(f"\n{Fore.GREEN}{Style.BRIGHT}Found {len(matches)} TODOs/FIXMEs/HACKs:")
                            for m in matches:
                                print(f"  {Fore.CYAN}{m['file']}:{m['line']} {Fore.WHITE}│ {m['content']}")
                            print()
                        except Exception as e:
                            print(f"{Fore.RED}Failed to search for TODOs: {e}")
                        continue
                    elif cmd == "/symbols":
                        try:
                            searcher = CodeSearcher()
                            target = None if path_arg == "." else path_arg
                            symbols = searcher.find_symbols(target)

                            title = f"AST Symbols in file: {path_arg}" if target else "All AST Symbols in Repository"
                            print(f"\n{Fore.GREEN}{Style.BRIGHT}{title} (Found {len(symbols)}):")

                            for s in symbols:
                                prefix = f"{s['file']}:" if not target else ""
                                type_color = Fore.YELLOW if s['type'] == 'class' else Fore.CYAN
                                print(f"  {Fore.MAGENTA}{prefix}{s['line']:<4} {type_color}{s['type']:<8} {Fore.WHITE}{s['name']}")
                            print()
                        except Exception as e:
                            print(f"{Fore.RED}Failed to fetch symbols: {e}")
                        continue
                    elif cmd == "/bugs":
                        try:
                            searcher = CodeSearcher()
                            bugs = searcher.find_bugs()
                            print(f"\n{Fore.GREEN}{Style.BRIGHT}Static Analysis Bug Audit (Found {len(bugs)} issues):")
                            if bugs:
                                for b in bugs:
                                    print(f"  {Fore.RED}{b['file']}:{b['line']} {Fore.YELLOW}[{b['type']}] {Fore.WHITE}{b['message']}")
                            else:
                                print(f"  {Fore.GREEN}No bugs detected!")
                            print()
                        except Exception as e:
                            print(f"{Fore.RED}Bug scan failed: {e}")
                        continue
                    elif cmd == "/replace":
                        if path_arg == "." or not path_arg:
                            print(f"{Fore.RED}Please provide a target file. Usage: /replace <file>")
                            continue
                        try:
                            file_path = Path(path_arg).resolve()
                            if not file_path.exists():
                                print(f"{Fore.RED}File not found: {path_arg}")
                                continue

                            print(f"{Fore.CYAN}--- Search Block ---")
                            search_block = self.get_multiline_input("Enter block to search")
                            if not search_block:
                                print(f"{Fore.RED}Search block cannot be empty. Aborted.")
                                continue

                            print(f"\n{Fore.CYAN}--- Replacement Block ---")
                            replace_block = self.get_multiline_input("Enter replacement block")

                            new_content = self.file_editor.apply_replacement(file_path, search_block, replace_block)
                            diff_str = self.file_editor.get_diff(file_path, new_content)

                            if not diff_str:
                                print(f"{Fore.YELLOW}No changes would be made.")
                                continue

                            print(f"\n{Fore.GREEN}{Style.BRIGHT}--- Proposed Changes Diff ---")
                            for line in diff_str.splitlines():
                                if line.startswith("+"):
                                    print(f"{Fore.GREEN}{line}")
                                elif line.startswith("-"):
                                    print(f"{Fore.RED}{line}")
                                elif line.startswith("@@"):
                                    print(f"{Fore.CYAN}{line}")
                                else:
                                    print(f"{Fore.WHITE}{line}")
                            print(f"{Fore.GREEN}{Style.BRIGHT}------------------------------\n")

                            confirm = input(f"{Fore.YELLOW}Apply these changes? (y/N): ").strip().lower()
                            if confirm in ["y", "yes"]:
                                self.file_editor.write(file_path, new_content)
                                print(f"{Fore.GREEN}Changes applied successfully.")
                            else:
                                print(f"{Fore.YELLOW}Changes aborted.")
                        except Exception as e:
                            print(f"{Fore.RED}Replacement failed: {e}")
                        continue
                    elif cmd == "/diff":
                        if path_arg == "." or not path_arg:
                            print(f"{Fore.RED}Please provide a file name. Usage: /diff <file>")
                            continue
                        try:
                            file_path = Path(path_arg).resolve()
                            backup_path = self.file_editor.backups.get(str(file_path))

                            if str(file_path) not in self.file_editor.backups:
                                print(f"{Fore.YELLOW}No edit history found for {path_arg} in this session.")
                                continue

                            with open(file_path, "r", encoding="utf-8") as f:
                                current_content = f.read()

                            original_content = ""
                            if backup_path and backup_path.exists():
                                with open(backup_path, "r", encoding="utf-8") as f:
                                    original_content = f.read()

                            diff_str = self.file_editor.get_diff(file_path, current_content)

                            # Re-read from backup to get true diff comparing backup to current
                            import difflib
                            original_lines = original_content.splitlines(keepends=True)
                            current_lines = current_content.splitlines(keepends=True)
                            diff = difflib.unified_diff(
                                original_lines,
                                current_lines,
                                fromfile=f"a/{file_path.name}",
                                tofile=f"b/{file_path.name}",
                                lineterm=""
                            )
                            diff_str = "\n".join(diff)

                            if not diff_str:
                                print(f"{Fore.YELLOW}No differences found.")
                            else:
                                print(f"\n{Fore.GREEN}{Style.BRIGHT}--- Session Diff for {path_arg} ---")
                                for line in diff_str.splitlines():
                                    if line.startswith("+"):
                                        print(f"{Fore.GREEN}{line}")
                                    elif line.startswith("-"):
                                        print(f"{Fore.RED}{line}")
                                    elif line.startswith("@@"):
                                        print(f"{Fore.CYAN}{line}")
                                    else:
                                        print(f"{Fore.WHITE}{line}")
                                print(f"{Fore.GREEN}{Style.BRIGHT}------------------------------------\n")
                        except Exception as e:
                            print(f"{Fore.RED}Failed to compute diff: {e}")
                        continue
                    elif cmd == "/undo":
                        if path_arg == "." or not path_arg:
                            print(f"{Fore.RED}Please provide a file name. Usage: /undo <file>")
                            continue
                        try:
                            file_path = Path(path_arg).resolve()
                            success = self.file_editor.undo(file_path)
                            if success:
                                print(f"{Fore.GREEN}Successfully rolled back changes to {path_arg}.")
                            else:
                                print(f"{Fore.YELLOW}No backup found for {path_arg} in this session.")
                        except Exception as e:
                            print(f"{Fore.RED}Undo failed: {e}")
                        continue
                    elif cmd == "/run":
                        if path_arg == "." or not path_arg:
                            print(f"{Fore.RED}Please provide a command string to run. Usage: /run <command>")
                            continue
                        try:
                            from executor import CommandRunner
                            print(f"\n{Fore.YELLOW}Executing custom command stream: {path_arg}\n")
                            runner = CommandRunner()
                            for line in runner.run_streaming(path_arg):
                                print(line, end="", flush=True)
                            print()
                        except Exception as e:
                            print(f"{Fore.RED}Execution failed: {e}")
                        continue
                    elif cmd == "/test":
                        try:
                            from executor import CommandRunner
                            print(f"\n{Fore.YELLOW}Running pytest suite stream...\n")
                            runner = CommandRunner()
                            for line in runner.run_streaming("pytest"):
                                print(line, end="", flush=True)
                            print()
                        except Exception as e:
                            print(f"{Fore.RED}Tests execution failed: {e}")
                        continue
                    elif cmd == "/git-status":
                        try:
                            from executor import CommandRunner
                            print(f"\n{Fore.YELLOW}Running git status stream...\n")
                            runner = CommandRunner()
                            for line in runner.run_streaming("git status"):
                                print(line, end="", flush=True)
                            print()
                        except Exception as e:
                            print(f"{Fore.RED}Git status failed: {e}")
                        continue
                    else:
                        print(f"{Fore.RED}Unknown command: {user_input}. Type '/help' for options.")
                        continue

                self.messages.append({"role": "user", "content": user_input})

                print(f"{Fore.GREEN}{Style.BRIGHT}Agent > {Style.RESET_ALL}", end="", flush=True)

                loop_count = 0
                max_loops = 5  # Prevent infinite tool call loops

                while loop_count < max_loops:
                    loop_count += 1
                    tool_calls = None
                    response_content = ""

                    # Stream chat with tools registered
                    stream = self.client.stream_chat(self.messages, tools=self.tool_registry.schemas)

                    for event in stream:
                        if isinstance(event, str):
                            print(event, end="", flush=True)
                            response_content += event
                        elif isinstance(event, dict) and event.get("type") == "tool_calls":
                            tool_calls = event["calls"]

                    # If no tool calls, append the assistant response and break the loop
                    if not tool_calls:
                        if response_content:
                            self.messages.append({"role": "assistant", "content": response_content})
                        break

                    # Format tool calls in history
                    api_tool_calls = []
                    for tc in tool_calls:
                        api_tool_calls.append({
                            "id": tc["id"],
                            "type": "function",
                            "function": {
                                "name": tc["name"],
                                "arguments": tc["arguments"]
                            }
                        })

                    self.messages.append({
                        "role": "assistant",
                        "content": response_content or None,
                        "tool_calls": api_tool_calls
                    })

                    # Execute each tool call
                    for tc in tool_calls:
                        name = tc["name"]
                        args_str = tc["arguments"]
                        tc_id = tc["id"]

                        import json
                        try:
                            args = json.loads(args_str) if args_str else {}
                        except json.JSONDecodeError as e:
                            print(f"\n{Fore.RED}Failed to parse tool arguments for '{name}': {args_str} ({e})")
                            tool_result = f"Error: Invalid arguments JSON: {e}"
                            args = {}
                        else:
                            args_formatted = ", ".join(f"{k}={repr(v)}" for k, v in args.items())
                            print(f"\n{Fore.YELLOW}{Style.BRIGHT}⚙ Tool Run: {Fore.CYAN}{name}({args_formatted})")

                            tool_result = self.tool_registry.execute(name, args)
                            result_preview = tool_result[:250] + "..." if len(tool_result) > 250 else tool_result
                            print(f"{Fore.GREEN}Result Preview:\n{Fore.WHITE}{result_preview}")

                        self.messages.append({
                            "role": "tool",
                            "tool_call_id": tc_id,
                            "name": name,
                            "content": tool_result
                        })

                    # Print header for subsequent response turn
                    print(f"{Fore.GREEN}{Style.BRIGHT}Agent > {Style.RESET_ALL}", end="", flush=True)

                # Save history to memory file
                try:
                    self.memory.save(self.messages)
                except Exception as e:
                    print(f"{Fore.RED}Warning: Failed to auto-save history: {e}")

            except LLMError as e:
                print(f"\n{Fore.RED}API Error: {e}\n")
            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}Session interrupted. Goodbye!")
                break
            except Exception as e:
                print(f"\n{Fore.RED}An unexpected error occurred: {e}\n")
