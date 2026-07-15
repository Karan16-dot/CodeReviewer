import os
import sys
import importlib.util
from pathlib import Path
from typing import Dict, List, Any, Callable, Optional, Type

class BasePlugin:
    """Base class that all dynamic plugins must inherit from."""
    name: str = "BasePlugin"
    description: str = "Default plugin interface."
    version: str = "1.0.0"

    def get_commands(self) -> Dict[str, Callable[[str], str]]:
        """Returns a dictionary mapping custom slash command strings to their CLI handlers."""
        return {}

    def get_tools(self) -> List[Dict[str, Any]]:
        """
        Returns a list of custom tool registrations.
        Each item is a dictionary:
        {
            "name": "tool_name",
            "func": callable_function,
            "schema": schema_dict
        }
        """
        return []


class PluginManager:
    """Scans directories and dynamically loads custom plugins, registering tools and commands."""

    def __init__(self, plugins_dir: str = "plugins", tool_registry: Optional[Any] = None):
        self.plugins_dir = Path(plugins_dir).resolve()
        self.tool_registry = tool_registry
        self.loaded_plugins: List[BasePlugin] = []
        self.commands: Dict[str, Callable[[str], str]] = {}

    def load_plugins(self):
        """Loads all Python modules inside self.plugins_dir and instantiates BasePlugin subclasses."""
        if not self.plugins_dir.exists():
            self.plugins_dir.mkdir(parents=True, exist_ok=True)
            return

        # Add plugins directory to sys.path to resolve local imports cleanly if needed
        if str(self.plugins_dir) not in sys.path:
            sys.path.insert(0, str(self.plugins_dir))

        for entry in self.plugins_dir.iterdir():
            module = None
            if entry.is_file() and entry.suffix == ".py" and entry.name != "__init__.py":
                module = self._load_module_from_file(entry)
            elif entry.is_dir() and (entry / "__init__.py").exists():
                module = self._load_module_from_dir(entry)

            if module:
                self._discover_and_register_plugins(module)

    def _load_module_from_file(self, file_path: Path) -> Optional[Any]:
        """Loads a python module dynamically from a file path."""
        module_name = file_path.stem
        try:
            spec = importlib.util.spec_from_file_location(module_name, str(file_path))
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                return module
        except Exception:
            # Ignore individual load errors to prevent system-wide startup failures
            pass
        return None

    def _load_module_from_dir(self, dir_path: Path) -> Optional[Any]:
        """Loads a python module dynamically from a package directory."""
        module_name = dir_path.name
        init_file = dir_path / "__init__.py"
        try:
            spec = importlib.util.spec_from_file_location(module_name, str(init_file))
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                return module
        except Exception:
            pass
        return None

    def _discover_and_register_plugins(self, module: Any):
        """Inspects module attributes, registers BasePlugin instances, tools, and commands."""
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, BasePlugin)
                and attr is not BasePlugin
            ):
                try:
                    plugin_instance = attr()
                    self.loaded_plugins.append(plugin_instance)
                    
                    # 1. Register commands
                    plugin_cmds = plugin_instance.get_commands()
                    for cmd, handler in plugin_cmds.items():
                        self.commands[cmd] = handler

                    # 2. Register tools
                    plugin_tools = plugin_instance.get_tools()
                    if self.tool_registry:
                        for tool in plugin_tools:
                            name = tool.get("name")
                            func = tool.get("func")
                            schema = tool.get("schema")
                            if name and func and schema:
                                self.tool_registry.register(name, func, schema)
                except Exception:
                    pass

    def get_command(self, cmd_name: str) -> Optional[Callable[[str], str]]:
        """Returns the command handler associated with custom plugin commands if registered."""
        return self.commands.get(cmd_name)
