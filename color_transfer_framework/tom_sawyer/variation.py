"""
Variation Controller - Tom Sawyer Method
=========================================

Generates parameter variations for each worker to create diverse
processing perspectives.

Prototype version: Blend factor variations (0.85 to 1.15).
"""

import logging
from typing import List
from ..transfer_engine import TransferConfig

logger = logging.getLogger(__name__)


class VariationController:
    """
    Controls parameter variations for Tom Sawyer workers.

    Prototype Implementation:
    - Blend factor variations only
    - Linear distribution from 0.85 to 1.15
    - Fixed variation range (will be adaptive in full version)
    """

    def __init__(self, variation_range: tuple = (0.85, 1.15)):
        """
        Initialize variation controller.

        Args:
            variation_range: (min, max) variation factors (default: 0.85 to 1.15)
        """
        self.variation_min = variation_range[0]
        self.variation_max = variation_range[1]
        logger.info(f"VariationController initialized with range {variation_range}")

    def generate_variations(
        self, base_config: TransferConfig, num_workers: int
    ) -> List[TransferConfig]:
        """
        Generate configuration variations for each worker.

        Variation strategy:
        - Worker 0: blend_factor × 0.85 (conservative)
        - Worker 4-5: blend_factor × 1.00 (standard)
        - Worker 9: blend_factor × 1.15 (aggressive)

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

            # Create varied configuration
            varied_config = self._apply_variation(base_config, variation_factor)
            variations.append(varied_config)

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
        self, base_config: TransferConfig, variation_factor: float
    ) -> TransferConfig:
        """
        Apply variation factor to base configuration.

        Prototype: Only varies blend_factor
        Full version will vary: blend, epsilon, preservation, etc.

        Args:
            base_config: Base configuration
            variation_factor: Variation multiplier

        Returns:
            Varied configuration
        """
        # Calculate varied blend factor and clamp to valid range [0.0, 1.0]
        # (TransferConfig validates this range in __post_init__)
        varied_blend = base_config.blend_factor * variation_factor
        varied_blend = max(0.0, min(1.0, varied_blend))

        # Create copy of base config with clamped blend_factor
        varied_config = TransferConfig(
            algorithm=base_config.algorithm,
            blend_factor=varied_blend,
            clip_output=base_config.clip_output,
            preserve_luminance=base_config.preserve_luminance,
            epsilon=base_config.epsilon,
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
