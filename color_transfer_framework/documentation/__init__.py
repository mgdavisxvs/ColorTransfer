"""
Documentation Module
====================

Automatic documentation generation for the Color Transfer Framework.

Features:
- API documentation generation
- Architecture diagram creation
- User guide generation
- Code documentation extraction
- README generation
"""

from .api_doc_generator import APIDocGenerator
from .architecture_diagram import ArchitectureDiagram
from .user_guide_generator import UserGuideGenerator
from .readme_generator import ReadmeGenerator

__all__ = [
    'APIDocGenerator',
    'ArchitectureDiagram',
    'UserGuideGenerator',
    'ReadmeGenerator'
]
