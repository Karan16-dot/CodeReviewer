import pytest
from pathlib import Path
from search import CodeSearcher

@pytest.fixture
def mock_search_dir(tmp_path):
    """Creates a temporary folder structure for search testing."""
    # Text file
    (tmp_path / "info.txt").write_text(
        "The quick brown fox jumps over the lazy dog.\nImportant instructions inside.",
        encoding="utf-8"
    )

    # Python file with TODO and symbol declarations
    py_content = (
        "class Animal:\n"
        "    def __init__(self, name):\n"
        "        self.name = name\n"
        "\n"
        "    async def speak(self):\n"
        "        # TODO: Implement speech synth\n"
        "        pass\n"
    )
    (tmp_path / "animals.py").write_text(py_content, encoding="utf-8")

    # Python file with bugs (unsafe eval and empty except catches)
    buggy_content = (
        "def run_code(user_input):\n"
        "    # FIXME: This is insecure\n"
        "    eval(user_input)\n"
        "\n"
        "def try_something():\n"
        "    try:\n"
        "        x = 1 / 0\n"
        "    except Exception:\n"
        "        pass\n"
    )
    (tmp_path / "utils.py").write_text(buggy_content, encoding="utf-8")

    # Ignored directory file (should not be searched)
    node_dir = tmp_path / "node_modules"
    node_dir.mkdir()
    (node_dir / "index.js").write_text("const keyword = 'fox';", encoding="utf-8")

    return tmp_path

def test_keyword_search(mock_search_dir):
    """Verify keyword text searches successfully matching literals, case-insensitively."""
    searcher = CodeSearcher(root_path=str(mock_search_dir))
    matches = searcher.search_text("fox")

    assert len(matches) == 1
    assert matches[0]["file"] == "info.txt"
    assert matches[0]["line"] == 1
    assert "fox" in matches[0]["content"]

    # Verify case-insensitive match
    matches_upper = searcher.search_text("FOX")
    assert len(matches_upper) == 1

def test_regex_search(mock_search_dir):
    """Verify regular expression matching identifies lines correctly."""
    searcher = CodeSearcher(root_path=str(mock_search_dir))

    # Match class definitions
    matches = searcher.search_text(r"^class \w+:", is_regex=True)
    assert len(matches) == 1
    assert matches[0]["file"] == "animals.py"
    assert matches[0]["line"] == 1

    # Match invalid regex throws ValueError
    with pytest.raises(ValueError):
        searcher.search_text(r"*(invalid", is_regex=True)

def test_find_todos(mock_search_dir):
    """Verify finding TODO, FIXME, HACK comments in workspace files."""
    searcher = CodeSearcher(root_path=str(mock_search_dir))
    todos = searcher.find_todos()

    # Should find TODO in animals.py and FIXME in utils.py
    assert len(todos) == 2
    files = [t["file"] for t in todos]
    assert "animals.py" in files
    assert "utils.py" in files

def test_find_symbols(mock_search_dir):
    """Verify AST symbol parsing indexes python classes and functions with lines."""
    searcher = CodeSearcher(root_path=str(mock_search_dir))

    # Test repository-wide symbols
    symbols = searcher.find_symbols()

    # In animals.py: class Animal, function __init__, function speak
    # In utils.py: function run_code, function try_something
    assert len(symbols) == 5

    animal_class = next(s for s in symbols if s["name"] == "Animal")
    assert animal_class["type"] == "class"
    assert animal_class["line"] == 1
    assert animal_class["file"] == "animals.py"

    speak_func = next(s for s in symbols if s["name"] == "speak")
    assert speak_func["type"] == "function"
    assert speak_func["line"] == 5

def test_find_bugs(mock_search_dir):
    """Verify AST bug analyzer flags empty catch blocks and eval calls."""
    searcher = CodeSearcher(root_path=str(mock_search_dir))
    bugs = searcher.find_bugs()

    # Should find 2 issues in utils.py: unsafe eval (line 3) and empty except (line 8)
    assert len(bugs) == 2

    eval_bug = next(b for b in bugs if b["type"] == "unsafe_eval_exec")
    assert eval_bug["line"] == 3
    assert "eval" in eval_bug["message"]

    except_bug = next(b for b in bugs if b["type"] == "empty_except")
    assert except_bug["line"] == 8
    assert "Empty except" in except_bug["message"]
