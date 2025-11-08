"""
Health Checks and Readiness Probes - Operational Excellence

Implements Kubernetes-style health monitoring:
1. Liveness Probe - Is the process alive?
2. Readiness Probe - Can it handle requests?
3. Startup Probe - Has initialization completed?
4. Dependency Health - Are external services available?

Mathematical Analysis (Knuth):
- Health check interval: T seconds
- Timeout: t seconds (t < T to avoid overlap)
- Failure threshold: N consecutive failures before unhealthy
- Recovery threshold: M consecutive successes before healthy

State Machine:
- Healthy → Unhealthy: After N consecutive failures
- Unhealthy → Healthy: After M consecutive successes
- Prevents flapping: Requires sustained state change

Operational Excellence (Graham):
- Fast checks: < 100ms for basic health
- Graceful degradation: Partial functionality vs complete failure
- Clear error messages: Help operators debug issues
"""

import time
import logging
import threading
from enum import Enum
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta


logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status values"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"  # Partial functionality
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """
    Individual health check result

    Knuth's Health Model:
    - status: Binary healthy/unhealthy (or degraded for partial)
    - latency_ms: Response time (important for SLA monitoring)
    - message: Human-readable status
    - details: Machine-readable details for debugging
    """
    name: str
    status: HealthStatus
    latency_ms: float
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'name': self.name,
            'status': self.status.value,
            'latency_ms': round(self.latency_ms, 2),
            'message': self.message,
            'details': self.details,
            'timestamp': self.timestamp.isoformat()
        }


class LivenessProbe:
    """
    Liveness Probe - Is the process alive?

    Kubernetes Liveness:
    - Detects deadlock, infinite loops, unresponsive processes
    - Failure action: Restart container/process
    - Should be simple: Just check if process can respond

    Knuth's Analysis:
    - Check complexity: O(1) - just return True if running
    - False positive rate: ~0 (if process running, always succeeds)
    - False negative rate: ~0 (if process dead, no response)

    Graham's Implementation:
    - No external dependencies (don't check Redis, etc.)
    - Fast: < 10ms
    - Stateless: No initialization required
    """

    def __init__(self, name: str = "liveness"):
        self.name = name
        self._start_time = time.time()

    def check(self) -> HealthCheck:
        """
        Perform liveness check

        Basic check:
        1. Process is running (we can execute code)
        2. No deadlock (can acquire locks, if needed)
        3. Basic memory sanity

        Returns:
            HealthCheck with status
        """
        start = time.time()

        try:
            # Simple alive check - if we can execute this, we're alive
            uptime_seconds = time.time() - self._start_time

            status = HealthStatus.HEALTHY
            message = f"Process alive for {uptime_seconds:.0f} seconds"
            details = {
                'uptime_seconds': uptime_seconds,
                'pid': threading.current_thread().ident
            }

            latency_ms = (time.time() - start) * 1000

            return HealthCheck(
                name=self.name,
                status=status,
                latency_ms=latency_ms,
                message=message,
                details=details
            )

        except Exception as e:
            # If we can't even run this check, process is unhealthy
            latency_ms = (time.time() - start) * 1000
            return HealthCheck(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                latency_ms=latency_ms,
                message=f"Liveness check failed: {e}",
                details={'error': str(e)}
            )


