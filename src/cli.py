import sys
from colorama import init, Fore, Style
from llm.openai_client import OpenAIClient
from llm.client import LLMError
from memory import ConversationMemory

# Initialize colorama for colored CLI output
init(autoreset=True)

class InteractiveCLI:
    """Manages the console interactive chat loop for the AI Coding Agent."""

    def __init__(self):
        self.messages = []
        self.client = None
        self.memory = ConversationMemory()
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
        print(f"  {Fore.CYAN}/help{Fore.RESET}        - Show this help message")
        print(f"  {Fore.CYAN}/history{Fore.RESET}     - Print current conversation history")
        print(f"  {Fore.CYAN}/clear{Fore.RESET}       - Delete memory and start a new chat")
        print(f"  {Fore.CYAN}/delete{Fore.RESET}      - Same as /clear")
        print(f"  {Fore.CYAN}exit{Fore.RESET} or {Fore.CYAN}quit{Fore.RESET} - Exit the agent shell\n")

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
                    cmd = user_input.lower()
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
