import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from executor import CommandRunner
from editor import FileEditor

class TracebackParser:
    """Parses output logs to find traceback file references and line numbers."""

    @staticmethod
    def parse_traceback(output: str) -> List[Dict[str, Any]]:
        """
        Parses console traceback records to locate failing source files and line numbers.
        Returns a list of dicts: [{'file': 'path/to/file.py', 'line': 123}] ordered from oldest to newest call.
        """
        pattern = r'File "([^"]+)", line (\d+)'
        matches = re.findall(pattern, output)
        results = []
        for file_path, line_str in matches:
            # Skip python standard library files or package index internal files (e.g. site-packages, python3X)
            if "site-packages" in file_path or "lib\\" in file_path.lower() or "lib/" in file_path.lower() or "<" in file_path:
                continue
            results.append({
                "file": file_path,
                "line": int(line_str)
            })
        return results


class SelfCorrectionOrchestrator:
    """Runs shell verification commands, captures tracebacks, and coordinates LLM self-correction loops."""

    def __init__(self, client: Any, workspace_root: str = "."):
        self.client = client
        self.workspace_root = Path(workspace_root).resolve()
        self.runner = CommandRunner(workspace_root=str(self.workspace_root))
        self.editor = FileEditor()

    def run_command_with_correction(self, command: str, max_retries: int = 3) -> Dict[str, Any]:
        """
        Executes the command. If a non-zero exit code is encountered, parses traceback,
        retrieves file context, calls client to retrieve code edits, and retries.
        """
        retries = 0
        current_cmd = command
        log_steps = []

        while retries <= max_retries:
            try:
                stdout, stderr, exit_code = self.runner.run(current_cmd)
                output = stdout + "\n" + stderr
            except Exception as e:
                output = str(e)
                exit_code = 1

            log_steps.append({
                "retry": retries,
                "command": current_cmd,
                "exit_code": exit_code,
                "output_preview": output[:500] + "..." if len(output) > 500 else output
            })

            if exit_code == 0:
                return {
                    "status": "success",
                    "retries": retries,
                    "output": output,
                    "steps": log_steps
                }

            retries += 1
            if retries > max_retries:
                break

            # Parse traceback to isolate file + line
            errors = TracebackParser.parse_traceback(output)
            if not errors:
                # If we cannot locate source files, we cannot apply a correction patch
                break

            # Target the last traceback item (most likely failure cause)
            target = errors[-1]
            file_rel = target["file"]
            line_no = target["line"]

            # Locate file in local workspace
            file_path = Path(file_rel)
            if not file_path.is_absolute():
                file_path = self.workspace_root / file_path

            if not file_path.exists():
                # Attempt to find under src/
                src_candidate = self.workspace_root / "src" / file_rel
                if src_candidate.exists():
                    file_path = src_candidate
                else:
                    break

            # Read code lines around failure line (e.g. 10 lines window)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
            except Exception:
                break

            start_line = max(1, line_no - 10)
            end_line = min(len(lines), line_no + 10)
            context_code = "".join(f"{idx}: {lines[idx-1]}" for idx in range(start_line, end_line + 1))

            # Prompt LLM to solve the error
            prompt = f"""You are a self-correction assistant. The command '{current_cmd}' failed with exit code {exit_code}.
Here is the error output:
{output}

We detected the failure occurred in file '{file_path.name}' around line {line_no}.
Here is the file context:
{context_code}

Please analyze the error and provide a search-and-replace fix.
Your response MUST contain exactly one block in the format:
<<<<
[exact search lines from the context above, keeping line numbers stripped]
====
[replacement lines]
>>>>
"""
            messages = [{"role": "user", "content": prompt}]
            try:
                stream = self.client.stream_chat(messages)
                response = ""
                for chunk in stream:
                    if isinstance(chunk, str):
                        response += chunk
            except Exception as e:
                log_steps.append({"error": f"LLM stream failure: {e}"})
                break

            # Extract search-replace block from response
            match = re.search(r"<<<<\s*(.*?)\s*====\s*(.*?)\s*>>>>", response, re.DOTALL)
            if not match:
                match = re.search(r"<<<<(.*?)====(.*?)>>>>", response, re.DOTALL)

            if match:
                search_block = match.group(1).strip()
                replace_block = match.group(2).strip()

                try:
                    # Apply changes to target file
                    modified = self.editor.apply_replacement(file_path, search_block, replace_block)
                    self.editor.write(file_path, modified)
                    log_steps[-1]["applied_fix"] = {
                        "file": file_path.name,
                        "search": search_block,
                        "replace": replace_block
                    }
                except Exception as e:
                    log_steps[-1]["applied_fix_error"] = str(e)
                    break
            else:
                log_steps[-1]["applied_fix_error"] = "Failed to parse <<<< SEARCH ==== REPLACE >>>> blocks from LLM return."
                break

        return {
            "status": "failure",
            "retries": retries - 1,
            "output": f"Failed after {retries - 1} self-correction retries. Last output:\n{output}",
            "steps": log_steps
        }