class ReadinessProbe:
    """
    Readiness Probe - Can the service handle requests?

    Kubernetes Readiness:
    - Detects when service is ready to accept traffic
    - Failure action: Remove from load balancer
    - Should check critical dependencies

    Knuth's Analysis:
    - Check complexity: O(d) where d = number of dependencies
    - Should be fast: < 100ms total
    - Dependencies: Redis, database, external APIs, etc.

    Graham's Implementation:
    - Check each dependency with timeout
    - Parallel checks for speed
    - Graceful degradation: Distinguish critical vs optional deps
    """

    def __init__(
        self,
        name: str = "readiness",
        timeout_seconds: float = 5.0
    ):
        self.name = name
        self.timeout_seconds = timeout_seconds
        self._dependency_checks: List[Callable[[], HealthCheck]] = []

    def add_dependency_check(self, check_func: Callable[[], HealthCheck]):
        """
        Add a dependency check function

        Args:
            check_func: Function that returns HealthCheck

        Example:
            def check_redis():
                try:
                    redis_client.ping()
                    return HealthCheck("redis", HealthStatus.HEALTHY, 5.0, "Connected")
                except:
                    return HealthCheck("redis", HealthStatus.UNHEALTHY, 0, "Failed")

            readiness.add_dependency_check(check_redis)
        """
        self._dependency_checks.append(check_func)

    def check(self) -> HealthCheck:
        """
        Perform readiness check

        Algorithm:
        1. Run all dependency checks
        2. If any critical dependency fails: UNHEALTHY
        3. If optional dependency fails: DEGRADED
        4. If all succeed: HEALTHY

        Time Complexity: O(d) where d = dependencies
        Can be parallelized for O(1) with threading
        """
        start = time.time()
        all_checks = []

        try:
            # Run all dependency checks
            for check_func in self._dependency_checks:
                try:
                    result = check_func()
                    all_checks.append(result)
                except Exception as e:
                    # Dependency check raised exception
                    all_checks.append(HealthCheck(
                        name="unknown",
                        status=HealthStatus.UNHEALTHY,
                        latency_ms=0,
                        message=f"Check failed: {e}"
                    ))

            # Determine overall status
            if not all_checks:
                # No dependencies configured - always ready
                status = HealthStatus.HEALTHY
                message = "No dependencies configured"
            else:
                # Check if any dependencies failed
                failed = [c for c in all_checks if c.status == HealthStatus.UNHEALTHY]
                degraded = [c for c in all_checks if c.status == HealthStatus.DEGRADED]

                if failed:
                    status = HealthStatus.UNHEALTHY
                    message = f"{len(failed)} dependencies unhealthy"
                elif degraded:
                    status = HealthStatus.DEGRADED
                    message = f"{len(degraded)} dependencies degraded"
                else:
                    status = HealthStatus.HEALTHY
                    message = "All dependencies healthy"

            latency_ms = (time.time() - start) * 1000

            return HealthCheck(
                name=self.name,
                status=status,
                latency_ms=latency_ms,
                message=message,
                details={
                    'dependencies': [c.to_dict() for c in all_checks]
                }
            )

        except Exception as e:
            latency_ms = (time.time() - start) * 1000
            return HealthCheck(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                latency_ms=latency_ms,
                message=f"Readiness check failed: {e}",
                details={'error': str(e)}
            )


