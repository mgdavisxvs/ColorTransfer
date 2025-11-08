"""
Performance Analyzer
====================

Comprehensive performance analysis and scaling predictions.

Mathematical Foundation (Knuth):
- Amdahl's Law: Speedup = 1 / ((1-P) + P/N)
- Universal Scalability Law (Gunther): C(N) = N / (1 + α(N-1) + βN(N-1))
- Little's Law: L = λW
- Queue theory: M/M/c model analysis

Practical Implementation (Graham):
- Empirical performance profiling
- Bottleneck identification
- Scaling recommendations
- Cost-performance optimization
"""

import logging
from typing import Dict, Any, List, Tuple, Optional
import time
import numpy as np
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class PerformanceProfile:
    """
    Performance profiling results.

    Metrics following Knuth's analysis framework:
    - Latency: Response time
    - Throughput: Requests per second
    - Utilization: Resource usage percentage
    - Scalability: Performance vs load curve
    """
    operation: str
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    throughput_rps: float
    cpu_utilization: float
    memory_utilization_mb: float
    timestamp: datetime


class PerformanceAnalyzer:
    """
    Analyze and predict system performance and scalability.

    Theoretical Framework (Knuth):
    ------------------------------
    1. Amdahl's Law:
       Speedup(N) = 1 / ((1-P) + P/N)
       Where P = parallel fraction, N = processors

    2. Universal Scalability Law (Gunther):
       C(N) = N / (1 + α(N-1) + βN(N-1))
       Where α = contention, β = coherency

    3. Queue Theory:
       W = L/λ (Little's Law)
       ρ = λ/(μ*c) (Utilization)

    Example:
        >>> analyzer = PerformanceAnalyzer()
        >>> profile = analyzer.profile_operation(transfer_func, iterations=100)
        >>> prediction = analyzer.predict_scalability(current_workers=4, target_workers=16)
    """

    def __init__(self):
        """Initialize performance analyzer."""
        self.profiles: List[PerformanceProfile] = []
        self.measurements: Dict[str, List[float]] = {}

    def profile_operation(
        self,
        operation_func: callable,
        iterations: int = 100,
        operation_name: str = "operation"
    ) -> PerformanceProfile:
        """
        Profile operation performance.

        Parameters:
        -----------
        operation_func : callable
            Function to profile
        iterations : int
            Number of iterations
        operation_name : str
            Operation name

        Returns:
        --------
        PerformanceProfile
            Performance profile
        """
        latencies = []

        logger.info(f"Profiling {operation_name}: {iterations} iterations")

        for i in range(iterations):
            start = time.perf_counter()
            try:
                operation_func()
            except Exception as e:
                logger.error(f"Operation failed: {e}")
                continue

            latency_ms = (time.perf_counter() - start) * 1000
            latencies.append(latency_ms)

        if not latencies:
            raise RuntimeError("No successful iterations")

        # Calculate percentiles
        latencies_arr = np.array(latencies)
        profile = PerformanceProfile(
            operation=operation_name,
            avg_latency_ms=float(np.mean(latencies_arr)),
            p50_latency_ms=float(np.percentile(latencies_arr, 50)),
            p95_latency_ms=float(np.percentile(latencies_arr, 95)),
            p99_latency_ms=float(np.percentile(latencies_arr, 99)),
            throughput_rps=1000.0 / np.mean(latencies_arr),  # requests/sec
            cpu_utilization=0.0,  # Would need psutil
            memory_utilization_mb=0.0,  # Would need psutil
            timestamp=datetime.now()
        )

        self.profiles.append(profile)

        logger.info(
            f"Profile complete: avg={profile.avg_latency_ms:.2f}ms, "
            f"p95={profile.p95_latency_ms:.2f}ms, "
            f"throughput={profile.throughput_rps:.2f} rps"
        )

        return profile

    def predict_amdahl_speedup(
        self,
        parallel_fraction: float,
        num_processors: int
    ) -> float:
        """
        Predict speedup using Amdahl's Law.

        Amdahl's Law (Knuth, 1967):
        ---------------------------
        Speedup(N) = 1 / ((1-P) + P/N)

        Where:
        - P: Fraction of program that can be parallelized
        - N: Number of processors
        - (1-P): Serial fraction

        Key Insight: Serial fraction limits maximum speedup
        Even with infinite processors: Speedup_max = 1/(1-P)

        Example:
        - P=0.95, N=16: Speedup = 10.3x (not 16x!)
        - P=0.99, N=100: Speedup = 50.3x (not 100x!)

        Parameters:
        -----------
        parallel_fraction : float
            Fraction that can be parallelized (0-1)
        num_processors : int
            Number of processors

        Returns:
        --------
        float
            Predicted speedup
        """
        if not 0 <= parallel_fraction <= 1:
            raise ValueError("Parallel fraction must be in [0, 1]")

        serial_fraction = 1 - parallel_fraction

        speedup = 1.0 / (serial_fraction + parallel_fraction / num_processors)

        logger.info(
            f"Amdahl's Law: P={parallel_fraction:.2f}, N={num_processors} "
            f"→ Speedup={speedup:.2f}x"
        )

        return speedup

    def predict_usl_throughput(
        self,
        baseline_throughput: float,
        num_workers: int,
        contention_coeff: float = 0.05,
        coherency_coeff: float = 0.01
    ) -> float:
        """
        Predict throughput using Universal Scalability Law.

        USL (Gunther, 2007):
        -------------------
        C(N) = N / (1 + α(N-1) + βN(N-1))

        Where:
        - N: Number of workers
        - α (alpha): Contention coefficient
        - β (beta): Coherency/crosstalk coefficient

        Behavior:
        - α causes sublinear scaling (contention for shared resources)
        - β causes retrograde scaling (coherency overhead)
        - When β > 0: throughput eventually decreases!

        Parameters:
        -----------
        baseline_throughput : float
            Throughput with 1 worker
        num_workers : int
            Target number of workers
        contention_coeff : float
            Contention coefficient α
        coherency_coeff : float
            Coherency coefficient β

        Returns:
        --------
        float
            Predicted throughput
        """
        N = num_workers
        alpha = contention_coeff
        beta = coherency_coeff

        # USL formula
        capacity_factor = N / (1 + alpha * (N - 1) + beta * N * (N - 1))

        predicted_throughput = baseline_throughput * capacity_factor

        logger.info(
            f"USL Prediction: N={N}, α={alpha}, β={beta} "
            f"→ Throughput={predicted_throughput:.2f} rps "
            f"(capacity={capacity_factor:.2f}x)"
        )

        return predicted_throughput

    def find_optimal_workers(
        self,
        baseline_throughput: float,
        contention_coeff: float = 0.05,
        coherency_coeff: float = 0.01,
        max_workers: int = 100
    ) -> Tuple[int, float]:
        """
        Find optimal number of workers.

        Optimization (Graham):
        ---------------------
        Find N* = argmax_N C(N)

        For USL: C'(N) = 0 when N* = sqrt((1-α)/β)

        Parameters:
        -----------
        baseline_throughput : float
            Single worker throughput
        contention_coeff : float
            Contention α
        coherency_coeff : float
            Coherency β
        max_workers : int
            Maximum workers to consider

        Returns:
        --------
        tuple
            (optimal_workers, max_throughput)
        """
        best_workers = 1
        best_throughput = baseline_throughput

        for N in range(1, max_workers + 1):
            throughput = self.predict_usl_throughput(
                baseline_throughput, N,
                contention_coeff, coherency_coeff
            )

            if throughput > best_throughput:
                best_throughput = throughput
                best_workers = N
            elif coherency_coeff > 0 and throughput < best_throughput * 0.95:
                # Retrograde region, stop searching
                break

        logger.info(
            f"Optimal workers: N*={best_workers} "
            f"→ Max throughput={best_throughput:.2f} rps"
        )

        return best_workers, best_throughput

    def analyze_queue_performance(
        self,
        arrival_rate: float,
        service_rate: float,
        num_servers: int
    ) -> Dict[str, float]:
        """
        Analyze queue system performance.

        M/M/c Queue Theory (Knuth):
        ---------------------------
        - M: Markovian arrivals (Poisson process)
        - M: Markovian service times (exponential)
        - c: Number of servers

        Key Metrics:
        - ρ (rho): Utilization = λ/(c*μ)
        - L: Average queue length
        - W: Average wait time
        - Lq: Queue length (excluding service)
        - Wq: Queue wait time (excluding service)

        Little's Law: L = λW

        Parameters:
        -----------
        arrival_rate : float
            Arrival rate λ (jobs/second)
        service_rate : float
            Service rate μ (jobs/second/server)
        num_servers : int
            Number of servers c

        Returns:
        --------
        dict
            Performance metrics
        """
        λ = arrival_rate
        μ = service_rate
        c = num_servers

        # Utilization
        ρ = λ / (c * μ)

        # System must be stable
        if ρ >= 1.0:
            logger.warning(f"Unstable system: ρ={ρ:.2f} >= 1.0")
            return {
                'utilization': ρ,
                'stable': False,
                'avg_queue_length': float('inf'),
                'avg_wait_time': float('inf')
            }

        # Erlang C formula (approximation for M/M/c)
        # Simplified calculation
        C = 1.0 / (1 - ρ)  # Approximation for c >> 1

        # Average number in queue (Little's Law)
        Lq = (ρ ** 2) / (1 - ρ) * (c / (c - 1)) if c > 1 else ρ ** 2 / (1 - ρ)

        # Average wait time in queue
        Wq = Lq / λ

        # Average number in system
        L = Lq + λ / μ

        # Average time in system
        W = L / λ

        metrics = {
            'utilization': ρ,
            'stable': True,
            'avg_queue_length': L,
            'avg_wait_time_s': W,
            'avg_queue_wait_s': Wq,
            'avg_service_time_s': 1.0 / μ
        }

        logger.info(
            f"Queue Analysis: λ={λ:.2f}, μ={μ:.2f}, c={c} "
            f"→ ρ={ρ:.2%}, W={W:.2f}s"
        )

        return metrics

    def estimate_cost_performance(
        self,
        num_workers: int,
        cost_per_worker_hour: float,
        throughput_per_worker: float,
        target_throughput: float
    ) -> Dict[str, float]:
        """
        Estimate cost-performance tradeoff.

        Graham's Cost Optimization:
        --------------------------
        Minimize: Cost subject to: Throughput >= Target

        Find minimum N such that:
        T(N) >= Target

        Parameters:
        -----------
        num_workers : int
            Current number of workers
        cost_per_worker_hour : float
            Cost per worker per hour
        throughput_per_worker : float
            Throughput per worker (requests/hour)
        target_throughput : float
            Target throughput (requests/hour)

        Returns:
        --------
        dict
            Cost analysis
        """
        # Calculate required workers
        required_workers = int(np.ceil(target_throughput / throughput_per_worker))

        # Cost
        current_cost = num_workers * cost_per_worker_hour
        required_cost = required_workers * cost_per_worker_hour

        # Efficiency
        current_throughput = num_workers * throughput_per_worker
        efficiency = current_throughput / current_cost  # requests per dollar

        return {
            'current_workers': num_workers,
            'required_workers': required_workers,
            'current_cost_per_hour': current_cost,
            'required_cost_per_hour': required_cost,
            'current_throughput': current_throughput,
            'target_throughput': target_throughput,
            'efficiency_requests_per_dollar': efficiency,
            'overprovisioned': num_workers > required_workers
        }

    def recommend_scaling(
        self,
        current_metrics: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Recommend scaling based on current metrics.

        Decision Algorithm (Knuth):
        ---------------------------
        1. If utilization > 0.8: Scale up
        2. If utilization < 0.3: Scale down
        3. If queue length > threshold: Scale up
        4. If costs > budget: Optimize

        Parameters:
        -----------
        current_metrics : dict
            Current system metrics

        Returns:
        --------
        dict
            Scaling recommendations
        """
        utilization = current_metrics.get('utilization', 0.5)
        queue_length = current_metrics.get('avg_queue_length', 0)
        workers = current_metrics.get('num_workers', 1)

        recommendations = []

        # Utilization-based
        if utilization > 0.85:
            target_workers = int(np.ceil(workers * utilization / 0.75))
            recommendations.append({
                'action': 'scale_up',
                'reason': f'High utilization ({utilization:.1%})',
                'target_workers': target_workers
            })

        elif utilization < 0.30:
            target_workers = max(1, int(workers * utilization / 0.70))
            recommendations.append({
                'action': 'scale_down',
                'reason': f'Low utilization ({utilization:.1%})',
                'target_workers': target_workers
            })

        # Queue-based
        if queue_length > 10:
            recommendations.append({
                'action': 'scale_up',
                'reason': f'Large queue ({queue_length:.1f} jobs)',
                'urgency': 'high'
            })

        if not recommendations:
            recommendations.append({
                'action': 'maintain',
                'reason': 'Performance within acceptable range'
            })

        return {
            'current_workers': workers,
            'current_utilization': utilization,
            'recommendations': recommendations
        }
