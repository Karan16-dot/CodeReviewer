import pytest
import git
import os
from pathlib import Path
from git_manager import GitManager

@pytest.fixture
def temp_git_repo(tmp_path):
    """Fixture that initializes a temporary Git repository for testing VCS commands."""
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()
    repo = git.Repo.init(repo_dir)

    # Set up basic Git configs so commits can be created successfully
    with repo.config_writer() as config:
        config.set_value("user", "name", "Test User")
        config.set_value("user", "email", "testuser@example.com")

    # Create an initial commit to avoid empty repository constraints in some tests
    initial_file = repo_dir / "init.txt"
    initial_file.write_text("initial content", encoding="utf-8")
    repo.index.add(["init.txt"])
    repo.index.commit("Initial commit")

    return repo_dir

def test_git_manager_invalid_path(tmp_path):
    """Verify that GitManager raises a ValueError when initialized on a non-git directory."""
    with pytest.raises(ValueError):
        GitManager(repo_path=str(tmp_path))

def test_git_manager_status(temp_git_repo):
    """Verify GitManager correctly classifies untracked, modified, and staged files."""
    mgr = GitManager(repo_path=str(temp_git_repo))

    # 1. Check clean status
    status = mgr.get_status()
    assert not status["staged"]
    assert not status["modified"]
    assert not status["untracked"]

    # 2. Add an untracked file
    untracked_file = temp_git_repo / "new.txt"
    untracked_file.write_text("hello", encoding="utf-8")
    status = mgr.get_status()
    assert "new.txt" in status["untracked"]

    # 3. Stage the file
    mgr.repo.index.add(["new.txt"])
    status = mgr.get_status()
    assert "new.txt" in status["staged"]
    assert "new.txt" not in status["untracked"]

    # 4. Modify a committed file
    init_file = temp_git_repo / "init.txt"
    init_file.write_text("updated content", encoding="utf-8")
    status = mgr.get_status()
    assert "init.txt" in status["modified"]

def test_git_manager_commit(temp_git_repo):
    """Verify that GitManager successfully commits files and moves HEAD."""
    mgr = GitManager(repo_path=str(temp_git_repo))

    # Add and stage a new file
    new_file = temp_git_repo / "file.txt"
    new_file.write_text("content", encoding="utf-8")

    commit_sha = mgr.commit("Added file.txt")
    assert commit_sha is not None

    # Check commit was registered in the log
    log = mgr.get_log(limit=1)
    assert len(log) == 1
    assert log[0]["message"] == "Added file.txt"

def test_git_manager_branches(temp_git_repo):
    """Verify that GitManager creates and checkouts branches."""
    mgr = GitManager(repo_path=str(temp_git_repo))

    # Query initial branches
    branch_info = mgr.get_branches()
    assert branch_info["active"] == "master" or branch_info["active"] == "main"

    # Create new branch and checkout
    mgr.create_branch("feature-branch", checkout=True)
    branch_info = mgr.get_branches()
    assert branch_info["active"] == "feature-branch"
    assert "feature-branch" in branch_info["branches"]

def test_git_manager_diff(temp_git_repo):
    """Verify that GitManager retrieves file diff details."""
    mgr = GitManager(repo_path=str(temp_git_repo))

    # Make an unstaged modification
    init_file = temp_git_repo / "init.txt"
    init_file.write_text("diff content", encoding="utf-8")

    diff = mgr.get_diff()
    assert "diff content" in diff
    assert "initial content" in diff
