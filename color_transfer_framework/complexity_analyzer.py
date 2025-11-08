"""
ComplexityAnalyzer Module
=========================

Analyzes emergent behavior and convergence of color transfer systems.

Responsibilities:
- Iterate color transfer to study convergence
- Compute entropy evolution
- Detect fixed points and cycles
- Analyze system stability (Lyapunov)
- Track distribution similarity over iterations
- Emergent behavior analysis

Design Principles:
- Observer Pattern: Track system evolution
- Strategy Pattern: Different convergence tests
- Iterator Pattern: Step through iterations
"""

import numpy as np
import cv2
from typing import Optional, List, Dict, Tuple, Callable
from enum import Enum
from dataclasses import dataclass, field

from .color_space_manager import ColorSpaceManager, ColorSpace
from .color_statistics_engine import ColorStatisticsEngine, ColorStatistics
from .transfer_engine import TransferEngine, TransferConfig


class ConvergenceTest(Enum):
    """Convergence test criteria."""
    MEAN_THRESHOLD = "mean_threshold"
    STD_THRESHOLD = "std_threshold"
    KL_DIVERGENCE = "kl_divergence"
    DELTA_E = "delta_e"
    COMBINED = "combined"


@dataclass
class IterationData:
    """
    Data from a single iteration.

    Attributes:
    ----------
    iteration : int
        Iteration number
    image : np.ndarray
        Image at this iteration
    statistics : ColorStatistics
        Color statistics
    entropy : float
        Total entropy
    mean_change : float
        Change in mean from previous iteration
    std_change : float
        Change in std from previous iteration
    kl_divergence : Optional[float]
        KL divergence from target distribution
    converged : bool
        Whether system has converged
    """
    iteration: int
    image: np.ndarray
    statistics: ColorStatistics
    entropy: float
    mean_change: float = 0.0
    std_change: float = 0.0
    kl_divergence: Optional[float] = None
    converged: bool = False
    metadata: Dict = field(default_factory=dict)


@dataclass
class ConvergenceReport:
    """
    Report on system convergence.

    Attributes:
    ----------
    converged : bool
        Whether system converged
    iterations_to_convergence : int
        Number of iterations to convergence
    final_mean_error : float
        Final mean error
    final_std_ratio : float
        Final std deviation ratio
    convergence_rate : str
        Convergence classification
    is_stable : bool
        Whether fixed point is stable
    has_cycles : bool
        Whether system has periodic cycles
    """
    converged: bool
    iterations_to_convergence: int
    final_mean_error: float
    final_std_ratio: float
    convergence_rate: str
    is_stable: bool
    has_cycles: bool
    cycle_length: Optional[int] = None
    metadata: Dict = field(default_factory=dict)

    def summary(self) -> str:
        """Generate human-readable summary."""
        lines = []
        lines.append("Convergence Analysis Report")
        lines.append("=" * 50)
        lines.append(f"Converged: {'Yes' if self.converged else 'No'}")
        if self.converged:
            lines.append(f"Iterations: {self.iterations_to_convergence}")
            lines.append(f"Convergence Rate: {self.convergence_rate}")
        lines.append(f"Final Mean Error: {self.final_mean_error:.6f}")
        lines.append(f"Final Std Ratio: {self.final_std_ratio:.6f}")
        lines.append(f"Stable: {'Yes' if self.is_stable else 'No'}")
        if self.has_cycles:
            lines.append(f"Cycles Detected: Period {self.cycle_length}")
        return "\n".join(lines)


