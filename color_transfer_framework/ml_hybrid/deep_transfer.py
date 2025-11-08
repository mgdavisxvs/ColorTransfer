"""
Deep Color Transfer
===================

High-level interface for deep learning-based color transfer.

Provides simplified API that automatically selects best available method.
"""

import cv2
import numpy as np
from typing import Optional
import logging

from .neural_style_transfer import NeuralStyleTransfer, TORCH_AVAILABLE
from .model_manager import ModelManager

logger = logging.getLogger(__name__)


class DeepColorTransfer:
    """
    High-level deep learning color transfer.

    Automatically uses best available method based on installed libraries.

    Example:
        >>> deep_transfer = DeepColorTransfer()
        >>> result = deep_transfer.transfer(source, target, method='neural')
    """

    def __init__(self, use_gpu: bool = False):
        """
        Initialize deep color transfer.

        Parameters:
        -----------
        use_gpu : bool
            Enable GPU acceleration if available
        """
        self.use_gpu = use_gpu
        self.model_manager = ModelManager()

        # Initialize neural style transfer if available
        if TORCH_AVAILABLE:
            self.neural_transfer = NeuralStyleTransfer(use_gpu=use_gpu)
            logger.info("Deep learning mode: Neural (PyTorch)")
        else:
            self.neural_transfer = None
            logger.warning("PyTorch not available, using classical fallback")

    def transfer(
        self,
        source: np.ndarray,
        target: np.ndarray,
        method: str = 'auto',
        **kwargs
    ) -> np.ndarray:
        """
        Apply deep color transfer.

        Parameters:
        -----------
        source : np.ndarray
            Source image (color donor)
        target : np.ndarray
            Target image
        method : str
            Method to use: 'auto', 'neural', 'fast', 'classical'
        **kwargs
            Additional method-specific parameters

        Returns:
        --------
        np.ndarray
            Transformed image
        """
        if method == 'auto':
            method = 'neural' if TORCH_AVAILABLE else 'classical'

        if method == 'neural':
            if self.neural_transfer is None:
                logger.warning("Neural transfer not available, using classical")
                return self._classical_transfer(source, target)

            return self.neural_transfer.transfer(
                source, target, **kwargs
            )

        elif method == 'fast':
            if self.neural_transfer is None:
                logger.warning("Fast neural transfer not available, using classical")
                return self._classical_transfer(source, target)

            return self.neural_transfer.fast_color_transfer(source, target)

        elif method == 'classical':
            return self._classical_transfer(source, target)

        else:
            raise ValueError(f"Unknown method: {method}")

    def _classical_transfer(
        self,
        source: np.ndarray,
        target: np.ndarray
    ) -> np.ndarray:
        """Classical color transfer fallback."""
        from ..transfer_engine import TransferEngine, TransferConfig, TransferAlgorithm

        engine = TransferEngine()
        config = TransferConfig(algorithm=TransferAlgorithm.REINHARD_LAB)

        return engine.transfer(source, target, config)

    def is_available(self, method: str) -> bool:
        """Check if a method is available."""
        if method in ['neural', 'fast']:
            return TORCH_AVAILABLE and self.neural_transfer is not None
        elif method == 'classical':
            return True
        else:
            return False

    def get_info(self) -> dict:
        """Get information about available methods."""
        return {
            'pytorch_available': TORCH_AVAILABLE,
            'gpu_available': TORCH_AVAILABLE and self.use_gpu,
            'methods': {
                'neural': self.is_available('neural'),
                'fast': self.is_available('fast'),
                'classical': True
            }
        }
