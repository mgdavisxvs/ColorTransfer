"""
Color Transfer Framework
========================

A modular, enterprise-grade framework for color transfer between images,
combining rigorous algorithmic analysis with practical performance optimization.

Architecture:
------------
This framework follows SOLID principles with clear separation of concerns:

1. ColorSpaceManager: Color space conversions and channel operations
2. ColorStatisticsEngine: Statistical computations and distributions
3. TransferEngine: Core color transfer algorithms
4. OptimizerEngine: Performance optimization and profiling
5. DiagnosticsVisualizer: Visualization and diagnostics
6. ComplexityAnalyzer: Emergent behavior and convergence analysis
7. MLHybridModule: Machine learning integration
8. InterfaceLayer: CLI, GUI, and API interfaces
9. PersistenceLogger: Data persistence and logging
10. DocumentationModule: Auto-documentation generation

Author: AI Research Agent
Date: 2025-11-07
Version: 2.0.0
"""

__version__ = "2.0.0"
__author__ = "AI Research Agent"

# Import main classes for convenient access
from .color_space_manager import ColorSpaceManager
from .color_statistics_engine import ColorStatisticsEngine
from .transfer_engine import TransferEngine
from .optimizer_engine import OptimizerEngine
from .diagnostics_visualizer import DiagnosticsVisualizer
from .complexity_analyzer import ComplexityAnalyzer

# Optional imports (may not be available in all environments)
try:
    from .ml_hybrid_module import MLHybridModule
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

from .interface_layer import InterfaceLayer
from .persistence_logger import PersistenceLogger
from .documentation_module import DocumentationModule

__all__ = [
    'ColorSpaceManager',
    'ColorStatisticsEngine',
    'TransferEngine',
    'OptimizerEngine',
    'DiagnosticsVisualizer',
    'ComplexityAnalyzer',
    'MLHybridModule',
    'InterfaceLayer',
    'PersistenceLogger',
    'DocumentationModule',
    'ML_AVAILABLE',
]
