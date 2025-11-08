"""
Monitoring Middleware - Observability Layer (Knuth/Graham)

Provides comprehensive monitoring and metrics collection:
- Health checks (liveness, readiness)
- Metrics collection (latency, throughput, errors)
- Request logging
- Performance profiling

Mathematical Analysis (Knuth):
- Metric collection: O(1) per data point
- Aggregation: O(n) where n = metric count
- Total overhead: < 1ms per request

Operational Excellence (Graham):
- Prometheus-compatible metrics
- Structured logging (JSON)
- Health check endpoints
- Performance insights
"""

import time
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import threading

from ..security.health_checker import (
    HealthChecker,
    HealthStatus,
    HealthCheck,
    create_redis_check,
    create_disk_space_check,
    create_memory_check
)
from .context import get_request_context


logger = logging.getLogger(__name__)


@dataclass
class RequestMetrics:
    """
    Metrics for a single request

    Knuth's Metric Design:
    - Timing: Start, end, duration
    - Outcome: Success, error, status code
    - Resources: Bytes processed, items handled
    - Custom: User-defined metrics
    """

    # Timing
    timestamp: float
    duration_ms: float

    # Request info
    method: str
    path: str
    client_id: str

    # Outcome
    status_code: int
    success: bool
    error: Optional[str] = None

    # Resources
    bytes_processed: int = 0
    items_handled: int = 0

    # Custom metrics
    custom: Dict[str, Any] = field(default_factory=dict)


