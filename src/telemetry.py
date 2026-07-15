import sqlite3
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

class TelemetryTracker:
    """Collects system, tool, and LLM telemetry data securely in SQLite and exports analytics reports."""
    
    db_path: Path = Path("logs/memory.db")

    @classmethod
    def _init_db(cls):
        """Creates the telemetry_events table inside logs/memory.db if not exists."""
        cls.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(cls.db_path))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS telemetry_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT,
                event_data TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    @classmethod
    def sanitize_data(cls, data: Any) -> Any:
        """Recursively redacts sensitive info keys matching key/token/password/secret/auth."""
        if isinstance(data, dict):
            sanitized = {}
            for k, v in data.items():
                k_lower = k.lower()
                if any(sec in k_lower for sec in ["key", "password", "secret", "token", "auth"]):
                    if any(allowed in k_lower for allowed in ["prompt_tokens", "completion_tokens", "total_tokens", "trained_tokens"]):
                        sanitized[k] = cls.sanitize_data(v)
                    else:
                        sanitized[k] = "[REDACTED]"
                else:
                    sanitized[k] = cls.sanitize_data(v)
            return sanitized
        elif isinstance(data, list):
            return [cls.sanitize_data(item) for item in data]
        elif isinstance(data, str):
            # Check for API key formats (like sk-...) or long hex tokens
            if "sk-" in data and len(data) > 15:
                return "[REDACTED]"
            return data
        else:
            return data

    @classmethod
    def log_event(cls, event_type: str, data: Dict[str, Any]):
        """Logs a sanitized event to the SQLite database."""
        try:
            cls._init_db()
            sanitized = cls.sanitize_data(data)
            conn = sqlite3.connect(str(cls.db_path))
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO telemetry_events (event_type, event_data) VALUES (?, ?)",
                (event_type, json.dumps(sanitized))
            )
            conn.commit()
            conn.close()
        except Exception:
            # Silence telemetry logging errors to avoid interrupting user flows
            pass

    @classmethod
    def log_tool_call(cls, tool_name: str, arguments: Dict[str, Any], duration: float, success: bool):
        cls.log_event("tool_call", {
            "name": tool_name,
            "arguments": arguments,
            "duration": duration,
            "success": success
        })

    @classmethod
    def log_llm_call(cls, model: str, prompt_tokens: int, completion_tokens: int, duration: float):
        cls.log_event("llm_call", {
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "duration": duration
        })

    @classmethod
    def log_command(cls, command: str, duration: float, exit_code: int):
        cls.log_event("command", {
            "command": command,
            "duration": duration,
            "exit_code": exit_code
        })

    @classmethod
    def get_metrics(cls) -> Dict[str, Any]:
        """Calculates aggregate usage and performance metrics."""
        cls._init_db()
        conn = sqlite3.connect(str(cls.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT event_type, event_data FROM telemetry_events")
        rows = cursor.fetchall()
        conn.close()

        total_llm_calls = 0
        total_prompt_tokens = 0
        total_completion_tokens = 0
        llm_durations = []

        total_tool_calls = 0
        tool_success_count = 0
        tool_durations = []
        tool_frequencies = {}

        total_commands = 0
        command_durations = []

        for r in rows:
            etype = r["event_type"]
            try:
                data = json.loads(r["event_data"])
            except Exception:
                continue

            if etype == "llm_call":
                total_llm_calls += 1
                total_prompt_tokens += data.get("prompt_tokens", 0)
                total_completion_tokens += data.get("completion_tokens", 0)
                llm_durations.append(data.get("duration", 0.0))

            elif etype == "tool_call":
                total_tool_calls += 1
                name = data.get("name", "unknown")
                tool_frequencies[name] = tool_frequencies.get(name, 0) + 1
                if data.get("success", False):
                    tool_success_count += 1
                tool_durations.append(data.get("duration", 0.0))

            elif etype == "command":
                total_commands += 1
                command_durations.append(data.get("duration", 0.0))

        avg_llm_duration = sum(llm_durations) / len(llm_durations) if llm_durations else 0.0
        avg_tool_duration = sum(tool_durations) / len(tool_durations) if tool_durations else 0.0
        avg_command_duration = sum(command_durations) / len(command_durations) if command_durations else 0.0
        tool_success_rate = (tool_success_count / total_tool_calls * 100.0) if total_tool_calls else 100.0

        return {
            "llm": {
                "total_calls": total_llm_calls,
                "total_tokens": total_prompt_tokens + total_completion_tokens,
                "prompt_tokens": total_prompt_tokens,
                "completion_tokens": total_completion_tokens,
                "average_duration": avg_llm_duration
            },
            "tools": {
                "total_calls": total_tool_calls,
                "success_rate": tool_success_rate,
                "average_duration": avg_tool_duration,
                "frequencies": tool_frequencies
            },
            "commands": {
                "total_runs": total_commands,
                "average_duration": avg_command_duration
            }
        }

    @classmethod
    def export_telemetry(cls, dest_path: Path) -> int:
        """Exports all telemetry logs as a pretty JSON file to dest_path."""
        cls._init_db()
        conn = sqlite3.connect(str(cls.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, event_type, event_data, timestamp FROM telemetry_events ORDER BY id ASC")
        rows = cursor.fetchall()
        conn.close()

        records = []
        for r in rows:
            try:
                data = json.loads(r["event_data"])
            except Exception:
                data = {}
            records.append({
                "id": r["id"],
                "event_type": r["event_type"],
                "event_data": data,
                "timestamp": r["timestamp"]
            })

        dest_path = Path(dest_path).resolve()
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(dest_path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=4)
        return len(records)

    @classmethod
    def clear_telemetry(cls):
        """Deletes all logged telemetry events."""
        cls._init_db()
        conn = sqlite3.connect(str(cls.db_path))
        cursor = conn.cursor()
        cursor.execute("DELETE FROM telemetry_events")
        conn.commit()
        conn.close()
