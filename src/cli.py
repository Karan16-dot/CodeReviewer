import sys
from colorama import init, Fore, Style
from llm.openai_client import OpenAIClient
from llm.client import LLMError
from memory import ConversationMemory
from repository import RepositoryExplorer
from reader import FileReader

# Initialize colorama for colored CLI output
init(autoreset=True)

class InteractiveCLI:
    """Manages the console interactive chat loop for the AI Coding Agent."""

    def __init__(self):
        self.messages = []
        self.client = None
        self.memory = ConversationMemory()
        self.file_reader = FileReader()
        self.system_prompt = "You are Claude Code Agent, a helpful AI programming assistant."

    def initialize_client(self):
        """Initializes the LLM client, exiting gracefully if the API key is missing."""
        try:
            self.client = OpenAIClient()
        except LLMError as e:
            print(f"{Fore.RED}Configuration Error: {e}")
            print(f"{Fore.YELLOW}Please configure your OPENAI_API_KEY in the environment or a .env file.")
            sys.exit(1)

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

                            # Check if code requires token chunking
                            # If larger than 3000 tokens, let the user know we chunk it
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

                            # Save a simplified representation in history to save context tokens
                            self.messages.append({"role": "user", "content": f"Explain the file {path_arg}"})
                            self.messages.append({"role": "assistant", "content": response_content})
                            print()

                            # Auto-save history
                            self.memory.save(self.messages)
                        except Exception as e:
                            print(f"{Fore.RED}Failed to explain file: {e}")
                        continue
                    elif cmd == "/summarize":
                        try:
                            explorer = RepositoryExplorer()
                            tree = explorer.build_tree()

                            # Try to load README
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
                                # Common file entry names
                                if name in ["main.py", "app.py", "index.js", "index.ts", "server.js", "main.go"]:
                                    detected.append(f)
                                    continue

                                # Python files with standard __main__
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
                    else:
                        print(f"{Fore.RED}Unknown command: {user_input}. Type '/help' for options.")
                        continue

                self.messages.append({"role": "user", "content": user_input})

                print(f"{Fore.GREEN}{Style.BRIGHT}Agent > {Style.RESET_ALL}", end="", flush=True)

                response_content = ""
                # Stream the response
                for chunk in self.client.stream_chat(self.messages):
                    print(chunk, end="", flush=True)
                    response_content += chunk
                print()  # Add a newline at the end of the stream

                self.messages.append({"role": "assistant", "content": response_content})
                print()  # Spacer

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
