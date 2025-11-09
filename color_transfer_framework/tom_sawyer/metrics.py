"""
Metrics - Tom Sawyer Method
============================

Performance tracking and comparison metrics for Tom Sawyer processing.
"""

import time
import logging
from typing import Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class TomSawyerMetrics:
    """
    Performance metrics for Tom Sawyer processing.

    Attributes:
        num_workers: Number of workers used
        processing_time_ms: Total processing time in milliseconds
        per_worker_time_ms: Average time per worker
        aggregation_time_ms: Time spent aggregating results
        num_outliers: Number of outliers rejected
        consensus_confidence: Confidence score (0-1)
        memory_used_mb: Estimated memory usage
        speedup_vs_sequential: Speedup factor (if parallel)
    """

    num_workers: int
    processing_time_ms: float
    per_worker_time_ms: float
    aggregation_time_ms: float
    num_outliers: int
    consensus_confidence: float
    memory_used_mb: float
    speedup_vs_sequential: Optional[float] = None

    def to_dict(self) -> dict:
        """Convert metrics to dictionary."""
        return asdict(self)

    def __str__(self) -> str:
        """Human-readable metrics string."""
        return (
            f"TomSawyer Metrics:\n"
            f"  Workers: {self.num_workers}\n"
            f"  Total Time: {self.processing_time_ms:.2f}ms\n"
            f"  Per Worker: {self.per_worker_time_ms:.2f}ms\n"
            f"  Aggregation: {self.aggregation_time_ms:.2f}ms\n"
            f"  Outliers: {self.num_outliers}\n"
            f"  Confidence: {self.consensus_confidence:.2%}\n"
            f"  Memory: {self.memory_used_mb:.2f}MB"
        )


class PerformanceTracker:
    """
    Tracks performance metrics during Tom Sawyer processing.
    """

    def __init__(self):
        """Initialize performance tracker."""
        self.start_time: Optional[float] = None
        self.worker_times: list = []
        self.aggregation_start: Optional[float] = None
        self.aggregation_end: Optional[float] = None

    def start(self):
        """Start tracking."""
        self.start_time = time.time()
        self.worker_times = []

    def record_worker_start(self):
        """Record worker processing start."""
        return time.time()

    def record_worker_end(self, start_time: float):
        """Record worker processing end."""
        elapsed = (time.time() - start_time) * 1000  # Convert to ms
        self.worker_times.append(elapsed)

    def start_aggregation(self):
        """Start aggregation timing."""
        self.aggregation_start = time.time()

    def end_aggregation(self):
        """End aggregation timing."""
        self.aggregation_end = time.time()

    def get_metrics(
        self,
        num_workers: int,
        num_outliers: int,
        confidence: float,
        memory_mb: float,
    ) -> TomSawyerMetrics:
        """
        Get final metrics.

        Args:
            num_workers: Number of workers used
            num_outliers: Number of outliers rejected
            confidence: Consensus confidence score
            memory_mb: Memory used in MB

        Returns:
            TomSawyerMetrics object
        """
        total_time = (time.time() - self.start_time) * 1000 if self.start_time else 0

        per_worker_time = (
            sum(self.worker_times) / len(self.worker_times) if self.worker_times else 0
        )

        aggregation_time = (
            (self.aggregation_end - self.aggregation_start) * 1000
            if self.aggregation_start and self.aggregation_end
            else 0
        )

        # Estimate speedup if we have parallel execution
        # (Sequential would be: per_worker_time * num_workers)
        speedup = None
        if per_worker_time > 0 and total_time > 0:
            sequential_time = per_worker_time * num_workers
            speedup = sequential_time / total_time

        return TomSawyerMetrics(
            num_workers=num_workers,
            processing_time_ms=total_time,
            per_worker_time_ms=per_worker_time,
            aggregation_time_ms=aggregation_time,
            num_outliers=num_outliers,
            consensus_confidence=confidence,
            memory_used_mb=memory_mb,
            speedup_vs_sequential=speedup,
        )


class ComparisonMetrics:
    """
    Metrics for comparing Tom Sawyer vs standard processing.
    """

    @staticmethod
    def compare(
        tom_sawyer_result: dict, standard_result: dict, ground_truth: Optional[any] = None
    ) -> dict:
        """
        Compare Tom Sawyer processing vs standard.

        Args:
            tom_sawyer_result: Tom Sawyer metrics
            standard_result: Standard processing metrics
            ground_truth: Optional ground truth for accuracy

        Returns:
            Comparison dictionary
        """
        time_overhead = (
            tom_sawyer_result["processing_time_ms"]
            / standard_result["processing_time_ms"]
        )

        memory_overhead = (
            tom_sawyer_result["memory_used_mb"] / standard_result["memory_used_mb"]
        )

        return {
            "time_overhead": time_overhead,
            "time_overhead_pct": (time_overhead - 1.0) * 100,
            "memory_overhead": memory_overhead,
            "memory_overhead_pct": (memory_overhead - 1.0) * 100,
            "tom_sawyer_time_ms": tom_sawyer_result["processing_time_ms"],
            "standard_time_ms": standard_result["processing_time_ms"],
            "tom_sawyer_memory_mb": tom_sawyer_result["memory_used_mb"],
            "standard_memory_mb": standard_result["memory_used_mb"],
            "consensus_confidence": tom_sawyer_result.get("consensus_confidence", 0),
        }