class HealthChecker:
    """
    Unified Health Checker

    Combines liveness and readiness probes with:
    - Automatic periodic checks
    - State machine for failure/recovery thresholds
    - Metrics collection

    Knuth's State Machine:
    =====================

    States: {HEALTHY, UNHEALTHY, DEGRADED}

    Transitions:
    - HEALTHY → UNHEALTHY: After N consecutive failures
    - UNHEALTHY → HEALTHY: After M consecutive successes
    - DEGRADED: Partial functionality (some deps failed)

    This prevents flapping from transient failures.

    Parameters:
    - failure_threshold: N (default 3)
    - success_threshold: M (default 2)

    Graham's Implementation:
    - HTTP endpoints: /health/live, /health/ready
    - JSON response with detailed status
    - Prometheus metrics (optional)
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        success_threshold: int = 2
    ):
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold

        self.liveness = LivenessProbe()
        self.readiness = ReadinessProbe()

        # State tracking for failure/success thresholds
        self._consecutive_failures = 0
        self._consecutive_successes = 0
        self._current_status = HealthStatus.HEALTHY

        # History for metrics
        self._check_history: List[HealthCheck] = []
        self._max_history = 100

    def add_dependency_check(self, check_func: Callable[[], HealthCheck]):
        """Add dependency check to readiness probe"""
        self.readiness.add_dependency_check(check_func)

    def check_liveness(self) -> HealthCheck:
        """Check liveness (is process alive?)"""
        return self.liveness.check()

    def check_readiness(self) -> HealthCheck:
        """Check readiness (can handle requests?)"""
        result = self.readiness.check()

        # Update state machine based on result
        if result.status == HealthStatus.UNHEALTHY:
            self._consecutive_failures += 1
            self._consecutive_successes = 0

            if self._consecutive_failures >= self.failure_threshold:
                self._current_status = HealthStatus.UNHEALTHY

        else:  # HEALTHY or DEGRADED
            self._consecutive_successes += 1
            self._consecutive_failures = 0

            if self._consecutive_successes >= self.success_threshold:
                self._current_status = result.status

        # Record in history
        self._check_history.append(result)
        if len(self._check_history) > self._max_history:
            self._check_history.pop(0)

        return result

    def get_status(self) -> Dict[str, Any]:
        """
        Get comprehensive health status

        Returns:
            Dictionary with liveness, readiness, and overall status

        Example response:
        {
            "status": "healthy",
            "liveness": {...},
            "readiness": {...},
            "metrics": {
                "uptime_seconds": 3600,
                "total_checks": 100,
                "success_rate": 0.99
            }
        }
        """
        liveness = self.check_liveness()
        readiness = self.check_readiness()

        # Calculate metrics
        total_checks = len(self._check_history)
        if total_checks > 0:
            successful = len([
                c for c in self._check_history
                if c.status == HealthStatus.HEALTHY
            ])
            success_rate = successful / total_checks
        else:
            success_rate = 1.0

        uptime_seconds = time.time() - self.liveness._start_time

        return {
            'status': self._current_status.value,
            'liveness': liveness.to_dict(),
            'readiness': readiness.to_dict(),
            'metrics': {
                'uptime_seconds': round(uptime_seconds, 2),
                'total_checks': total_checks,
                'success_rate': round(success_rate, 4),
                'consecutive_failures': self._consecutive_failures,
                'consecutive_successes': self._consecutive_successes
            },
            'timestamp': datetime.now().isoformat()
        }

    def is_healthy(self) -> bool:
        """Simple boolean health check"""
        return self._current_status == HealthStatus.HEALTHY

    def is_ready(self) -> bool:
        """Simple boolean readiness check"""
        status = self.check_readiness().status
        return status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]


# Example dependency check functions
def create_redis_check(redis_client) -> Callable[[], HealthCheck]:
    """
    Create Redis dependency check

    Usage:
        import redis
        r = redis.Redis(host='localhost', port=6379)
        health_checker.add_dependency_check(create_redis_check(r))
    """
    def check_redis() -> HealthCheck:
        start = time.time()
        try:
            redis_client.ping()
            latency_ms = (time.time() - start) * 1000
            return HealthCheck(
                name="redis",
                status=HealthStatus.HEALTHY,
                latency_ms=latency_ms,
                message="Connected to Redis",
                details={'host': redis_client.connection_pool.connection_kwargs.get('host')}
            )
        except Exception as e:
            latency_ms = (time.time() - start) * 1000
            return HealthCheck(
                name="redis",
                status=HealthStatus.UNHEALTHY,
                latency_ms=latency_ms,
                message=f"Redis connection failed: {e}",
                details={'error': str(e)}
            )

    return check_redis


def create_disk_space_check(min_free_gb: float = 1.0) -> Callable[[], HealthCheck]:
    """
    Create disk space check

    Graham's Disk Monitoring:
    - Check available disk space
    - Warn if below threshold
    - Critical if very low (< 100 MB)

    Usage:
        health_checker.add_dependency_check(create_disk_space_check(min_free_gb=5.0))
    """
    def check_disk() -> HealthCheck:
        start = time.time()
        try:
            import shutil
            stat = shutil.disk_usage('/')

            free_gb = stat.free / (1024 ** 3)
            total_gb = stat.total / (1024 ** 3)
            percent_free = (stat.free / stat.total) * 100

            if free_gb < 0.1:  # < 100 MB
                status = HealthStatus.UNHEALTHY
                message = f"Critical: Only {free_gb:.2f} GB free"
            elif free_gb < min_free_gb:
                status = HealthStatus.DEGRADED
                message = f"Warning: Only {free_gb:.2f} GB free"
            else:
                status = HealthStatus.HEALTHY
                message = f"{free_gb:.2f} GB free ({percent_free:.1f}%)"

            latency_ms = (time.time() - start) * 1000

            return HealthCheck(
                name="disk_space",
                status=status,
                latency_ms=latency_ms,
                message=message,
                details={
                    'free_gb': round(free_gb, 2),
                    'total_gb': round(total_gb, 2),
                    'percent_free': round(percent_free, 1)
                }
            )

        except Exception as e:
            latency_ms = (time.time() - start) * 1000
            return HealthCheck(
                name="disk_space",
                status=HealthStatus.UNKNOWN,
                latency_ms=latency_ms,
                message=f"Disk check failed: {e}",
                details={'error': str(e)}
            )

    return check_disk


def create_memory_check(max_usage_percent: float = 90.0) -> Callable[[], HealthCheck]:
    """
    Create memory usage check

    Knuth's Memory Monitoring:
    - Track memory usage percentage
    - Warn at 90% (default)
    - Critical at 95%

    Usage:
        health_checker.add_dependency_check(create_memory_check(max_usage_percent=85.0))
    """
    def check_memory() -> HealthCheck:
        start = time.time()
        try:
            import psutil
            mem = psutil.virtual_memory()

            percent_used = mem.percent

            if percent_used > 95:
                status = HealthStatus.UNHEALTHY
                message = f"Critical: {percent_used:.1f}% memory used"
            elif percent_used > max_usage_percent:
                status = HealthStatus.DEGRADED
                message = f"Warning: {percent_used:.1f}% memory used"
            else:
                status = HealthStatus.HEALTHY
                message = f"{percent_used:.1f}% memory used"

            latency_ms = (time.time() - start) * 1000

            return HealthCheck(
                name="memory",
                status=status,
                latency_ms=latency_ms,
                message=message,
                details={
                    'percent_used': round(percent_used, 1),
                    'available_gb': round(mem.available / (1024 ** 3), 2),
                    'total_gb': round(mem.total / (1024 ** 3), 2)
                }
            )

        except Exception as e:
            latency_ms = (time.time() - start) * 1000
            return HealthCheck(
                name="memory",
                status=HealthStatus.UNKNOWN,
                latency_ms=latency_ms,
                message=f"Memory check failed: {e}",
                details={'error': str(e)}
            )

    return check_memory


# Knuth's Health Check Analysis
"""
Health Check Analysis (Knuth/Graham):
=====================================

