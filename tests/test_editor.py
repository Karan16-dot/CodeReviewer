import pytest
from pathlib import Path
from editor import FileEditor

def test_backup_and_undo(tmp_path):
    """Verify that file backing up and manual restoration works."""
    file_path = tmp_path / "hello.txt"
    file_path.write_text("Hello World", encoding="utf-8")

    backup_dir = tmp_path / "backups"
    editor = FileEditor(backup_dir=str(backup_dir))

    # Verify backup copies file
    assert editor.backup(file_path) is True
    backup_path = editor.get_backup_path(file_path)
    assert backup_path.exists()
    assert backup_path.read_text(encoding="utf-8") == "Hello World"

    # Modify file
    file_path.write_text("Modified Content", encoding="utf-8")

    # Undo
    assert editor.undo(file_path) is True
    assert file_path.read_text(encoding="utf-8") == "Hello World"
    # Backup file should be cleaned up after restore
    assert not backup_path.exists()

def test_write_triggers_automatic_backup(tmp_path):
    """Verify that writing to an existing file automatically creates a backup."""
    file_path = tmp_path / "hello.txt"
    file_path.write_text("Original content", encoding="utf-8")

    editor = FileEditor(backup_dir=str(tmp_path / "backups"))
    editor.write(file_path, "Overwritten content")

    assert file_path.read_text(encoding="utf-8") == "Overwritten content"

    # Undo should restore original
    assert editor.undo(file_path) is True
    assert file_path.read_text(encoding="utf-8") == "Original content"

def test_undo_new_file_deletes_it(tmp_path):
    """Verify that rolling back a newly created file deletes it from disk."""
    file_path = tmp_path / "new_file.txt"
    editor = FileEditor(backup_dir=str(tmp_path / "backups"))

    editor.write(file_path, "Brand new content")
    assert file_path.exists()

    assert editor.undo(file_path) is True
    assert not file_path.exists()

def test_apply_replacement_success(tmp_path):
    """Verify that apply_replacement updates content correctly when search block matches exactly once."""
    file_path = tmp_path / "code.py"
    original = "def main():\n    print('start')\n    print('end')\n"
    file_path.write_text(original, encoding="utf-8")

    editor = FileEditor()
    new_content = editor.apply_replacement(
        file_path,
        "    print('start')",
        "    print('hello')\n    print('world')"
    )

    expected = "def main():\n    print('hello')\n    print('world')\n    print('end')\n"
    assert new_content == expected

def test_apply_replacement_not_found(tmp_path):
    """Verify that apply_replacement raises ValueError if target search block is missing."""
    file_path = tmp_path / "code.py"
    file_path.write_text("foo bar", encoding="utf-8")

    editor = FileEditor()
    with pytest.raises(ValueError) as exc_info:
        editor.apply_replacement(file_path, "baz", "qux")
    assert "not found" in str(exc_info.value)

def test_apply_replacement_multiple_matches(tmp_path):
    """Verify that apply_replacement raises ValueError if search block matches more than once."""
    file_path = tmp_path / "code.py"
    file_path.write_text("duplicate\nduplicate\n", encoding="utf-8")

    editor = FileEditor()
    with pytest.raises(ValueError) as exc_info:
        editor.apply_replacement(file_path, "duplicate", "single")
    assert "matches 2 occurrences" in str(exc_info.value)

def test_get_diff(tmp_path):
    """Verify that get_diff generates formatted unified diffs."""
    file_path = tmp_path / "test.txt"
    file_path.write_text("line 1\nline 2\n", encoding="utf-8")

    editor = FileEditor()
    diff = editor.get_diff(file_path, "line 1\nline 3\n")

    assert "a/test.txt" in diff
    assert "b/test.txt" in diff
    assert "-line 2" in diff
    assert "+line 3" in diff
