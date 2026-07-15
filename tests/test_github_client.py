import pytest
import json
import base64
from pathlib import Path
from unittest.mock import patch, MagicMock
from github_client import GitHubManager, GitHubError

def test_github_manager_get_repo_tree():
    """Verify that get_repo_tree queries GitHub API and returns tree list."""
    manager = GitHubManager(token="test-token")
    
    # Mock response data
    mock_tree_data = {
        "tree": [
            {"path": "src/main.py", "type": "blob"},
            {"path": "tests", "type": "tree"}
        ]
    }
    
    # Mock urlopen
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(mock_tree_data).encode("utf-8")
    
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        tree = manager.get_repo_tree("owner", "repo")
        assert len(tree) == 2
        assert tree[0]["path"] == "src/main.py"
        assert tree[0]["type"] == "blob"
        
        mock_urlopen.assert_called_once()
        req = mock_urlopen.call_args[0][0]
        assert req.get_header("Authorization") == "token test-token"
        assert req.get_header("Accept") == "application/vnd.github.v3+json"


def test_github_manager_download_file():
    """Verify that download_file fetches contents and base64 decodes them."""
    manager = GitHubManager()
    
    # "Hello GitHub" base64 is SGVsbG8gR2l0SHVi
    mock_file_data = {
        "content": "SGVsbG8g\nR2l0SHVi\n"
    }
    
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(mock_file_data).encode("utf-8")
    
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        content = manager.download_file("owner", "repo", "src/main.py")
        assert content == "Hello GitHub"


def test_github_manager_create_pull_request():
    """Verify that create_pull_request sends POST payload and returns PR metrics."""
    manager = GitHubManager()
    
    mock_pr_response = {
        "number": 12,
        "html_url": "https://github.com/owner/repo/pull/12"
    }
    
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(mock_pr_response).encode("utf-8")
    
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        res = manager.create_pull_request(
            "owner", "repo", "Fix bugs", "PR description", "dev-branch", "main"
        )
        assert res["number"] == 12
        assert res["html_url"] == "https://github.com/owner/repo/pull/12"
        
        req = mock_urlopen.call_args[0][0]
        assert req.method == "POST"
        payload = json.loads(req.data.decode("utf-8"))
        assert payload["title"] == "Fix bugs"
        assert payload["head"] == "dev-branch"


def test_github_manager_clone_repository(tmp_path):
    """Verify clone_repository retrieves trees and downloads blobs, writing them to disk."""
    manager = GitHubManager()
    
    mock_tree = [
        {"path": "src/main.py", "type": "blob"},
        {"path": "config/settings.json", "type": "blob"},
        {"path": "docs", "type": "tree"}
    ]
    
    def mock_download(owner, repo, file_path, ref):
        if file_path == "src/main.py":
            return "print('Hello')"
        elif file_path == "config/settings.json":
            return "{}"
        return ""
    
    checkout_dir = tmp_path / "checkout"
    
    with patch.object(manager, "get_repo_tree", return_value=mock_tree), \
         patch.object(manager, "download_file", side_effect=mock_download):
             
        count = manager.clone_repository("owner/repo", str(checkout_dir))
        assert count == 2
        
        # Verify files exist on disk
        main_py = checkout_dir / "src" / "main.py"
        assert main_py.exists()
        assert main_py.read_text(encoding="utf-8") == "print('Hello')"
        
        settings_json = checkout_dir / "config" / "settings.json"
        assert settings_json.exists()
        assert settings_json.read_text(encoding="utf-8") == "{}"
