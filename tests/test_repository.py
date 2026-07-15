import pytest
from pathlib import Path
from repository import RepositoryExplorer

@pytest.fixture
def mock_repo_dir(tmp_path):
    """Creates a temporary folder structure to simulate a repository."""
    # Source files
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "main.py").write_text("print('hello')", encoding="utf-8")
    (src_dir / "utils.py").write_text("# utility module", encoding="utf-8")

    # Test files
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_main.py").write_text("def test(): pass", encoding="utf-8")

    # Document files
    (tmp_path / "README.md").write_text("# Mock Repo", encoding="utf-8")

    # Ignored directories (.git)
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text("[core]\nrepositoryformatversion = 0", encoding="utf-8")

    # Ignored directories (node_modules)
    node_dir = tmp_path / "node_modules"
    node_dir.mkdir()
    dep_dir = node_dir / "express"
    dep_dir.mkdir(parents=True)
    (dep_dir / "index.js").write_text("module.exports = {};", encoding="utf-8")

    # Ignored directory (venv)
    venv_dir = tmp_path / "venv"
    venv_dir.mkdir()
    (venv_dir / "pip.exe").write_bytes(b"mock-binary")

    return tmp_path

def test_scan_files_ignores_standard_directories(mock_repo_dir):
    """Verify that scan_files excludes standard ignored folders like .git and node_modules."""
    explorer = RepositoryExplorer(root_path=str(mock_repo_dir))
    files = explorer.scan_files()

    # Convert paths to relative strings for easy assertions
    relative_files = [f.relative_to(mock_repo_dir).as_posix() for f in files]

    expected = [
        "README.md",
        "src/main.py",
        "src/utils.py",
        "tests/test_main.py"
    ]

    assert relative_files == expected

    # Verify that ignored files are NOT in the list
    assert "node_modules/express/index.js" not in relative_files
    assert ".git/config" not in relative_files
    assert "venv/pip.exe" not in relative_files

def test_count_files_by_language(mock_repo_dir):
    """Verify language detection aggregates file counts correctly based on extensions."""
    explorer = RepositoryExplorer(root_path=str(mock_repo_dir))
    stats = explorer.count_files_by_language()

    assert stats.get("Python") == 3
    assert stats.get("Markdown") == 1
    assert "JavaScript" not in stats  # express/index.js should be ignored

def test_build_tree_layout(mock_repo_dir):
    """Verify build_tree compiles a correct visual directory structure string."""
    explorer = RepositoryExplorer(root_path=str(mock_repo_dir))
    tree = explorer.build_tree()

    # The top level name should be the directory name
    assert mock_repo_dir.name in tree
    assert "├── src/" in tree
    assert "│   ├── main.py" in tree
    assert "│   └── utils.py" in tree
    assert "├── tests/" in tree
    assert "│   └── test_main.py" in tree
    assert "└── README.md" in tree

    # Ignored elements should not be present in the tree
    assert ".git" not in tree
    assert "node_modules" not in tree
    assert "venv" not in tree

def test_invalid_path_handling(tmp_path):
    """Verify that invalid paths raise appropriate standard exceptions."""
    non_existent = tmp_path / "does_not_exist"
    explorer_non_existent = RepositoryExplorer(root_path=str(non_existent))

    with pytest.raises(FileNotFoundError):
        explorer_non_existent.scan_files()

    with pytest.raises(FileNotFoundError):
        explorer_non_existent.build_tree()

    # Try passing a file instead of a directory
    dummy_file = tmp_path / "dummy.txt"
    dummy_file.write_text("test")
    explorer_file = RepositoryExplorer(root_path=str(dummy_file))

    with pytest.raises(NotADirectoryError):
        explorer_file.scan_files()

    with pytest.raises(NotADirectoryError):
        explorer_file.build_tree()
