"""
Tom Sawyer Method - Parallel Processing for Color Transfer
===========================================================

The Tom Sawyer Method uses multiple "workers" to collaboratively solve
complex image processing tasks. Each worker processes the image with slight
parameter variations, then results are aggregated through weighted consensus.

Prototype Implementation:
- 10 fixed workers
- Blend factor variations (0.85 to 1.15)
- Simple weighted aggregation
- Performance metrics

Usage:
    from color_transfer_framework.tom_sawyer import TomSawyerProcessor

    processor = TomSawyerProcessor()
    result = processor.process(source, target, config)
"""

from .processor import TomSawyerProcessor
from .worker_manager import WorkerManager
from .variation import VariationController
from .aggregator import ConsensusAggregator
from .metrics import TomSawyerMetrics

__all__ = [
    'TomSawyerProcessor',
    'WorkerManager',
    'VariationController',
    'ConsensusAggregator',
    'TomSawyerMetrics',
]

__version__ = '0.1.0'  # Prototype version