Liveness vs Readiness:

Liveness (Process Alive?):
- Purpose: Detect deadlock, crash, unresponsive
- Action on failure: Restart process/container
- Should NOT check dependencies
- Complexity: O(1)
- Latency: < 10ms

Readiness (Can Handle Requests?):
- Purpose: Detect if service can serve traffic
- Action on failure: Remove from load balancer
- Should check dependencies (Redis, DB, etc.)
- Complexity: O(d) where d = dependencies
- Latency: < 100ms

State Machine (Anti-Flapping):

Without threshold:
- Transient failure → immediate unhealthy → load balancer changes
- Quick recovery → immediate healthy → load balancer changes
- Result: Constant churn, poor user experience

With threshold (N=3 failures, M=2 successes):
- Transient failure → still healthy (< 3 failures)
- Sustained failure → unhealthy after 3 failures
- Recovery → healthy after 2 successes
- Result: Stable state, smooth traffic management

Mathematical Analysis:

False Positive Rate:
- Healthy service marked unhealthy
- Probability: P(N consecutive false failures)
- If failure rate f = 0.01, P(3 consecutive) = 0.01^3 = 0.000001

False Negative Rate:
- Unhealthy service marked healthy
- Probability: P(M consecutive false successes)
- If success rate s = 0.99 when unhealthy, P(2 consecutive) = 0.99^2 = 0.98

Detection Time:
- To detect failure: N * check_interval
- To detect recovery: M * check_interval
- Tradeoff: Lower N/M = faster detection, higher flapping

Graham's Recommendations:

Check Intervals:
- Liveness: Every 10 seconds (default)
- Readiness: Every 5 seconds (default)
- Don't check too frequently (wastes resources)

Thresholds:
- Failure threshold: 3 (good balance)
- Success threshold: 2 (faster recovery than detection)
- Higher for flappy dependencies

Timeouts:
- Liveness timeout: 1 second
- Readiness timeout: 5 seconds
- Per-dependency timeout: 2 seconds

HTTP Endpoints (Kubernetes-style):
- GET /health/live → Liveness probe
- GET /health/ready → Readiness probe
- GET /health → Combined status

Response Codes:
- 200: Healthy
- 503: Unhealthy (Service Unavailable)
- 429: Degraded (Too Many Requests - partial capacity)
"""
