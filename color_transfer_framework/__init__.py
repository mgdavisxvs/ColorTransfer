"""
Color Transfer Framework
========================

A modular, enterprise-grade framework for color transfer between images,
combining rigorous algorithmic analysis with practical performance optimization.

Architecture:
------------
This framework follows SOLID principles with clear separation of concerns:

1. ColorSpaceManager: Color space conversions and channel operations ✓
2. ColorStatisticsEngine: Statistical computations and distributions ✓
3. TransferEngine: Core color transfer algorithms ✓
4. OptimizerEngine: Performance optimization and profiling ✓
5. DiagnosticsVisualizer: Visualization and diagnostics ✓
6. ComplexityAnalyzer: Emergent behavior and convergence analysis ✓
7. MLHybridModule: Machine learning integration ⏳
8. InterfaceLayer: CLI, GUI, and API interfaces ⏳
9. PersistenceLogger: Data persistence and logging ⏳
10. DocumentationModule: Auto-documentation generation ⏳

Author: AI Research Agent
Date: 2025-11-07
Version: 2.0.0-alpha
"""

__version__ = "2.0.0-alpha"
__author__ = "AI Research Agent"

# Import core modules (available)
from .color_space_manager import ColorSpaceManager, ColorSpace
from .color_statistics_engine import (
    ColorStatisticsEngine,
    ColorStatistics,
    compute_image_stats
)
from .transfer_engine import (
    TransferEngine,
    TransferConfig,
    TransferAlgorithm,
    transfer_color
)
from .optimizer_engine import (
    OptimizerEngine,
    OptimizationMode,
    PerformanceMetrics,
    benchmark_transfer
)

# Import optional modules (may not be available yet)
try:
    from .diagnostics_visualizer import DiagnosticsVisualizer
    VISUALIZER_AVAILABLE = True
except ImportError:
    VISUALIZER_AVAILABLE = False

try:
    from .complexity_analyzer import ComplexityAnalyzer, analyze_transfer_convergence
    ANALYZER_AVAILABLE = True
except ImportError:
    ANALYZER_AVAILABLE = False

# try:
#     from .ml_hybrid_module import MLHybridModule
#     ML_AVAILABLE = True
# except ImportError:
#     ML_AVAILABLE = False

# try:
#     from .interface_layer import InterfaceLayer
#     INTERFACE_AVAILABLE = True
# except ImportError:
#     INTERFACE_AVAILABLE = False

# try:
#     from .persistence_logger import PersistenceLogger
#     PERSISTENCE_AVAILABLE = True
# except ImportError:
#     PERSISTENCE_AVAILABLE = False

# try:
#     from .documentation_module import DocumentationModule
#     DOCUMENTATION_AVAILABLE = True
# except ImportError:
#     DOCUMENTATION_AVAILABLE = False

__all__ = [
    # Core classes
    'ColorSpaceManager',
    'ColorSpace',
    'ColorStatisticsEngine',
    'ColorStatistics',
    'TransferEngine',
    'TransferConfig',
    'TransferAlgorithm',
    'OptimizerEngine',
    'OptimizationMode',
    'PerformanceMetrics',

    # Convenience functions
    'compute_image_stats',
    'transfer_color',
    'benchmark_transfer',

    # Optional modules
    'DiagnosticsVisualizer',
    'ComplexityAnalyzer',
    'analyze_transfer_convergence',
    # 'MLHybridModule',
    # 'InterfaceLayer',
    # 'PersistenceLogger',
    # 'DocumentationModule',
]
