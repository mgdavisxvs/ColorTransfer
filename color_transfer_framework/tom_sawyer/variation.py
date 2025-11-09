"""
Variation Controller - Tom Sawyer Method
=========================================

Generates parameter variations for each worker to create diverse
processing perspectives.

Phase 18.3: Multi-parameter variations (blend_factor, epsilon, preserve_luminance).
"""

import logging
import numpy as np
from typing import List
from ..transfer_engine import TransferConfig

logger = logging.getLogger(__name__)


class VariationController:
    """
    Controls parameter variations for Tom Sawyer workers.

    Phase 18.3 Implementation:
    - Multi-parameter variations (blend_factor, epsilon, preserve_luminance)
    - Linear distribution for blend_factor (0.7 to 1.3)
    - Log-scale distribution for epsilon (1e-11 to 1e-9)
    - Alternating boolean for preserve_luminance
    """

    def __init__(self, variation_range: tuple = (0.7, 1.3), enable_multi_param: bool = True):
        """
        Initialize variation controller.

        Args:
            variation_range: (min, max) variation factors for blend_factor
            enable_multi_param: Enable multi-parameter variation (Phase 18.3)
        """
        self.variation_min = variation_range[0]
        self.variation_max = variation_range[1]
        self.enable_multi_param = enable_multi_param
        logger.info(
            f"VariationController initialized with range {variation_range}, "
            f"multi-param={enable_multi_param}"
        )

    def generate_variations(
        self, base_config: TransferConfig, num_workers: int
    ) -> List[TransferConfig]:
        """
        Generate configuration variations for each worker.

        Phase 18.3 Multi-parameter variation strategy:
        - blend_factor: Linear from 0.7 to 1.3
        - epsilon: Log-scale from 1e-11 to 1e-9
        - preserve_luminance: Alternating (odd workers = True)

        Example (4 workers):
        - Worker 0: blend=0.70, epsilon=1e-11, preserve=False
        - Worker 1: blend=0.90, epsilon=1e-10.33, preserve=True
        - Worker 2: blend=1.10, epsilon=1e-9.67, preserve=False
        - Worker 3: blend=1.30, epsilon=1e-9, preserve=True

        Args:
            base_config: Base transfer configuration
            num_workers: Number of workers

        Returns:
            List of varied configurations (one per worker)
        """
        variations = []

        for i in range(num_workers):
            # Calculate variation factor for this worker
            variation_factor = self._calculate_variation_factor(i, num_workers)

            # Create varied configuration (with worker index for multi-param)
            varied_config = self._apply_variation(base_config, variation_factor, worker_index=i)
            variations.append(varied_config)

            if self.enable_multi_param:
                logger.debug(
                    f"Worker {i}: blend={varied_config.blend_factor:.3f}, "
                    f"epsilon={varied_config.epsilon:.2e}, "
                    f"preserve_lum={varied_config.preserve_luminance}"
                )
            else:
                logger.debug(
                    f"Worker {i}: variation={variation_factor:.3f}, "
                    f"blend={varied_config.blend_factor:.3f}"
                )

        return variations

    def _calculate_variation_factor(self, worker_index: int, num_workers: int) -> float:
        """
        Calculate variation factor for a specific worker.

        Uses linear interpolation: V(i) = min + (max - min) × i / (n - 1)

        Args:
            worker_index: Index of worker [0, num_workers-1]
            num_workers: Total number of workers

        Returns:
            Variation factor for this worker
        """
        if num_workers == 1:
            return 1.0

        # Linear interpolation from min to max
        progress = worker_index / (num_workers - 1)
        variation = self.variation_min + (self.variation_max - self.variation_min) * progress

        return variation

    def _apply_variation(
        self, base_config: TransferConfig, variation_factor: float, worker_index: int = 0
    ) -> TransferConfig:
        """
        Apply variation factor to base configuration.

        Phase 18.3: Multi-parameter variation
        - blend_factor: multiplicative variation (0.7 to 1.3)
        - epsilon: log-scale variation (1e-11 to 1e-9)
        - preserve_luminance: alternating boolean (even/odd workers)

        Args:
            base_config: Base configuration
            variation_factor: Variation multiplier for blend_factor
            worker_index: Index of worker (for multi-param variation)

        Returns:
            Varied configuration
        """
        # 1. Vary blend_factor (existing logic)
        varied_blend = base_config.blend_factor * variation_factor
        varied_blend = max(0.0, min(1.0, varied_blend))

        if self.enable_multi_param:
            # 2. Vary epsilon in log scale (1e-11 to 1e-9)
            # Map variation_factor (0.7-1.3) to log scale
            # 0.7 → 1e-11, 1.0 → 1e-10, 1.3 → 1e-9
            log_epsilon_min = -11
            log_epsilon_max = -9
            # Normalize variation_factor to [0, 1] range
            normalized = (variation_factor - self.variation_min) / (
                self.variation_max - self.variation_min
            )
            log_epsilon = log_epsilon_min + normalized * (log_epsilon_max - log_epsilon_min)
            varied_epsilon = 10 ** log_epsilon

            # 3. Vary preserve_luminance (alternating for diversity)
            varied_preserve = (worker_index % 2) == 1  # Odd workers preserve luminance
        else:
            # Single-parameter mode (backward compatibility)
            varied_epsilon = base_config.epsilon
            varied_preserve = base_config.preserve_luminance

        # Create varied configuration
        varied_config = TransferConfig(
            algorithm=base_config.algorithm,
            blend_factor=varied_blend,
            clip_output=base_config.clip_output,
            preserve_luminance=varied_preserve,
            epsilon=varied_epsilon,
        )

        return varied_config

    def get_variation_info(self, num_workers: int) -> dict:
        """
        Get information about variation distribution.

        Args:
            num_workers: Number of workers

        Returns:
            Dictionary with variation metadata
        """
        variations = [
            self._calculate_variation_factor(i, num_workers) for i in range(num_workers)
        ]

        return {
            "num_workers": num_workers,
            "variation_range": (self.variation_min, self.variation_max),
            "variations": variations,
            "mean": sum(variations) / len(variations),
            "std": (
                sum((v - sum(variations) / len(variations)) ** 2 for v in variations)
                / len(variations)
            )
            ** 0.5,
        }
