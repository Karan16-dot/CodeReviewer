import pytest
from pathlib import Path
from reader import FileReader

def test_read_file_utf8(tmp_path):
    """Verify that FileReader successfully reads standard UTF-8 files."""
    file_path = tmp_path / "utf8.txt"
    content = "Hello world! 😊"
    file_path.write_text(content, encoding="utf-8")

    reader = FileReader()
    assert reader.read_file(file_path) == content

def test_read_file_latin1(tmp_path):
    """Verify that FileReader successfully reads Latin-1 encoded files using fallback."""
    file_path = tmp_path / "latin1.txt"
    content = "cliché café"
    # Write using ISO-8859-1 (Latin-1) encoding
    with open(file_path, "w", encoding="latin-1") as f:
        f.write(content)

    reader = FileReader()
    assert reader.read_file(file_path) == content

def test_read_file_utf16(tmp_path):
    """Verify that FileReader successfully reads UTF-16 encoded files using fallback."""
    file_path = tmp_path / "utf16.txt"
    content = "UTF-16 encoding text"
    with open(file_path, "w", encoding="utf-16") as f:
        f.write(content)

    reader = FileReader()
    assert reader.read_file(file_path) == content

def test_read_file_exceptions(tmp_path):
    """Verify that FileReader raises correct standard exceptions for directory paths or missing files."""
    reader = FileReader()

    # Non-existent file
    non_existent = tmp_path / "does_not_exist.txt"
    with pytest.raises(FileNotFoundError):
        reader.read_file(non_existent)

    # Directory instead of file
    directory = tmp_path / "sub_dir"
    directory.mkdir()
    with pytest.raises(IsADirectoryError):
        reader.read_file(directory)

def test_count_tokens():
    """Verify that count_tokens returns accurate OpenAI token counts."""
    reader = FileReader()
    text = "Hello, this is a test of the token counter."

    # Using gpt-4o-mini
    tokens = reader.count_tokens(text, model="gpt-4o-mini")
    assert tokens > 0
    # The sentence "Hello, this is a test of the token counter." has 11 tokens under cl100k_base
    assert tokens == 11

def test_chunk_text():
    """Verify that chunk_text partitions long text with an overlapping token window."""
    reader = FileReader()
    # "one two three four five six seven eight nine ten" -> approx 10 tokens
    text = "one two three four five six seven eight nine ten"

    # Chunk with very small max_tokens
    chunks = reader.chunk_text(text, max_tokens=4, overlap_tokens=1)

    assert len(chunks) > 1
    # Check that parts of the text are present in chunks
    assert "one" in chunks[0]
    assert "ten" in chunks[-1]
