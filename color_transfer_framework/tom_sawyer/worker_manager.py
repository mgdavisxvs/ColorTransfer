"""
Worker Manager - Tom Sawyer Method
===================================

Manages worker allocation and configuration for parallel processing.

Prototype version: Fixed 10 workers with predefined weights.
"""

import logging
from typing import List
import numpy as np

logger = logging.getLogger(__name__)


class WorkerManager:
    """
    Manages worker allocation for Tom Sawyer parallel processing.

    Prototype Implementation:
    - Fixed 10 workers
    - Static weight distribution (center-heavy)
    - No adaptive allocation (will be added in full version)
    """

    def __init__(self, num_workers: int = 10):
        """
        Initialize worker manager.

        Args:
            num_workers: Number of workers (default: 10)
        """
        self.num_workers = num_workers
        self.weights = self._initialize_weights()
        logger.info(f"WorkerManager initialized with {num_workers} workers")

    def _initialize_weights(self) -> np.ndarray:
        """
        Initialize worker weights with center-heavy distribution.

        Weight distribution pattern:
        - Center workers (40%): weight = 2.0
        - Middle workers (40%): weight = 1.5
        - Edge workers (20%): weight = 1.0

        Returns:
            Array of worker weights
        """
        weights = np.ones(self.num_workers)

        # Center workers (indices 4-6 for 10 workers)
        center_start = self.num_workers // 2 - 1
        center_end = self.num_workers // 2 + 1
        weights[center_start:center_end] = 2.0

        # Middle workers (indices 2-3, 7-8 for 10 workers)
        middle_range = self.num_workers // 5
        weights[middle_range:center_start] = 1.5
        weights[center_end:self.num_workers - middle_range] = 1.5

        # Normalize so sum equals num_workers
        weights = weights * (self.num_workers / weights.sum())

        logger.debug(f"Initialized weights: {weights}")
        return weights

    def get_weights(self) -> np.ndarray:
        """
        Get current worker weights.

        Returns:
            Array of worker weights
        """
        return self.weights.copy()

    def get_num_workers(self) -> int:
        """
        Get number of workers.

        Returns:
            Number of workers
        """
        return self.num_workers

    def update_weights(self, new_weights: np.ndarray):
        """
        Update worker weights (for future learning implementation).

        Args:
            new_weights: New weight values
        """
        if len(new_weights) != self.num_workers:
            raise ValueError(f"Expected {self.num_workers} weights, got {len(new_weights)}")

        # Normalize
        self.weights = new_weights * (self.num_workers / new_weights.sum())
        logger.info(f"Weights updated: {self.weights}")
