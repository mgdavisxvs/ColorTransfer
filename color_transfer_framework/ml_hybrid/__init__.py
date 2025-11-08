"""
ML Hybrid Module
================

Machine Learning and Deep Learning based color transfer algorithms.

Features:
- Neural style transfer
- GAN-based color transfer
- Deep learning backend support (PyTorch)
- Pre-trained model management
- Hybrid classical + ML approaches
"""

from .neural_style_transfer import NeuralStyleTransfer
from .model_manager import ModelManager
from .deep_transfer import DeepColorTransfer

__all__ = [
    'NeuralStyleTransfer',
    'ModelManager',
    'DeepColorTransfer'
]
