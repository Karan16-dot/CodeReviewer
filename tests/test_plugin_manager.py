import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock
from plugin_manager import BasePlugin, PluginManager

def test_plugin_manager_loads_valid_plugin(tmp_path):
    """Verify that PluginManager scans folders and dynamically loads BasePlugin subclasses."""
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()

    # Create a dynamic plugin file content
    plugin_content = """from plugin_manager import BasePlugin

class TestDynamicPlugin(BasePlugin):
    name = "TestDynamicPlugin"
    description = "A temporary dynamic plugin for unit testing."
    version = "2.0.1"

    def get_commands(self):
        return {
            "/plug-test": self.handle_command
        }

    def get_tools(self):
        return [
            {
                "name": "plug_tool",
                "func": self.run_tool,
                "schema": {
                    "name": "plug_tool",
                    "description": "Dynamic tool"
                }
            }
        ]

    def handle_command(self, arg):
        return f"Plugin Cmd Echo: {arg}"

    def run_tool(self):
        return "Dynamic Tool Executed"
"""

    plugin_file = plugins_dir / "my_dynamic_plugin.py"
    plugin_file.write_text(plugin_content, encoding="utf-8")

    # Mock tool registry
    mock_registry = MagicMock()

    # Initialize and run loader
    manager = PluginManager(plugins_dir=str(plugins_dir), tool_registry=mock_registry)
    manager.load_plugins()

    # Assert plugin was discovered and loaded
    assert len(manager.loaded_plugins) == 1
    plugin = manager.loaded_plugins[0]
    assert plugin.name == "TestDynamicPlugin"
    assert plugin.description == "A temporary dynamic plugin for unit testing."
    assert plugin.version == "2.0.1"

    # Assert tool was registered on the registry
    mock_registry.register.assert_called_once()
    call_args = mock_registry.register.call_args[0]
    assert call_args[0] == "plug_tool"
    assert call_args[2] == {"name": "plug_tool", "description": "Dynamic tool"}

    # Assert command is registered inside the manager
    cmd_handler = manager.get_command("/plug-test")
    assert cmd_handler is not None
    res = cmd_handler("antigravity")
    assert res == "Plugin Cmd Echo: antigravity"


def test_plugin_manager_handles_missing_dir(tmp_path):
    """Verify that PluginManager handles non-existent plugin directories gracefully."""
    non_existent_dir = tmp_path / "missing_plugins"
    manager = PluginManager(plugins_dir=str(non_existent_dir))
    manager.load_plugins()

    # Should create directory and load 0 plugins
    assert non_existent_dir.exists()
    assert len(manager.loaded_plugins) == 0
