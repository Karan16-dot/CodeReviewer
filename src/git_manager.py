import git
from pathlib import Path
from typing import List, Dict, Any

class GitManager:
    """Manages Git repository status, commits, branching, diffs, and logs using GitPython."""

    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path).resolve()
        try:
            self.repo = git.Repo(self.repo_path, search_parent_directories=True)
        except git.InvalidGitRepositoryError:
            raise ValueError(f"Path is not a valid git repository: {self.repo_path}")

    def get_status(self) -> Dict[str, List[str]]:
        """Returns untracked, modified, staged, and deleted files status."""
        status = {
            "staged": [],
            "modified": [],
            "untracked": [],
            "deleted": []
        }

        # Staged files (compared HEAD to index)
        try:
            head = self.repo.head.commit
            diff_staged = self.repo.index.diff(head)
            for d in diff_staged:
                status["staged"].append(d.a_path)
        except ValueError:
            # No commits yet, check index entries
            for path, _ in self.repo.index.entries.keys():
                status["staged"].append(path)

        # Modified and deleted files (compared index to working tree)
        diff_worktree = self.repo.index.diff(None)
        for d in diff_worktree:
            if d.deleted_file:
                status["deleted"].append(d.a_path)
            else:
                status["modified"].append(d.a_path)

        # Untracked files
        status["untracked"] = self.repo.untracked_files

        return status

    def commit(self, message: str, files: List[str] = None) -> str:
        """Stages files (all if None) and commits with message. Returns commit hash."""
        if not message or not message.strip():
            raise ValueError("Commit message cannot be empty.")

        try:
            if files:
                self.repo.index.add(files)
            else:
                # Stage all modified/untracked files
                self.repo.git.add(A=True)

            commit_obj = self.repo.index.commit(message)
            return commit_obj.hexsha
        except Exception as e:
            raise Exception(f"Git commit failed: {e}")

    def get_branches(self) -> Dict[str, Any]:
        """Returns active branch name and list of local branches."""
        try:
            active_branch = self.repo.active_branch.name
        except TypeError:
            # Detached HEAD
            active_branch = "HEAD (detached)"

        local_branches = [b.name for b in self.repo.branches]
        return {
            "active": active_branch,
            "branches": local_branches
        }

    def create_branch(self, branch_name: str, checkout: bool = True) -> str:
        """Creates a new branch. Optionally checkouts to it."""
        try:
            new_branch = self.repo.create_head(branch_name)
            if checkout:
                self.repo.head.reference = new_branch
                self.repo.head.reset(index=True, working_tree=True)
            return f"Created branch '{branch_name}'" + (" and checked out" if checkout else "")
        except Exception as e:
            raise Exception(f"Failed to create branch '{branch_name}': {e}")

    def get_diff(self, file_path: str = None) -> str:
        """Returns current unstaged diff. If file_path is specified, filters by it."""
        try:
            diff_text = self.repo.git.diff(file_path) if file_path else self.repo.git.diff()
            return diff_text
        except Exception as e:
            raise Exception(f"Failed to fetch diff: {e}")

    def get_log(self, limit: int = 5) -> List[Dict[str, str]]:
        """Returns recent commit log info: hash, author, date, message."""
        try:
            commits = list(self.repo.iter_commits(max_count=limit))
            log_entries = []
            for c in commits:
                log_entries.append({
                    "hash": c.hexsha[:7],
                    "author": c.author.name,
                    "date": c.committed_datetime.strftime("%Y-%m-%d %H:%M:%S"),
                    "message": c.summary
                })
            return log_entries
        except Exception as e:
            raise Exception(f"Failed to fetch commit log: {e}")
