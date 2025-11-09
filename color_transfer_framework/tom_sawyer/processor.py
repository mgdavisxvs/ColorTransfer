"""
Tom Sawyer Processor - Main Interface
======================================

High-level interface for Tom Sawyer parallel processing.

Usage:
    processor = TomSawyerProcessor(num_workers=10)
    result = processor.process(source, target, config, transfer_func)
"""

import logging
from typing import Callable, List
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
import tracemalloc

from ..transfer_engine import TransferConfig
from .worker_manager import WorkerManager
from .variation import VariationController
from .aggregator import ConsensusAggregator
from .metrics import TomSawyerMetrics, PerformanceTracker

logger = logging.getLogger(__name__)


class TomSawyerProcessor:
    """
    Main processor for Tom Sawyer parallel color transfer.

    Coordinates worker management, variation generation, parallel execution,
    and consensus aggregation.
    """

    def __init__(
        self,
        num_workers: int = 10,
        variation_range: tuple = (0.7, 1.3),
        enable_outlier_rejection: bool = True,
        outlier_threshold: float = 3.0,
        max_parallel_workers: int = 4,
        enable_multi_param: bool = True,
        use_mad_outlier_detection: bool = True,
    ):
        """
        Initialize Tom Sawyer processor.

        Args:
            num_workers: Number of workers (default: 10)
            variation_range: (min, max) variation factors (default: 0.7 to 1.3)
            enable_outlier_rejection: Enable outlier detection (default: True)
            outlier_threshold: Threshold for outliers (default: 3.0)
            max_parallel_workers: Max parallel threads (default: 4)
            enable_multi_param: Enable multi-parameter variation (Phase 18.3, default: True)
            use_mad_outlier_detection: Use MAD instead of z-score (Knuth-Graham, default: True)
        """
        self.worker_manager = WorkerManager(num_workers=num_workers)
        self.variation_controller = VariationController(
            variation_range=variation_range, enable_multi_param=enable_multi_param
        )
        self.aggregator = ConsensusAggregator(
            outlier_threshold=outlier_threshold,
            enable_outlier_rejection=enable_outlier_rejection,
            use_mad=use_mad_outlier_detection,
        )
        self.max_parallel_workers = max_parallel_workers

        logger.info(
            f"TomSawyerProcessor initialized: "
            f"workers={num_workers}, "
            f"variation={variation_range}, "
            f"multi_param={enable_multi_param}, "
            f"outlier_rejection={enable_outlier_rejection} "
            f"(method={'MAD' if use_mad_outlier_detection else 'z-score'})"
        )

    def process(
        self,
        source: np.ndarray,
        target: np.ndarray,
        base_config: TransferConfig,
        transfer_func: Callable,
        enable_parallel: bool = True,
    ) -> tuple[np.ndarray, TomSawyerMetrics]:
        """
        Process color transfer using Tom Sawyer method.

        Algorithm:
        1. Generate parameter variations for each worker
        2. Execute workers in parallel (or sequentially)
        3. Aggregate results through weighted consensus
        4. Return consensus result with metrics

        Complexity (Knuth-Graham Analysis):
            Sequential: O(n × T(transfer)) where T(transfer) ≈ O(HWC log HWC)
            Parallel: O(⌈n/p⌉ × T(transfer) + n×HWC) where p=max_parallel_workers
            Space: O(n × H × W × C) for storing worker results

            Measured (Phase 18.3):
                512×512: +35% overhead (production-ready)
                1024×1024: +120% overhead (acceptable)

        Args:
            source: Source image (H, W, C)
            target: Target image (H, W, C)
            base_config: Base transfer configuration
            transfer_func: Transfer function(source, target, config) -> result
            enable_parallel: Use parallel execution (default: True)

        Returns:
            Tuple of (consensus_result, metrics)
        """
        tracker = PerformanceTracker()
        tracker.start()

        # Start memory tracking
        tracemalloc.start()
        memory_before = tracemalloc.get_traced_memory()[0] / 1024 / 1024  # MB

        # Step 1: Generate variations
        num_workers = self.worker_manager.get_num_workers()
        variations = self.variation_controller.generate_variations(
            base_config, num_workers
        )
        weights = self.worker_manager.get_weights()

        logger.info(f"Generated {len(variations)} worker configurations")

        # Step 2: Execute workers
        if enable_parallel and self.max_parallel_workers > 1:
            results = self._execute_parallel(
                source, target, variations, transfer_func, tracker
            )
        else:
            results = self._execute_sequential(
                source, target, variations, transfer_func, tracker
            )

        # Step 3: Aggregate results
        tracker.start_aggregation()
        consensus, agg_metadata = self.aggregator.aggregate(results, weights)
        tracker.end_aggregation()

        # Compute consensus quality
        quality = self.aggregator.compute_consensus_quality(results, consensus)

        # Memory tracking
        memory_after = tracemalloc.get_traced_memory()[0] / 1024 / 1024  # MB
        memory_used = memory_after - memory_before
        tracemalloc.stop()

        # Get final metrics
        metrics = tracker.get_metrics(
            num_workers=num_workers,
            num_outliers=agg_metadata["num_outliers"],
            confidence=quality["confidence"],
            memory_mb=memory_used,
        )

        logger.info(f"Tom Sawyer processing complete:\n{metrics}")
        logger.info(f"Consensus quality: {quality}")

        return consensus, metrics

    def _execute_parallel(
        self,
        source: np.ndarray,
        target: np.ndarray,
        variations: List[TransferConfig],
        transfer_func: Callable,
        tracker: PerformanceTracker,
    ) -> List[np.ndarray]:
        """
        Execute workers in parallel using ThreadPoolExecutor.

        Args:
            source: Source image
            target: Target image
            variations: List of configurations
            transfer_func: Transfer function
            tracker: Performance tracker

        Returns:
            List of worker results
        """
        results = [None] * len(variations)

        with ThreadPoolExecutor(max_workers=self.max_parallel_workers) as executor:
            # Submit all tasks
            future_to_index = {}
            for i, config in enumerate(variations):
                future = executor.submit(
                    self._execute_worker, source, target, config, transfer_func, tracker
                )
                future_to_index[future] = i

            # Collect results in order
            for future in as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    results[index] = future.result()
                except (ValueError, RuntimeError, TypeError) as e:
                    # Handle expected errors with fallback
                    logger.error(f"Worker {index} failed with expected error: {e}")
                    # Use fallback: average of source and target
                    results[index] = (source.astype(float) + target.astype(float)) / 2.0
                except Exception as e:
                    # Unexpected errors should be logged and re-raised
                    logger.critical(
                        f"Worker {index} failed with unexpected error: {e}. "
                        f"This indicates a serious bug that needs investigation."
                    )
                    raise

        logger.info(f"Parallel execution complete: {len(results)} results")
        return results

    def _execute_sequential(
        self,
        source: np.ndarray,
        target: np.ndarray,
        variations: List[TransferConfig],
        transfer_func: Callable,
        tracker: PerformanceTracker,
    ) -> List[np.ndarray]:
        """
        Execute workers sequentially.

        Args:
            source: Source image
            target: Target image
            variations: List of configurations
            transfer_func: Transfer function
            tracker: Performance tracker

        Returns:
            List of worker results
        """
        results = []

        for i, config in enumerate(variations):
            try:
                result = self._execute_worker(
                    source, target, config, transfer_func, tracker
                )
                results.append(result)
            except (ValueError, RuntimeError, TypeError) as e:
                # Handle expected errors with fallback
                logger.error(f"Worker {i} failed with expected error: {e}")
                results.append((source.astype(float) + target.astype(float)) / 2.0)
            except Exception as e:
                # Unexpected errors should be logged and re-raised
                logger.critical(
                    f"Worker {i} failed with unexpected error: {e}. "
                    f"This indicates a serious bug that needs investigation."
                )
                raise

        logger.info(f"Sequential execution complete: {len(results)} results")
        return results

    def _execute_worker(
        self,
        source: np.ndarray,
        target: np.ndarray,
        config: TransferConfig,
        transfer_func: Callable,
        tracker: PerformanceTracker,
    ) -> np.ndarray:
        """
        Execute single worker.

        Args:
            source: Source image
            target: Target image
            config: Transfer configuration
            transfer_func: Transfer function
            tracker: Performance tracker

        Returns:
            Worker result image
        """
        start_time = tracker.record_worker_start()

        # Execute transfer
        result = transfer_func(source, target, config)

        tracker.record_worker_end(start_time)

        return result

    def get_info(self) -> dict:
        """
        Get processor information.

        Returns:
            Dictionary with processor configuration
        """
        return {
            "num_workers": self.worker_manager.get_num_workers(),
            "variation_range": (
                self.variation_controller.variation_min,
                self.variation_controller.variation_max,
            ),
            "outlier_rejection": self.aggregator.enable_outlier_rejection,
            "outlier_threshold": self.aggregator.outlier_threshold,
            "max_parallel_workers": self.max_parallel_workers,
            "weights": self.worker_manager.get_weights().tolist(),
        }
