"""
Load Testing Suite - Knuth's Performance Analysis

Tests system behavior under load with mathematical rigor:
- Throughput measurement (requests/second)
- Latency analysis (p50, p95, p99)
- Concurrency testing (1-1000 users)
- Stability testing (sustained load)
- Breaking point identification

Mathematical Models (Knuth):
- Little's Law: L = λW (queue length = arrival rate × wait time)
- Amdahl's Law: Speedup = 1/((1-P) + P/N)
- Universal Scalability Law: C(N) = N/(1 + α(N-1) + βN(N-1))

Practical Load Testing (Graham):
- Realistic user behavior
- Gradual ramp-up
- Statistical analysis
- Clear reporting
"""

from locust import HttpUser, task, between, events
import random
import base64
import io
import numpy as np
import cv2
import time
from typing import Dict, List


def generate_test_image(size: tuple = (100, 100), color: tuple = (255, 0, 0)) -> bytes:
    """
    Generate test image in memory

    Knuth's Test Image:
    - Known size: Predictable load
    - Known color: Easy verification
    - Minimal size: Faster generation
    """
    img = np.zeros((size[0], size[1], 3), dtype=np.uint8)
    img[:, :] = color
    _, buffer = cv2.imencode('.png', img)
    return buffer.tobytes()


def image_to_base64(image_bytes: bytes) -> str:
    """Convert image bytes to base64 string"""
    return base64.b64encode(image_bytes).decode('utf-8')


