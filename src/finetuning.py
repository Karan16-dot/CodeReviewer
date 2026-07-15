import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

class FineTuningDataPreparer:
    """Exports structured database conversation histories to JSONL format for fine-tuning."""

    @staticmethod
    def export_to_jsonl(db_path: Path, output_file: Path, session_id: Optional[str] = None) -> int:
        """
        Groups message logs from SQLite by session and writes them to JSONL format.
        Only exports sessions containing at least one user and one assistant message.
        Returns the number of conversations successfully exported.
        """
        db_path = Path(db_path).resolve()
        output_file = Path(output_file).resolve()
        output_file.parent.mkdir(parents=True, exist_ok=True)

        if not db_path.exists():
            return 0

        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if session_id:
            cursor.execute(
                "SELECT session_id, role, content, tool_calls FROM messages WHERE session_id = ? ORDER BY id ASC",
                (session_id,)
            )
        else:
            cursor.execute(
                "SELECT session_id, role, content, tool_calls FROM messages ORDER BY session_id, id ASC"
            )

        rows = cursor.fetchall()
        conn.close()

        # Group by session_id
        sessions = {}
        for r in rows:
            sid = r["session_id"]
            if sid not in sessions:
                sessions[sid] = []

            role = r["role"]
            content = r["content"]
            tool_calls = r["tool_calls"]

            msg = {"role": role}
            msg["content"] = content if content else ""

            if tool_calls and role == "assistant":
                try:
                    msg["tool_calls"] = json.loads(tool_calls)
                except Exception:
                    pass

            if role == "tool" and tool_calls:
                try:
                    tc_info = json.loads(tool_calls)
                    if tc_info and isinstance(tc_info, list) and len(tc_info) > 0:
                        msg["tool_call_id"] = tc_info[0].get("id", "call-id")
                        msg["name"] = tc_info[0].get("name", "tool-name")
                except Exception:
                    pass

            sessions[sid].append(msg)

        valid_conversations_count = 0
        with open(output_file, "w", encoding="utf-8") as f:
            for sid, messages in sessions.items():
                has_user = any(m["role"] == "user" for m in messages)
                has_assistant = any(m["role"] == "assistant" for m in messages)

                if has_user and has_assistant:
                    cleaned_messages = []
                    for m in messages:
                        cleaned_m = {"role": m["role"], "content": m.get("content", "")}
                        if "tool_calls" in m:
                            cleaned_m["tool_calls"] = m["tool_calls"]
                        if "tool_call_id" in m:
                            cleaned_m["tool_call_id"] = m["tool_call_id"]
                            cleaned_m["name"] = m.get("name", "tool_name")
                        cleaned_messages.append(cleaned_m)

                    f.write(json.dumps({"messages": cleaned_messages}) + "\n")
                    valid_conversations_count += 1

        return valid_conversations_count


class FineTuningManager:
    """Manages uploading training JSONL files and running/monitoring OpenAI Fine-Tuning API jobs."""

    def __init__(self, client: Any):
        # Exposes the underlying OpenAI client instance
        from llm.openai_client import OpenAIClient
        if isinstance(client, OpenAIClient):
            self.client = client.client
        else:
            self.client = client

    def upload_file(self, file_path: Path) -> str:
        """Uploads a training JSONL file to OpenAI. Returns the file ID."""
        file_path = Path(file_path).resolve()
        if not file_path.exists():
            raise FileNotFoundError(f"Training file not found: {file_path}")

        try:
            with open(file_path, "rb") as f:
                response = self.client.files.create(
                    file=f,
                    purpose="fine-tune"
                )
            return response.id
        except Exception as e:
            raise RuntimeError(f"OpenAI File Upload failed: {e}")

    def start_job(self, file_id: str, base_model: str = "gpt-3.5-turbo") -> str:
        """Starts a fine-tuning job on OpenAI. Returns the job ID."""
        try:
            response = self.client.fine_tuning.jobs.create(
                training_file=file_id,
                model=base_model
            )
            return response.id
        except Exception as e:
            raise RuntimeError(f"OpenAI Fine-Tuning Job creation failed: {e}")

    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Retrieves details of a specific fine-tuning job."""
        try:
            job = self.client.fine_tuning.jobs.retrieve(job_id)
            return {
                "id": job.id,
                "status": job.status,
                "base_model": job.model,
                "fine_tuned_model": job.fine_tuned_model,
                "trained_tokens": job.trained_tokens,
                "created_at": job.created_at
            }
        except Exception as e:
            raise RuntimeError(f"Failed to retrieve job status: {e}")

    def list_jobs(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Lists recent fine-tuning jobs on OpenAI."""
        try:
            jobs = self.client.fine_tuning.jobs.list(limit=limit)
            results = []
            for job in jobs.data:
                results.append({
                    "id": job.id,
                    "status": job.status,
                    "base_model": job.model,
                    "fine_tuned_model": job.fine_tuned_model,
                    "created_at": job.created_at
                })
            return results
        except Exception as e:
            raise RuntimeError(f"Failed to list fine-tuning jobs: {e}")
