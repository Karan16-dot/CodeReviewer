import sys
from pathlib import Path
from main import main

def test_main_output(capsys):
    """
    Test that the main CLI starts and prints the correct version string.
    """
    main()
    captured = capsys.readouterr()
    assert "Claude Code Agent v0.1" in captured.out
