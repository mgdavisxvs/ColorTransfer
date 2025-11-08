"""
API Documentation Generator
============================

Auto-generate API documentation from code.

Features:
- Extract docstrings and type hints
- Generate markdown documentation
- Create endpoint reference
- Parameter documentation
"""

import inspect
import ast
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class APIDocGenerator:
    """
    Generate API documentation from source code.

    Example:
        >>> generator = APIDocGenerator()
        >>> generator.generate_module_docs('transfer_engine')
        >>> generator.save_markdown('docs/api.md')
    """

    def __init__(self):
        self.docs: List[str] = []

    def generate_module_docs(
        self,
        module_path: str,
        output_path: Optional[str] = None
    ) -> str:
        """
        Generate documentation for a module.

        Parameters:
        -----------
        module_path : str
            Path to Python module
        output_path : str, optional
            Path to save markdown file

        Returns:
        --------
        str
            Generated markdown documentation
        """
        self.docs = []
        self._add_header("API Documentation", level=1)

        try:
            # Import module dynamically
            import importlib
            module = importlib.import_module(module_path)

            # Document classes
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if obj.__module__ == module_path:
                    self._document_class(obj)

            # Document functions
            for name, obj in inspect.getmembers(module, inspect.isfunction):
                if obj.__module__ == module_path:
                    self._document_function(obj)

        except Exception as e:
            logger.error(f"Failed to generate docs for {module_path}: {e}")

        markdown = '\n'.join(self.docs)

        if output_path:
            Path(output_path).write_text(markdown)
            logger.info(f"Documentation saved to {output_path}")

        return markdown

    def _document_class(self, cls):
        """Document a class."""
        self._add_header(f"Class: {cls.__name__}", level=2)

        # Class docstring
        if cls.__doc__:
            self.docs.append(inspect.cleandoc(cls.__doc__))
            self.docs.append('')

        # Constructor
        if hasattr(cls, '__init__'):
            self._document_method(cls.__init__, name='__init__')

        # Public methods
        for name, method in inspect.getmembers(cls, inspect.isfunction):
            if not name.startswith('_') or name.startswith('__'):
                if name != '__init__':
                    self._document_method(method, name=name)

    def _document_function(self, func, name: Optional[str] = None):
        """Document a function."""
        func_name = name or func.__name__
        self._add_header(f"Function: {func_name}", level=3)

        # Signature
        try:
            sig = inspect.signature(func)
            self.docs.append(f"```python\n{func_name}{sig}\n```\n")
        except:
            pass

        # Docstring
        if func.__doc__:
            self.docs.append(inspect.cleandoc(func.__doc__))
            self.docs.append('')

    def _document_method(self, method, name: str):
        """Document a class method."""
        self._add_header(f"Method: {name}", level=3)

        # Signature
        try:
            sig = inspect.signature(method)
            self.docs.append(f"```python\n{name}{sig}\n```\n")
        except:
            pass

        # Docstring
        if method.__doc__:
            self.docs.append(inspect.cleandoc(method.__doc__))
            self.docs.append('')

    def _add_header(self, text: str, level: int = 1):
        """Add markdown header."""
        self.docs.append(f"{'#' * level} {text}\n")

    def generate_rest_api_docs(self, app_module: str = 'interface_layer.api') -> str:
        """Generate REST API endpoint documentation."""
        self.docs = []
        self._add_header("REST API Documentation", level=1)

        try:
            from ..interface_layer import api

            # Document endpoints
            self._add_header("Endpoints", level=2)

            # Get FastAPI app
            app = api.app

            for route in app.routes:
                if hasattr(route, 'methods') and hasattr(route, 'path'):
                    self._add_header(f"{list(route.methods)[0]} {route.path}", level=3)

                    # Endpoint function
                    if hasattr(route, 'endpoint'):
                        endpoint = route.endpoint
                        if endpoint.__doc__:
                            self.docs.append(inspect.cleandoc(endpoint.__doc__))
                            self.docs.append('')

        except Exception as e:
            logger.error(f"Failed to generate REST API docs: {e}")

        return '\n'.join(self.docs)

    def generate_cli_docs(self) -> str:
        """Generate CLI command documentation."""
        self.docs = []
        self._add_header("CLI Documentation", level=1)

        try:
            from ..interface_layer import cli

            # Get typer app
            app = cli.app

            self._add_header("Commands", level=2)

            for command in app.registered_commands:
                if hasattr(command, 'callback'):
                    func = command.callback
                    self._add_header(f"Command: {command.name or func.__name__}", level=3)

                    if func.__doc__:
                        self.docs.append(inspect.cleandoc(func.__doc__))
                        self.docs.append('')

                    # Parameters
                    self.docs.append("**Parameters:**\n")
                    try:
                        sig = inspect.signature(func)
                        for param_name, param in sig.parameters.items():
                            self.docs.append(f"- `{param_name}`: {param.annotation}")
                    except:
                        pass

                    self.docs.append('')

        except Exception as e:
            logger.error(f"Failed to generate CLI docs: {e}")

        return '\n'.join(self.docs)
