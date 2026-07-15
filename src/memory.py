import json
from pathlib import Path
from typing import List, Dict

class ConversationMemory:
    """Manages serialization and deserialization of conversation message history."""

    def __init__(self, file_path: str = "messages.json"):
        self.file_path = Path(file_path)

    def save(self, messages: List[Dict[str, str]]) -> None:
        """Saves conversation messages to the JSON file."""
        try:
            # Ensure the parent directory exists
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(messages, f, indent=4, ensure_ascii=False)
        except Exception as e:
            raise IOError(f"Failed to save conversation history: {e}")

    def load(self) -> List[Dict[str, str]]:
        """Loads conversation messages from the JSON file. Returns empty list if file not found."""
        if not self.file_path.exists():
            return []
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    return []
                return json.loads(content)
        except json.JSONDecodeError:
            raise ValueError("Failed to load conversation history: File is corrupted or contains invalid JSON.")
        except Exception as e:
            raise IOError(f"Failed to read conversation history: {e}")

    def delete(self) -> None:
        """Removes the conversation history file if it exists."""
        if self.file_path.exists():
            try:
                self.file_path.unlink()
            except Exception as e:
                raise IOError(f"Failed to delete conversation history: {e}")
