import pytest
from unittest.mock import patch, MagicMock
from main import main

def test_main_runs_cli():
    """Verify that main() instantiates InteractiveCLI and runs it."""
    with patch("main.InteractiveCLI") as mock_cli_class:
        mock_cli_instance = MagicMock()
        mock_cli_class.return_value = mock_cli_instance

        main()

        mock_cli_class.assert_called_once()
        mock_cli_instance.run.assert_called_once()
