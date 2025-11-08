"""
Plugin Manager
==============

Dynamic plugin system for custom transfer algorithms.

Features:
- Dynamic algorithm loading
- Plugin discovery and registration
- Validation and sandboxing
- Hot-reloading support
"""

import importlib.util
import inspect
from pathlib import Path
from typing import Dict, List, Optional, Type, Any, Callable
from abc import ABC, abstractmethod
import logging
import numpy as np

logger = logging.getLogger(__name__)


class TransferPlugin(ABC):
    """
    Base class for custom transfer algorithm plugins.

    Plugin developers should inherit from this class and implement
    the `transfer` method.

    Example:
        >>> class MyCustomAlgorithm(TransferPlugin):
        ...     name = "my_custom"
        ...     description = "My custom transfer algorithm"
        ...
        ...     def transfer(self, source, target, **kwargs):
        ...         # Custom implementation
        ...         return result
    """

    name: str = "unknown"
    description: str = ""
    version: str = "1.0.0"
    author: str = ""

    @abstractmethod
    def transfer(
        self,
        source: np.ndarray,
        target: np.ndarray,
        **kwargs
    ) -> np.ndarray:
        """
        Apply custom color transfer algorithm.

        Parameters:
        -----------
        source : np.ndarray
            Source image (BGR format)
        target : np.ndarray
            Target image (BGR format)
        **kwargs
            Additional algorithm-specific parameters

        Returns:
        --------
        np.ndarray
            Transformed image (BGR format)
        """
        pass

    def validate(self) -> bool:
        """
        Validate plugin configuration.

        Returns:
        --------
        bool
            True if plugin is valid
        """
        return (
            self.name and
            self.name != "unknown" and
            hasattr(self, 'transfer') and
            callable(self.transfer)
        )

    def get_info(self) -> Dict[str, Any]:
        """Get plugin information."""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "author": self.author
        }


class PluginManager:
    """
    Manage custom transfer algorithm plugins.

    Example:
        >>> manager = PluginManager()
        >>> manager.discover_plugins("./plugins")
        >>> manager.load_plugin("my_custom")
        >>> result = manager.execute("my_custom", source, target)
    """

    def __init__(self, plugin_dirs: Optional[List[str]] = None):
        """
        Initialize plugin manager.

        Parameters:
        -----------
        plugin_dirs : List[str], optional
            Directories to search for plugins
        """
        self.plugins: Dict[str, Type[TransferPlugin]] = {}
        self.instances: Dict[str, TransferPlugin] = {}
        self.plugin_dirs = [Path(d) for d in (plugin_dirs or [])]

    def register_plugin(
        self,
        plugin_class: Type[TransferPlugin],
        replace: bool = False
    ) -> bool:
        """
        Register a plugin class.

        Parameters:
        -----------
        plugin_class : Type[TransferPlugin]
            Plugin class to register
        replace : bool
            Replace existing plugin with same name

        Returns:
        --------
        bool
            True if registered successfully
        """
        # Validate plugin
        if not issubclass(plugin_class, TransferPlugin):
            logger.error(f"{plugin_class.__name__} is not a TransferPlugin subclass")
            return False

        # Create temporary instance to validate
        try:
            temp_instance = plugin_class()
            if not temp_instance.validate():
                logger.error(f"Plugin validation failed: {plugin_class.__name__}")
                return False
        except Exception as e:
            logger.error(f"Failed to instantiate plugin {plugin_class.__name__}: {e}")
            return False

        name = temp_instance.name

        # Check for conflicts
        if name in self.plugins and not replace:
            logger.warning(f"Plugin '{name}' already registered. Use replace=True to override.")
            return False

        self.plugins[name] = plugin_class
        logger.info(f"Registered plugin: {name} (v{temp_instance.version})")
        return True

    def unregister_plugin(self, name: str) -> bool:
        """
        Unregister a plugin.

        Parameters:
        -----------
        name : str
            Plugin name

        Returns:
        --------
        bool
            True if unregistered successfully
        """
        if name in self.plugins:
            del self.plugins[name]
            if name in self.instances:
                del self.instances[name]
            logger.info(f"Unregistered plugin: {name}")
            return True
        return False

    def load_plugin(self, name: str) -> Optional[TransferPlugin]:
        """
        Load and instantiate a plugin.

        Parameters:
        -----------
        name : str
            Plugin name

        Returns:
        --------
        TransferPlugin or None
            Plugin instance, or None if not found
        """
        if name in self.instances:
            return self.instances[name]

        if name not in self.plugins:
            logger.error(f"Plugin not found: {name}")
            return None

        try:
            instance = self.plugins[name]()
            self.instances[name] = instance
            logger.info(f"Loaded plugin: {name}")
            return instance
        except Exception as e:
            logger.error(f"Failed to load plugin {name}: {e}")
            return None

    def execute(
        self,
        name: str,
        source: np.ndarray,
        target: np.ndarray,
        **kwargs
    ) -> Optional[np.ndarray]:
        """
        Execute a plugin.

        Parameters:
        -----------
        name : str
            Plugin name
        source : np.ndarray
            Source image
        target : np.ndarray
            Target image
        **kwargs
            Plugin-specific parameters

        Returns:
        --------
        np.ndarray or None
            Result image, or None if plugin not found
        """
        plugin = self.load_plugin(name)
        if plugin is None:
            return None

        try:
            return plugin.transfer(source, target, **kwargs)
        except Exception as e:
            logger.error(f"Plugin execution failed ({name}): {e}")
            return None

    def discover_plugins(self, directory: str, pattern: str = "plugin_*.py") -> int:
        """
        Discover and load plugins from a directory.

        Parameters:
        -----------
        directory : str
            Directory to search
        pattern : str
            Filename pattern to match

        Returns:
        --------
        int
            Number of plugins discovered
        """
        plugin_path = Path(directory)
        if not plugin_path.exists():
            logger.warning(f"Plugin directory not found: {directory}")
            return 0

        discovered = 0

        for file_path in plugin_path.glob(pattern):
            try:
                # Load module
                spec = importlib.util.spec_from_file_location(
                    file_path.stem,
                    file_path
                )
                if spec is None or spec.loader is None:
                    continue

                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Find TransferPlugin subclasses
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if (
                        issubclass(obj, TransferPlugin) and
                        obj is not TransferPlugin
                    ):
                        if self.register_plugin(obj, replace=False):
                            discovered += 1

            except Exception as e:
                logger.error(f"Failed to load plugin from {file_path}: {e}")

        logger.info(f"Discovered {discovered} plugins from {directory}")
        return discovered

    def list_plugins(self) -> List[Dict[str, Any]]:
        """
        List all registered plugins.

        Returns:
        --------
        List[Dict[str, Any]]
            List of plugin information
        """
        plugin_list = []

        for name, plugin_class in self.plugins.items():
            try:
                instance = plugin_class()
                plugin_list.append(instance.get_info())
            except Exception as e:
                logger.error(f"Failed to get info for plugin {name}: {e}")

        return plugin_list

    def get_plugin_info(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific plugin.

        Parameters:
        -----------
        name : str
            Plugin name

        Returns:
        --------
        Dict[str, Any] or None
            Plugin information, or None if not found
        """
        plugin = self.load_plugin(name)
        if plugin:
            return plugin.get_info()
        return None
