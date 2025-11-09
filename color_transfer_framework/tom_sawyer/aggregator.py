"""
Consensus Aggregator - Tom Sawyer Method
=========================================

Aggregates results from multiple workers using weighted consensus.

Prototype version: Simple weighted average with optional outlier rejection.
"""

import logging
from typing import List
import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)


class ConsensusAggregator:
    """
    Aggregates worker results through weighted consensus.

    Prototype Implementation:
    - Weighted average aggregation
    - Optional z-score outlier rejection
    - No quality-based weight adjustment (will be added in full version)
    """

    def __init__(self, outlier_threshold: float = 3.0, enable_outlier_rejection: bool = True):
        """
        Initialize consensus aggregator.

        Args:
            outlier_threshold: Z-score threshold for outlier rejection (default: 3.0)
            enable_outlier_rejection: Enable outlier detection (default: True)
        """
        self.outlier_threshold = outlier_threshold
        self.enable_outlier_rejection = enable_outlier_rejection
        logger.info(
            f"ConsensusAggregator initialized "
            f"(outlier_rejection={enable_outlier_rejection}, threshold={outlier_threshold})"
        )

    def aggregate(
        self, results: List[np.ndarray], weights: np.ndarray
    ) -> tuple[np.ndarray, dict]:
        """
        Aggregate worker results using weighted consensus.

        Algorithm:
        1. Optional: Detect and remove outliers using z-score
        2. Compute weighted average
        3. Return consensus result with metadata

        Args:
            results: List of worker results (each shape: H x W x C)
            weights: Worker weights (shape: num_workers)

        Returns:
            Tuple of (consensus_result, metadata)
        """
        if len(results) == 0:
            raise ValueError("No results to aggregate")

        if len(results) != len(weights):
            raise ValueError(
                f"Mismatch: {len(results)} results but {len(weights)} weights"
            )

        # Stack results for processing
        results_stack = np.stack(results, axis=0)  # Shape: (num_workers, H, W, C)
        num_workers = len(results)

        # Outlier detection and removal
        outlier_mask = None
        if self.enable_outlier_rejection and num_workers >= 5:
            outlier_mask = self._detect_outliers(results_stack)
            num_outliers = outlier_mask.sum()

            if num_outliers > 0:
                logger.info(f"Rejected {num_outliers}/{num_workers} outlier workers")
        else:
            outlier_mask = np.zeros(num_workers, dtype=bool)

        # Filter results and weights
        valid_mask = ~outlier_mask
        filtered_results = results_stack[valid_mask]
        filtered_weights = weights[valid_mask]

        # Weighted average
        consensus = self._weighted_average(filtered_results, filtered_weights)

        # Compute metadata
        metadata = {
            "num_workers": num_workers,
            "num_outliers": outlier_mask.sum(),
            "num_used": valid_mask.sum(),
            "weight_sum": filtered_weights.sum(),
            "outlier_rejection_enabled": self.enable_outlier_rejection,
        }

        logger.debug(f"Aggregation complete: {metadata}")
        return consensus, metadata

    def _detect_outliers(self, results_stack: np.ndarray) -> np.ndarray:
        """
        Detect outlier workers using z-score method.

        Method:
        1. Compute mean absolute difference for each worker vs median
        2. Calculate z-scores
        3. Mark workers with |z| > threshold as outliers

        Args:
            results_stack: Stacked results (num_workers, H, W, C)

        Returns:
            Boolean mask (True = outlier)
        """
        num_workers = results_stack.shape[0]

        # Compute pixel-wise median
        median = np.median(results_stack, axis=0)

        # Compute mean absolute deviation for each worker
        deviations = []
        for i in range(num_workers):
            mad = np.mean(np.abs(results_stack[i] - median))
            deviations.append(mad)

        deviations = np.array(deviations)

        # Compute z-scores
        if deviations.std() > 1e-6:  # Avoid division by zero
            z_scores = np.abs(stats.zscore(deviations))
            outlier_mask = z_scores > self.outlier_threshold
        else:
            # All results are very similar, no outliers
            outlier_mask = np.zeros(num_workers, dtype=bool)

        return outlier_mask

    def _weighted_average(self, results: np.ndarray, weights: np.ndarray) -> np.ndarray:
        """
        Compute weighted average of results.

        Formula: result = Σ(weight[i] × result[i]) / Σ(weight[i])

        Args:
            results: Worker results (num_workers, H, W, C)
            weights: Worker weights (num_workers,)

        Returns:
            Consensus result (H, W, C)
        """
        # Normalize weights to sum to 1.0
        normalized_weights = weights / weights.sum()

        # Reshape weights for broadcasting: (num_workers, 1, 1, 1)
        weights_reshaped = normalized_weights[:, np.newaxis, np.newaxis, np.newaxis]

        # Weighted sum
        weighted_sum = (results * weights_reshaped).sum(axis=0)

        return weighted_sum

    def compute_consensus_quality(
        self, results: List[np.ndarray], consensus: np.ndarray
    ) -> dict:
        """
        Compute quality metrics for consensus result.

        Metrics:
        - Agreement: How similar are workers to consensus
        - Variance: Spread of worker results
        - Confidence: Inverse of variance (higher = more agreement)

        Args:
            results: List of worker results
            consensus: Consensus result

        Returns:
            Dictionary of quality metrics
        """
        results_stack = np.stack(results, axis=0)

        # Mean squared error vs consensus
        mse_values = []
        for result in results:
            mse = np.mean((result - consensus) ** 2)
            mse_values.append(mse)

        mean_mse = np.mean(mse_values)
        std_mse = np.std(mse_values)

        # Variance across workers
        variance = np.var(results_stack, axis=0).mean()

        # Confidence (inverse variance, normalized)
        confidence = 1.0 / (1.0 + variance)

        return {
            "mean_mse": float(mean_mse),
            "std_mse": float(std_mse),
            "variance": float(variance),
            "confidence": float(confidence),
            "agreement_pct": float(100.0 * (1.0 - mean_mse / 255.0)),  # Assuming 0-255 range
        }