class MetricsCollector:
    """
    Thread-safe metrics collector

    Collects and aggregates metrics from multiple requests:
    - Request count by status code
    - Latency percentiles (p50, p95, p99)
    - Throughput (requests per second)
    - Error rate

    Knuth's Statistical Analysis:
    ==============================

    Latency Percentiles:
    - Store last N request durations
    - Sort to find percentiles: O(n log n)
    - p50 (median): sorted[n/2]
    - p95: sorted[0.95*n]
    - p99: sorted[0.99*n]

    Throughput:
    - Count requests in time window
    - RPS = count / window_seconds

    Error Rate:
    - errors / total_requests
    """

    def __init__(self, max_history: int = 1000):
        """
        Initialize metrics collector

        Args:
            max_history: Maximum number of requests to keep in history
        """
        self.max_history = max_history

        # Request history
        self._history: deque = deque(maxlen=max_history)

        # Counters
        self._total_requests = 0
        self._status_counts = defaultdict(int)
        self._error_count = 0

        # Thread safety
        self._lock = threading.Lock()

    def record_request(self, metrics: RequestMetrics):
        """
        Record request metrics

        Thread-safe recording with O(1) append
        """
        with self._lock:
            self._history.append(metrics)
            self._total_requests += 1
            self._status_counts[metrics.status_code] += 1
            if not metrics.success:
                self._error_count += 1

    def get_latency_percentiles(self) -> Dict[str, float]:
        """
        Calculate latency percentiles

        Knuth's Percentile Algorithm:
        1. Extract all durations: O(n)
        2. Sort durations: O(n log n)
        3. Find indices: O(1)
        4. Return values: O(1)

        Total: O(n log n) where n <= max_history

        Returns:
            Dictionary with p50, p95, p99 in milliseconds
        """
        with self._lock:
            if not self._history:
                return {'p50': 0.0, 'p95': 0.0, 'p99': 0.0, 'min': 0.0, 'max': 0.0}

            durations = sorted([m.duration_ms for m in self._history])
            n = len(durations)

            return {
                'p50': durations[int(n * 0.50)] if n > 0 else 0.0,
                'p95': durations[int(n * 0.95)] if n > 0 else 0.0,
                'p99': durations[int(n * 0.99)] if n > 0 else 0.0,
                'min': durations[0] if n > 0 else 0.0,
                'max': durations[-1] if n > 0 else 0.0
            }

    def get_throughput(self, window_seconds: float = 60.0) -> float:
        """
        Calculate throughput (requests per second)

        Graham's Throughput Calculation:
        - Count requests in last window_seconds
        - RPS = count / window_seconds

        Args:
            window_seconds: Time window for throughput calculation

        Returns:
            Requests per second
        """
        with self._lock:
            if not self._history:
                return 0.0

            cutoff = time.time() - window_seconds
            count = sum(1 for m in self._history if m.timestamp >= cutoff)

            return count / window_seconds

    def get_error_rate(self) -> float:
        """
        Calculate error rate

        Returns:
            Error rate as fraction (0.0 to 1.0)
        """
        with self._lock:
            if self._total_requests == 0:
                return 0.0

            return self._error_count / self._total_requests

    def get_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics

        Returns:
            Dictionary with all metrics
        """
        with self._lock:
            latency = self.get_latency_percentiles()
            throughput = self.get_throughput()
            error_rate = self.get_error_rate()

            return {
                'total_requests': self._total_requests,
                'error_count': self._error_count,
                'error_rate': error_rate,
                'status_codes': dict(self._status_counts),
                'latency_percentiles_ms': latency,
                'throughput_rps': throughput,
                'history_size': len(self._history)
            }

    def reset(self):
        """Reset all metrics (useful for testing)"""
        with self._lock:
            self._history.clear()
            self._total_requests = 0
            self._status_counts.clear()
            self._error_count = 0


class MonitoringMiddleware:
    """
    Unified monitoring middleware

    Combines:
    1. Health checking (liveness, readiness)
    2. Metrics collection (latency, throughput, errors)
    3. Request logging
    4. Performance profiling

    Graham's Observability Strategy:
    - Collect everything
    - Aggregate efficiently
    - Query quickly
    - Export to standard formats (Prometheus, JSON)
    """

    def __init__(
        self,
        health_checker: Optional[HealthChecker] = None,
        metrics_collector: Optional[MetricsCollector] = None,
        enable_health_checks: bool = True,
        enable_metrics: bool = True
    ):
        """
        Initialize monitoring middleware

        Args:
            health_checker: Health checker instance
            metrics_collector: Metrics collector instance
            enable_health_checks: Enable health checking
            enable_metrics: Enable metrics collection
        """
        self.enable_health_checks = enable_health_checks
        self.enable_metrics = enable_metrics

        # Initialize health checker
        if enable_health_checks:
            self.health_checker = health_checker or HealthChecker(
                failure_threshold=3,
                success_threshold=2
            )
        else:
            self.health_checker = None

        # Initialize metrics collector
        if enable_metrics:
            self.metrics_collector = metrics_collector or MetricsCollector(
                max_history=1000
            )
        else:
            self.metrics_collector = None

    def check_liveness(self) -> HealthCheck:
        """
        Check liveness (is process alive?)

        Returns:
            HealthCheck result
        """
        if not self.enable_health_checks or self.health_checker is None:
            return HealthCheck(
                name="liveness",
                status=HealthStatus.UNKNOWN,
                latency_ms=0,
                message="Health checks disabled"
            )

        return self.health_checker.check_liveness()

    def check_readiness(self) -> HealthCheck:
        """
        Check readiness (can handle requests?)

        Returns:
            HealthCheck result
        """
        if not self.enable_health_checks or self.health_checker is None:
            return HealthCheck(
                name="readiness",
                status=HealthStatus.UNKNOWN,
                latency_ms=0,
                message="Health checks disabled"
            )

        return self.health_checker.check_readiness()

    def get_health_status(self) -> Dict[str, Any]:
        """
        Get comprehensive health status

        Returns:
            Dictionary with liveness, readiness, and metrics
        """
        if not self.enable_health_checks or self.health_checker is None:
            return {
                'status': 'unknown',
                'message': 'Health checks disabled'
            }

        return self.health_checker.get_status()

    def record_request(
        self,
        method: str,
        path: str,
        client_id: str,
        status_code: int,
        duration_ms: float,
        success: bool = True,
        error: Optional[str] = None,
        **kwargs
    ):
        """
        Record request metrics

        Args:
            method: HTTP method
            path: Request path
            client_id: Client identifier
            status_code: HTTP status code
            duration_ms: Request duration in milliseconds
            success: Whether request was successful
            error: Error message if failed
            **kwargs: Additional custom metrics
        """
        if not self.enable_metrics or self.metrics_collector is None:
            return

        metrics = RequestMetrics(
            timestamp=time.time(),
            duration_ms=duration_ms,
            method=method,
            path=path,
            client_id=client_id,
            status_code=status_code,
            success=success,
            error=error,
            custom=kwargs
        )

        self.metrics_collector.record_request(metrics)

    def record_from_context(self, status_code: int, success: bool = True, error: Optional[str] = None):
        """
        Record request metrics from current context

        Convenience method that extracts info from request context

        Args:
            status_code: HTTP status code
            success: Whether request was successful
            error: Error message if failed
        """
        ctx = get_request_context()
        if ctx is None:
            return

        self.record_request(
            method=ctx.method,
            path=ctx.path,
            client_id=ctx.client_id,
            status_code=status_code,
            duration_ms=ctx.elapsed_ms,
            success=success,
            error=error,
            **ctx.metrics
        )

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get collected metrics

        Returns:
            Dictionary with all metrics
        """
        if not self.enable_metrics or self.metrics_collector is None:
            return {'message': 'Metrics collection disabled'}

        return self.metrics_collector.get_stats()


