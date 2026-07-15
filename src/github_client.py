import os
import json
import base64
import urllib.request
import urllib.error
import urllib.parse
from typing import Dict, Any, List, Optional
from pathlib import Path

class GitHubError(Exception):
    """Raised when GitHub API operations encounter failures."""
    pass

class GitHubManager:
    """Manages integration with the GitHub API for remote checkouts, pulls, commits, and pull requests."""

    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_PAT")
        self.base_url = "https://api.github.com"

    def _headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Claude-Code-Agent"
        }
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        return headers

    def _request(self, method: str, path: str, data: Optional[Dict[str, Any]] = None) -> Any:
        url = f"{self.base_url}{path}"
        req_data = json.dumps(data).encode("utf-8") if data else None
        
        req = urllib.request.Request(
            url,
            data=req_data,
            headers=self._headers(),
            method=method
        )
        
        try:
            with urllib.request.urlopen(req) as res:
                content = res.read().decode("utf-8")
                if content:
                    return json.loads(content)
                return {}
        except urllib.error.HTTPError as e:
            try:
                err_msg = e.read().decode("utf-8")
            except Exception:
                err_msg = e.reason
            raise GitHubError(f"GitHub API Error ({e.code}): {err_msg}")
        except Exception as e:
            raise GitHubError(f"Request failed: {e}")

    def get_repo_tree(self, owner: str, repo: str, branch: str = "main") -> List[Dict[str, Any]]:
        """Retrieves the file tree recursively for a repository."""
        path = f"/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
        res = self._request("GET", path)
        return res.get("tree", [])

    def download_file(self, owner: str, repo: str, file_path: str, ref: str = "main") -> str:
        """Fetches raw file content from a repository."""
        encoded_path = urllib.parse.quote(file_path)
        path = f"/repos/{owner}/{repo}/contents/{encoded_path}?ref={ref}"
        res = self._request("GET", path)
        
        content_b64 = res.get("content", "")
        # Remove any newline markers in base64 payload
        content_clean = content_b64.replace("\n", "").replace("\r", "")
        try:
            return base64.b64decode(content_clean).decode("utf-8")
        except Exception as e:
            raise GitHubError(f"Failed to base64 decode file content: {e}")

    def create_pull_request(self, owner: str, repo: str, title: str, body: str, head: str, base: str = "main") -> Dict[str, Any]:
        """Creates a Pull Request on GitHub."""
        path = f"/repos/{owner}/{repo}/pulls"
        data = {
            "title": title,
            "body": body,
            "head": head,
            "base": base
        }
        return self._request("POST", path, data)

    def clone_repository(self, repo_slug: str, dest_dir: str, branch: str = "main") -> int:
        """Clones a remote repository structure and files locally using the GitHub API."""
        parts = repo_slug.split("/")
        if len(parts) != 2:
            raise GitHubError("Repository slug must be in the format 'owner/repo'.")
        owner, repo = parts

        dest_path = Path(dest_dir).resolve()
        dest_path.mkdir(parents=True, exist_ok=True)

        tree = self.get_repo_tree(owner, repo, branch)
        blobs = [item for item in tree if item["type"] == "blob"]
        
        for item in blobs:
            item_path = item["path"]
            file_path = (dest_path / item_path).resolve()
            
            # Safety checks: prevent path traversal out of destination directory
            try:
                file_path.relative_to(dest_path)
            except ValueError:
                continue # Skip dangerous traversal references

            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            content = self.download_file(owner, repo, item_path, branch)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

        return len(blobs)
