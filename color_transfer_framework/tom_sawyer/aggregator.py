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

    Knuth-Graham Enhancement:
    - Weighted average aggregation
    - MAD-based outlier rejection (more robust than z-score)
    - No quality-based weight adjustment (will be added in full version)

    Note: MAD (Median Absolute Deviation) is preferred over z-score because
    it doesn't assume Gaussian distribution and is more robust to outliers.
    """

    def __init__(
        self,
        outlier_threshold: float = 3.0,
        enable_outlier_rejection: bool = True,
        use_mad: bool = True
    ):
        """
        Initialize consensus aggregator.

        Args:
            outlier_threshold: Threshold for outlier rejection (default: 3.0)
                - For z-score: standard deviations from mean
                - For MAD: MAD units from median (more robust)
            enable_outlier_rejection: Enable outlier detection (default: True)
            use_mad: Use MAD-based detection instead of z-score (default: True)
                Recommended by Knuth-Graham analysis for robustness
        """
        self.outlier_threshold = outlier_threshold
        self.enable_outlier_rejection = enable_outlier_rejection
        self.use_mad = use_mad
        logger.info(
            f"ConsensusAggregator initialized "
            f"(outlier_rejection={enable_outlier_rejection}, "
            f"threshold={outlier_threshold}, method={'MAD' if use_mad else 'z-score'})"
        )

    def aggregate(
        self, results: List[np.ndarray], weights: np.ndarray
    ) -> tuple[np.ndarray, dict]:
        """
        Aggregate worker results using weighted consensus.

        Algorithm:
        1. Optional: Detect and remove outliers using MAD or z-score
        2. Compute weighted average
        3. Return consensus result with metadata

        Complexity:
            Time: O(n × H × W × C) where n=num_workers
            Space: O(n × H × W × C) for stacking results

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
        Detect outlier workers using MAD or z-score method.

        MAD Method (Recommended - Knuth-Graham Analysis):
        1. Compute mean absolute difference for each worker vs median
        2. Calculate MAD (Median Absolute Deviation) of deviations
        3. Mark workers with deviation > threshold × MAD as outliers
        More robust to non-Gaussian distributions

        Z-Score Method (Legacy):
        1. Compute mean absolute difference for each worker vs median
        2. Calculate z-scores
        3. Mark workers with |z| > threshold as outliers
        Assumes Gaussian distribution

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

        if self.use_mad:
            # MAD-based detection (Knuth-Graham recommendation)
            outlier_mask = self._detect_outliers_mad(deviations)
        else:
            # Z-score detection (legacy)
            outlier_mask = self._detect_outliers_zscore(deviations)

        return outlier_mask

    def _detect_outliers_mad(self, deviations: np.ndarray) -> np.ndarray:
        """
        Detect outliers using Median Absolute Deviation (MAD).

        More robust than z-score for non-Gaussian distributions.
        Recommended by Knuth-Graham analysis.

        Formula:
            MAD = median(|deviations - median(deviations)|)
            outlier if |deviation - median| > threshold × MAD

        Args:
            deviations: Array of deviation values

        Returns:
            Boolean mask (True = outlier)
        """
        median = np.median(deviations)
        mad = np.median(np.abs(deviations - median))

        if mad < 1e-6:
            # All deviations are very similar, no outliers
            return np.zeros(len(deviations), dtype=bool)

        # Modified z-score using MAD
        # Scale factor 1.4826 makes MAD consistent with std for normal distribution
        modified_z_scores = 0.6745 * (deviations - median) / mad
        outlier_mask = np.abs(modified_z_scores) > self.outlier_threshold

        return outlier_mask

    def _detect_outliers_zscore(self, deviations: np.ndarray) -> np.ndarray:
        """
        Detect outliers using z-score method (legacy).

        Less robust than MAD for non-Gaussian distributions.

        Args:
            deviations: Array of deviation values

        Returns:
            Boolean mask (True = outlier)
        """
        if deviations.std() > 1e-6:  # Avoid division by zero
            z_scores = np.abs(stats.zscore(deviations))
            outlier_mask = z_scores > self.outlier_threshold
        else:
            # All results are very similar, no outliers
            outlier_mask = np.zeros(len(deviations), dtype=bool)

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