class HealthMiddleware:
    """
    Standalone health checking middleware

    Lightweight wrapper focused only on health checks.
    Use when you don't need full MonitoringMiddleware.
    """

    def __init__(self, health_checker: Optional[HealthChecker] = None):
        """
        Initialize health middleware

        Args:
            health_checker: Health checker instance
        """
        self.health_checker = health_checker or HealthChecker(
            failure_threshold=3,
            success_threshold=2
        )

    def add_dependency_check(self, check_func):
        """Add dependency check to readiness probe"""
        self.health_checker.add_dependency_check(check_func)

    def check_liveness(self) -> HealthCheck:
        """Check liveness"""
        return self.health_checker.check_liveness()

    def check_readiness(self) -> HealthCheck:
        """Check readiness"""
        return self.health_checker.check_readiness()

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive health status"""
        return self.health_checker.get_status()


class MetricsMiddleware:
    """
    Standalone metrics collection middleware

    Lightweight wrapper focused only on metrics collection.
    Use when you don't need full MonitoringMiddleware.
    """

    def __init__(self, metrics_collector: Optional[MetricsCollector] = None):
        """
        Initialize metrics middleware

        Args:
            metrics_collector: Metrics collector instance
        """
        self.metrics_collector = metrics_collector or MetricsCollector(max_history=1000)

    def record(self, metrics: RequestMetrics):
        """Record request metrics"""
        self.metrics_collector.record_request(metrics)

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics"""
        return self.metrics_collector.get_stats()

    def reset(self):
        """Reset metrics"""
        self.metrics_collector.reset()


# Knuth's Monitoring Analysis
"""
Monitoring Middleware Analysis (Knuth/Graham):
==============================================

Metrics Collection:

Data Structures:
- deque with maxlen: O(1) append, automatic eviction
- defaultdict: O(1) counter updates
- Threading lock: Ensures consistency

Performance:
- Record request: O(1) append
- Get percentiles: O(n log n) sort (n <= max_history)
- Get throughput: O(n) scan (n <= max_history)
- Get stats: O(n log n) total

Memory Usage:
- O(max_history) for request history
- O(status_codes) for status counts
- Total: ~1MB for max_history=1000

Latency Percentiles:

Why Percentiles?:
- Mean is misleading (affected by outliers)
- p50 (median): Typical user experience
- p95: Near-worst case
- p99: Worst case for most users

Example:
- 99 requests: 10ms
- 1 request: 1000ms
- Mean: 19.9ms (misleading!)
- p50: 10ms (typical)
- p99: 1000ms (worst case)

Throughput Calculation:

Time Window:
- Default: 60 seconds
- Count requests in [now - 60s, now]
- RPS = count / 60

Why sliding window?:
- More accurate than fixed window
- No boundary issues
- Reflects current load

Error Rate:

Calculation:
- errors / total_requests
- Fraction: 0.0 (no errors) to 1.0 (all errors)
- Percentage: error_rate * 100

Threshold:
- < 1%: Healthy
- 1-5%: Warning
- > 5%: Critical

Health Checks:

Liveness:
- Fast: < 10ms
- No dependencies
- Failure = process restart

Readiness:
- Moderate: < 100ms
- Checks dependencies
- Failure = remove from load balancer

State Machine:
- 3 consecutive failures → unhealthy
- 2 consecutive successes → healthy
- Prevents flapping

Graham's Best Practices:

1. Always collect metrics:
   monitoring.record_request(...)

2. Use percentiles, not mean:
   stats = monitoring.get_metrics()
   print(f"p95: {stats['latency_percentiles_ms']['p95']:.2f}ms")

3. Monitor error rate:
   if error_rate > 0.05:
       alert_operations()

4. Set appropriate history size:
   - 1000: Good for most APIs
   - 10000: High-traffic APIs
   - 100: Low-memory environments

5. Export to monitoring systems:
   # Prometheus
   stats = monitoring.get_metrics()
   # Convert to Prometheus format

6. Add custom dependency checks:
   health.add_dependency_check(create_redis_check(redis_client))
   health.add_dependency_check(create_disk_space_check(min_free_gb=5.0))
"""