class ComplexityAnalyzer:
    """
    Analyzer for emergent behavior and convergence.

    This class studies the behavior of color transfer when applied iteratively,
    analyzing convergence properties, entropy evolution, and emergent patterns.

    Example:
    -------
    >>> analyzer = ComplexityAnalyzer()
    >>> data = analyzer.iterate_transfer(source, target, n_iterations=10)
    >>> report = analyzer.analyze_convergence(data)
    >>> print(report.summary())
    """

    def __init__(self):
        """Initialize ComplexityAnalyzer."""
        self.color_manager = ColorSpaceManager()
        self.stats_engine = ColorStatisticsEngine()
        self.transfer_engine = TransferEngine()

    # ============================================================================
    # Iteration and Data Collection
    # ============================================================================

    def iterate_transfer(self,
                        source: np.ndarray,
                        target: np.ndarray,
                        n_iterations: int = 10,
                        config: Optional[TransferConfig] = None,
                        collect_images: bool = True) -> List[IterationData]:
        """
        Iterate color transfer and collect data.

        Parameters:
        ----------
        source : np.ndarray
            Source image (BGR uint8)
        target : np.ndarray
            Initial target image (BGR uint8)
        n_iterations : int
            Number of iterations
        config : Optional[TransferConfig]
            Transfer configuration
        collect_images : bool
            Whether to store full images (memory intensive)

        Returns:
        -------
        List[IterationData]
            Data from each iteration

        Mathematical Note:
        ----------------
        For the Reinhard algorithm, convergence occurs in 1 iteration
        (mean and variance exactly preserved). This method is useful for
        studying iterative/cyclic transfers or non-Reinhard algorithms.
        """
        data_series = []
        current = target.copy()

        # Convert source to Lab for statistics
        source_lab = self.color_manager.convert_to(
            self.color_manager.to_float(source), ColorSpace.LAB
        )
        source_stats = self.stats_engine.compute_stats(source_lab, compute_all=True)

        for i in range(n_iterations):
            # Apply transfer
            current = self.transfer_engine.transfer(source, current, config)

            # Convert to Lab for analysis
            current_lab = self.color_manager.convert_to(
                self.color_manager.to_float(current), ColorSpace.LAB
            )

            # Compute statistics
            current_stats = self.stats_engine.compute_stats(current_lab, compute_all=True)

            # Compute entropy
            entropy = np.sum(current_stats.entropy) if current_stats.entropy is not None else 0.0

            # Compute changes from previous iteration
            if i > 0:
                prev_stats = data_series[-1].statistics
                mean_change = np.linalg.norm(current_stats.mean - prev_stats.mean)
                std_change = np.linalg.norm(current_stats.std - prev_stats.std)
            else:
                mean_change = 0.0
                std_change = 0.0

            # Compute KL divergence from source
            comparison = self.stats_engine.compare_stats(source_stats, current_stats)
            kl_div = comparison.get('kl_divergence')

            # Create iteration data
            iter_data = IterationData(
                iteration=i,
                image=current.copy() if collect_images else None,
                statistics=current_stats,
                entropy=entropy,
                mean_change=mean_change,
                std_change=std_change,
                kl_divergence=kl_div,
                metadata={
                    'source_comparison': comparison
                }
            )

            data_series.append(iter_data)

        return data_series

    # ============================================================================
    # Convergence Analysis
    # ============================================================================

    def analyze_convergence(self,
                           data_series: List[IterationData],
                           threshold: float = 1e-6,
                           test: ConvergenceTest = ConvergenceTest.COMBINED) -> ConvergenceReport:
        """
        Analyze convergence from iteration data.

        Parameters:
        ----------
        data_series : List[IterationData]
            Iteration data
        threshold : float
            Convergence threshold
        test : ConvergenceTest
            Convergence test method

        Returns:
        -------
        ConvergenceReport
            Convergence analysis report
        """
        if not data_series:
            raise ValueError("Empty data series")

        # Detect convergence point
        converged = False
        convergence_iteration = len(data_series)

        for i, data in enumerate(data_series):
            if i == 0:
                continue

            # Apply convergence test
            if test == ConvergenceTest.MEAN_THRESHOLD:
                is_converged = data.mean_change < threshold
            elif test == ConvergenceTest.STD_THRESHOLD:
                is_converged = data.std_change < threshold
            elif test == ConvergenceTest.COMBINED:
                is_converged = (data.mean_change < threshold and
                              data.std_change < threshold)
            else:
                is_converged = data.mean_change < threshold

            if is_converged and not converged:
                converged = True
                convergence_iteration = i
                break

        # Final statistics
        final_data = data_series[-1]
        final_comparison = final_data.metadata.get('source_comparison', {})

        # Determine convergence rate
        if convergence_iteration == 1:
            conv_rate = "Immediate (single-step)"
        elif convergence_iteration <= 3:
            conv_rate = "Superlinear"
        elif convergence_iteration <= 10:
            conv_rate = "Linear"
        else:
            conv_rate = "Sublinear"

        # Detect cycles
        has_cycles, cycle_length = self._detect_cycles(data_series)

        # Stability analysis
        is_stable = self._analyze_stability(data_series)

        report = ConvergenceReport(
            converged=converged,
            iterations_to_convergence=convergence_iteration,
            final_mean_error=final_comparison.get('mean_error', 0.0),
            final_std_ratio=final_comparison.get('std_ratio', 1.0),
            convergence_rate=conv_rate,
            is_stable=is_stable,
            has_cycles=has_cycles,
            cycle_length=cycle_length,
            metadata={
                'total_iterations': len(data_series),
                'final_entropy': final_data.entropy,
                'final_kl_divergence': final_data.kl_divergence
            }
        )

        return report

    def _detect_cycles(self,
                      data_series: List[IterationData],
                      min_period: int = 2,
                      max_period: int = 10) -> Tuple[bool, Optional[int]]:
        """
        Detect periodic cycles in iteration data.

        Parameters:
        ----------
        data_series : List[IterationData]
            Iteration data
        min_period : int
            Minimum cycle period
        max_period : int
            Maximum cycle period to check

        Returns:
        -------
        Tuple[bool, Optional[int]]
            (has_cycles, cycle_length)
        """
        if len(data_series) < 2 * min_period:
            return False, None

        # Extract mean vectors
        means = np.array([d.statistics.mean for d in data_series])

        # Check for periodicity
        for period in range(min_period, min(max_period + 1, len(means) // 2)):
            # Compare points separated by period
            is_periodic = True
            for i in range(len(means) - period):
                diff = np.linalg.norm(means[i] - means[i + period])
                if diff > 1e-4:  # Threshold for "same" point
                    is_periodic = False
                    break

            if is_periodic:
                return True, period

        return False, None

    def _analyze_stability(self, data_series: List[IterationData]) -> bool:
        """
        Analyze stability of fixed point (Lyapunov analysis).

        Parameters:
        ----------
        data_series : List[IterationData]
            Iteration data

        Returns:
        -------
        bool
            True if stable (mean changes decrease over time)
        """
        if len(data_series) < 3:
            return True  # Not enough data

        # Check if changes are decreasing (stable)
        changes = [d.mean_change for d in data_series[1:]]

        # Stable if changes generally decrease
        decreasing_count = sum(changes[i] > changes[i+1]
                             for i in range(len(changes) - 1))

        return decreasing_count >= len(changes) // 2

    # ============================================================================
    # Entropy Evolution
    # ============================================================================

    def compute_entropy_series(self, data_series: List[IterationData]) -> np.ndarray:
        """
        Extract entropy evolution from iteration data.

        Parameters:
        ----------
        data_series : List[IterationData]
            Iteration data

        Returns:
        -------
        np.ndarray
            Entropy at each iteration
        """
        return np.array([d.entropy for d in data_series])

    def analyze_entropy_evolution(self,
                                  data_series: List[IterationData]) -> Dict[str, float]:
        """
        Analyze entropy evolution over iterations.

        Parameters:
        ----------
        data_series : List[IterationData]
            Iteration data

        Returns:
        -------
        Dict[str, float]
            Entropy analysis metrics
        """
        entropies = self.compute_entropy_series(data_series)

        return {
            'initial_entropy': entropies[0],
            'final_entropy': entropies[-1],
            'mean_entropy': np.mean(entropies),
            'std_entropy': np.std(entropies),
            'entropy_change': entropies[-1] - entropies[0],
            'max_entropy': np.max(entropies),
            'min_entropy': np.min(entropies),
        }

    # ============================================================================
    # Multi-Image Cycles
    # ============================================================================

    def analyze_n_way_cycle(self,
                           images: List[np.ndarray],
                           n_iterations: int = 10) -> Dict[str, any]:
        """
        Analyze n-way cyclic color transfer.

        Example: A → B → C → A (3-way cycle)

        Parameters:
        ----------
        images : List[np.ndarray]
            Images in cycle
        n_iterations : int
            Number of cycle iterations

        Returns:
        -------
        Dict[str, any]
            Analysis results
        """
        n_images = len(images)
        if n_images < 2:
            raise ValueError("Need at least 2 images for cycle")

        # Track evolution of each image
        current_images = [img.copy() for img in images]
        statistics_history = [[] for _ in range(n_images)]

        for iteration in range(n_iterations):
            # Apply cyclic transfer
            # Image 0 takes color from image n-1
            # Image i takes color from image i-1
            new_images = []
            for i in range(n_images):
                source_idx = (i - 1) % n_images
                target = current_images[i]
                source = current_images[source_idx]

                transferred = self.transfer_engine.transfer(source, target)
                new_images.append(transferred)

                # Collect statistics
                lab = self.color_manager.convert_to(
                    self.color_manager.to_float(transferred), ColorSpace.LAB
                )
                stats = self.stats_engine.compute_stats(lab)
                statistics_history[i].append(stats)

            current_images = new_images

        # Analyze convergence to common distribution
        final_stats = [history[-1] for history in statistics_history]

        # Compute pairwise differences in final states
        mean_diffs = []
        for i in range(n_images):
            for j in range(i + 1, n_images):
                diff = np.linalg.norm(final_stats[i].mean - final_stats[j].mean)
                mean_diffs.append(diff)

        avg_mean_diff = np.mean(mean_diffs)

        # Compute centroid (average of all means)
        all_means = np.array([stats.mean for stats in final_stats])
        centroid = np.mean(all_means, axis=0)

        return {
            'n_images': n_images,
            'n_iterations': n_iterations,
            'converged_to_common': avg_mean_diff < 1e-3,
            'average_pairwise_difference': avg_mean_diff,
            'centroid_mean': centroid,
            'final_statistics': final_stats,
            'statistics_history': statistics_history
        }

    # ============================================================================
    # Dynamical System Analysis
    # ============================================================================

    def compute_trajectory(self,
                          source: np.ndarray,
                          target: np.ndarray,
                          n_iterations: int = 20,
                          space: str = 'mean') -> np.ndarray:
        """
        Compute trajectory in state space.

        Parameters:
        ----------
        source : np.ndarray
            Source image
        target : np.ndarray
            Target image
        n_iterations : int
            Number of iterations
        space : str
            State space ('mean', 'std', 'both')

        Returns:
        -------
        np.ndarray
            Trajectory array (iterations × dimensions)
        """
        data = self.iterate_transfer(source, target, n_iterations, collect_images=False)

        if space == 'mean':
            return np.array([d.statistics.mean for d in data])
        elif space == 'std':
            return np.array([d.statistics.std for d in data])
        elif space == 'both':
            means = np.array([d.statistics.mean for d in data])
            stds = np.array([d.statistics.std for d in data])
            return np.concatenate([means, stds], axis=1)
        else:
            raise ValueError(f"Unknown space: {space}")

    def estimate_lyapunov_exponent(self,
                                  source: np.ndarray,
                                  target: np.ndarray,
                                  n_iterations: int = 20,
                                  perturbation: float = 1e-6) -> float:
        """
        Estimate Lyapunov exponent (measure of chaos/stability).

        Positive exponent → chaotic (divergence)
        Negative exponent → stable (convergence)
        Zero → neutral

        Parameters:
        ----------
        source : np.ndarray
            Source image
        target : np.ndarray
            Target image
        n_iterations : int
            Number of iterations
        perturbation : float
            Initial perturbation magnitude

        Returns:
        -------
        float
            Estimated Lyapunov exponent
        """
        # Original trajectory
        traj1 = self.compute_trajectory(source, target, n_iterations, space='mean')

        # Perturbed trajectory
        target_perturbed = target.astype(np.float32)
        target_perturbed += np.random.randn(*target.shape) * perturbation
        target_perturbed = np.clip(target_perturbed, 0, 255).astype(np.uint8)

        traj2 = self.compute_trajectory(source, target_perturbed, n_iterations, space='mean')

        # Compute divergence rate
        distances = np.linalg.norm(traj1 - traj2, axis=1)

        # Filter out zeros to avoid log(0)
        nonzero_distances = distances[distances > 1e-10]

        if len(nonzero_distances) < 2:
            return -np.inf  # Perfect convergence

        # Lyapunov exponent ≈ (1/n) * log(d_n / d_0)
        lyapunov = np.log(nonzero_distances[-1] / nonzero_distances[0]) / len(nonzero_distances)

        return lyapunov


# Convenience function
def analyze_transfer_convergence(source: np.ndarray,
                                target: np.ndarray,
                                n_iterations: int = 10) -> ConvergenceReport:
    """
    Quick convergence analysis.

    Parameters:
    ----------
    source, target : np.ndarray
        Images to analyze
    n_iterations : int
        Number of iterations

    Returns:
    -------
    ConvergenceReport
        Convergence report

    Example:
    -------
    >>> report = analyze_transfer_convergence(source, target)
    >>> print(report.summary())
    """
    analyzer = ComplexityAnalyzer()
    data = analyzer.iterate_transfer(source, target, n_iterations, collect_images=False)
    return analyzer.analyze_convergence(data)