class ColorTransferUser(HttpUser):
    """
    Simulated user for load testing

    Graham's User Model:
    - Think time: 1-5 seconds (realistic)
    - Actions: View, transfer, download
    - Distribution: Weighted by frequency
    """

    wait_time = between(1, 5)  # Think time between requests

    def on_start(self):
        """
        Initialize user session

        Knuth's Initialization:
        - Generate test images once
        - Store for reuse (efficiency)
        - Avoid regeneration overhead
        """
        self.source_b64 = image_to_base64(generate_test_image(color=(255, 0, 0)))
        self.target_b64 = image_to_base64(generate_test_image(color=(0, 0, 255)))

    @task(5)
    def view_home(self):
        """
        Task: View home page (weight: 5)

        Most common user action
        Expected: < 100ms
        """
        with self.client.get("/", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")

    @task(10)
    def view_algorithms(self):
        """
        Task: View available algorithms (weight: 10)

        Second most common action
        Expected: < 50ms
        """
        with self.client.get("/api/v1/algorithms", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")

    @task(3)
    def perform_transfer(self):
        """
        Task: Perform color transfer (weight: 3)

        Most expensive operation
        Expected: < 1000ms for small images

        Knuth's Performance Model:
        - Time = O(n) where n = image pixels
        - For 100x100: ~10-50ms
        - For 1000x1000: ~100-500ms
        """
        algorithms = ['reinhard_lab', 'reinhard_lch', 'rgb_direct', 'histogram_match']
        algorithm = random.choice(algorithms)

        payload = {
            "source_image": self.source_b64,
            "target_image": self.target_b64,
            "config": {
                "algorithm": algorithm,
                "blend_factor": random.uniform(0.5, 1.0),
                "clip_output": True,
                "preserve_luminance": False,
                "use_gpu": False
            }
        }

        start_time = time.time()

        with self.client.post(
            "/api/v1/transfer",
            json=payload,
            catch_response=True,
            timeout=30
        ) as response:
            duration_ms = (time.time() - start_time) * 1000

            if response.status_code == 200:
                # Verify response structure
                data = response.json()
                if 'result_image' in data and 'metrics' in data:
                    response.success()

                    # Log metrics for analysis
                    self.environment.events.request.fire(
                        request_type="transfer",
                        name=f"transfer_{algorithm}",
                        response_time=duration_ms,
                        response_length=len(response.content),
                        exception=None,
                        context={}
                    )
                else:
                    response.failure("Invalid response structure")
            else:
                response.failure(f"Got status code {response.status_code}")

    @task(2)
    def check_health(self):
        """
        Task: Check health endpoint (weight: 2)

        Monitoring/health checks
        Expected: < 10ms
        """
        with self.client.get("/health/live", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")

    @task(2)
    def check_metrics(self):
        """
        Task: Check metrics endpoint (weight: 2)

        Monitoring/metrics collection
        Expected: < 50ms
        """
        with self.client.get("/metrics", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")


class StressTestUser(HttpUser):
    """
    Stress test user - aggressive behavior

    Graham's Stress Testing:
    - No think time
    - Continuous requests
    - Larger payloads
    - Finds breaking points
    """

    wait_time = between(0.1, 0.5)  # Minimal wait time

    def on_start(self):
        # Generate larger images for stress testing
        self.source_b64 = image_to_base64(generate_test_image(size=(500, 500)))
        self.target_b64 = image_to_base64(generate_test_image(size=(500, 500)))

    @task
    def aggressive_transfer(self):
        """Aggressive transfer requests"""
        payload = {
            "source_image": self.source_b64,
            "target_image": self.target_b64,
            "config": {
                "algorithm": "reinhard_lab",
                "blend_factor": 1.0
            }
        }

        with self.client.post(
            "/api/v1/transfer",
            json=payload,
            catch_response=True,
            timeout=60
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 429:
                # Rate limited - expected under load
                response.success()
            else:
                response.failure(f"Got status code {response.status_code}")


# Custom statistics tracking

@events.init.add_listener
def on_locust_init(environment, **kwargs):
    """
    Initialize custom statistics

    Knuth's Statistical Analysis:
    - Track percentiles (p50, p95, p99)
    - Track error rates
    - Track throughput
    """
    environment.custom_stats = {
        'total_transfers': 0,
        'successful_transfers': 0,
        'failed_transfers': 0,
        'total_transfer_time': 0.0,
        'transfer_times': []
    }


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, context, **kwargs):
    """
    Track request statistics

    Graham's Metrics Collection:
    - Every request logged
    - Aggregated for analysis
    - Real-time statistics
    """
    if request_type == "transfer":
        stats = kwargs.get('environment').custom_stats if 'environment' in kwargs else None
        if stats:
            stats['total_transfers'] += 1
            if exception is None:
                stats['successful_transfers'] += 1
                stats['total_transfer_time'] += response_time
                stats['transfer_times'].append(response_time)
            else:
                stats['failed_transfers'] += 1


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """
    Print final statistics

    Knuth's Statistical Summary:
    - Mean, median, percentiles
    - Success rate
    - Throughput
    - Amdahl's Law analysis
    """
    stats = environment.custom_stats

    if stats['total_transfers'] > 0:
        print("\n" + "=" * 70)
        print("COLOR TRANSFER LOAD TEST RESULTS")
        print("=" * 70)

        success_rate = stats['successful_transfers'] / stats['total_transfers']
        print(f"Total Transfers: {stats['total_transfers']}")
        print(f"Successful: {stats['successful_transfers']}")
        print(f"Failed: {stats['failed_transfers']}")
        print(f"Success Rate: {success_rate:.2%}")

        if stats['successful_transfers'] > 0:
            avg_time = stats['total_transfer_time'] / stats['successful_transfers']
            print(f"\nAverage Transfer Time: {avg_time:.2f}ms")

            # Calculate percentiles
            if stats['transfer_times']:
                times = sorted(stats['transfer_times'])
                n = len(times)
                p50 = times[int(n * 0.50)]
                p95 = times[int(n * 0.95)]
                p99 = times[int(n * 0.99)]

                print(f"p50 (median): {p50:.2f}ms")
                print(f"p95: {p95:.2f}ms")
                print(f"p99: {p99:.2f}ms")

        print("=" * 70 + "\n")


# Knuth's Load Testing Analysis
"""
Load Testing Configuration Analysis (Knuth/Graham):
===================================================

Test Scenarios:

1. Smoke Test (Sanity Check):
   - Users: 1
   - Duration: 1 minute
   - Purpose: Verify basic functionality
   - Command: locust -f locustfile.py --headless -u 1 -r 1 -t 1m --host http://localhost:8000

2. Load Test (Normal Operation):
   - Users: 100
   - Spawn rate: 10 users/sec
   - Duration: 5 minutes
   - Purpose: Measure normal load performance
   - Command: locust -f locustfile.py --headless -u 100 -r 10 -t 5m --host http://localhost:8000

3. Stress Test (Find Breaking Point):
   - Users: 500
   - Spawn rate: 50 users/sec
   - Duration: 10 minutes
   - Purpose: Identify system limits
   - Command: locust -f locustfile.py --headless -u 500 -r 50 -t 10m --host http://localhost:8000

4. Spike Test (Sudden Load):
   - Users: 0 → 1000 → 0
   - Instant spawn
   - Duration: 2 minutes
   - Purpose: Test recovery
   - Command: locust -f locustfile.py --headless -u 1000 -r 1000 -t 2m --host http://localhost:8000

5. Endurance Test (Stability):
   - Users: 50
   - Spawn rate: 5 users/sec
   - Duration: 1 hour
   - Purpose: Memory leaks, degradation
   - Command: locust -f locustfile.py --headless -u 50 -r 5 -t 1h --host http://localhost:8000

Mathematical Expectations (Knuth):

Little's Law: L = λW
- If arrival rate λ = 100 req/s
- And average service time W = 0.1s
- Then queue length L = 100 * 0.1 = 10 requests

Throughput Limit:
- Single-threaded: ~100-500 req/s
- Multi-threaded (4 workers): ~400-2000 req/s
- With rate limiting (100 req/min): 1.67 req/s

Expected Results:
- p50 latency: 10-50ms (simple requests)
- p50 latency: 100-500ms (transfer requests)
- p95 latency: 2x p50
- p99 latency: 5x p50
- Success rate: > 99% under normal load
- Success rate: > 95% under stress load

Graham's Recommendations:
1. Start with smoke test
2. Gradually increase load
3. Monitor system resources (CPU, memory)
4. Identify bottlenecks
5. Optimize and retest
6. Document findings

Performance Baselines:
- API endpoints: < 100ms p95
- Transfer operations: < 1000ms p95
- Health checks: < 10ms p95
- Metrics endpoint: < 50ms p95

Failure Modes to Test:
- Rate limit exceeded (429)
- File too large (400)
- Invalid format (400)
- Server overload (503)
- Timeout (504)
"""
