"""
Distributed Processor
====================

Distributed task processing using Celery + RabbitMQ.

Mathematical Foundation (Knuth):
- Queue Theory: M/M/c model for task processing
- Expected wait time: W = (λ/μ) * (1/(c - ρ)) where ρ = λ/(c*μ)
- Optimal worker count: c* = ceil(λ/μ * (1 + safety_factor))

Practical Implementation (Graham):
- Task partitioning strategies
- Dynamic worker scaling
- Fault tolerance and retry logic
"""

import logging
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass
from datetime import datetime
import numpy as np

logger = logging.getLogger(__name__)

# Check for Celery availability
try:
    from celery import Celery, Task
    from celery.result import AsyncResult
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    logger.warning("Celery not available. Install with: pip install celery[redis]")


@dataclass
class WorkloadMetrics:
    """
    Workload analysis metrics.

    Based on queueing theory:
    - λ (lambda): Arrival rate (tasks/second)
    - μ (mu): Service rate (tasks/second per worker)
    - c: Number of workers
    - ρ (rho): Utilization = λ/(c*μ)
    """
    arrival_rate: float  # λ
    service_rate: float  # μ
    num_workers: int     # c

    @property
    def utilization(self) -> float:
        """System utilization ρ = λ/(c*μ)"""
        return self.arrival_rate / (self.num_workers * self.service_rate)

    @property
    def is_stable(self) -> bool:
        """System is stable if ρ < 1"""
        return self.utilization < 1.0

    @property
    def expected_queue_length(self) -> float:
        """
        Expected queue length (Erlang C formula approximation).

        L = ρ/(1-ρ) for M/M/1
        For M/M/c, use Erlang C formula approximation
        """
        if not self.is_stable:
            return float('inf')

        rho = self.utilization
        c = self.num_workers

        # Simplified approximation
        return (rho * c) / (1 - rho)

    @property
    def expected_wait_time(self) -> float:
        """
        Expected wait time in queue (seconds).

        W = L/λ (Little's Law)
        """
        if not self.is_stable:
            return float('inf')

        return self.expected_queue_length / self.arrival_rate


class DistributedProcessor:
    """
    Distributed task processing with optimal worker allocation.

    Example:
        >>> processor = DistributedProcessor(broker_url='amqp://localhost')
        >>> result = processor.submit_transfer_task(source, target, config)
        >>> output = result.get(timeout=30)
    """

    def __init__(
        self,
        broker_url: str = 'amqp://localhost',
        backend_url: str = 'redis://localhost:6379/0',
        max_workers: int = 8,
        task_queue: str = 'color_transfer'
    ):
        """
        Initialize distributed processor.

        Parameters:
        -----------
        broker_url : str
            RabbitMQ broker URL
        backend_url : str
            Redis backend URL for results
        max_workers : int
            Maximum number of concurrent workers
        task_queue : str
            Queue name for tasks
        """
        self.broker_url = broker_url
        self.backend_url = backend_url
        self.max_workers = max_workers
        self.task_queue = task_queue

        if not CELERY_AVAILABLE:
            logger.error("Celery not available. Distributed processing disabled.")
            self.app = None
            return

        # Initialize Celery app
        self.app = Celery(
            'color_transfer',
            broker=broker_url,
            backend=backend_url
        )

        # Configure Celery
        self.app.conf.update(
            task_serializer='json',
            accept_content=['json'],
            result_serializer='json',
            timezone='UTC',
            enable_utc=True,
            task_track_started=True,
            task_time_limit=3600,  # 1 hour
            task_soft_time_limit=3000,  # 50 minutes
            worker_prefetch_multiplier=1,  # Fair distribution
            worker_max_tasks_per_child=100,  # Prevent memory leaks
            task_acks_late=True,  # Reliability
            task_reject_on_worker_lost=True,
            task_default_queue=task_queue,
            task_routes={
                'transfer_task': {'queue': task_queue},
                'batch_task': {'queue': f'{task_queue}_batch'},
                'video_task': {'queue': f'{task_queue}_video'}
            }
        )

        # Register tasks
        self._register_tasks()

        # Metrics tracking
        self.task_history: List[Dict[str, Any]] = []

    def _register_tasks(self):
        """Register Celery tasks."""
        if not CELERY_AVAILABLE:
            return

        @self.app.task(name='transfer_task', bind=True)
        def transfer_task(task_self, source_b64: str, target_b64: str, config_dict: Dict):
            """
            Distributed color transfer task.

            Complexity Analysis (Knuth):
            - Time: O(n*m) where n,m are image dimensions
            - Space: O(n*m) for image storage
            - Communication: O(n*m) for data transfer
            """
            try:
                from ..interface_layer.orchestrator import TransferOrchestrator
                from ..transfer_engine import TransferConfig, TransferAlgorithm
                import base64
                import cv2
                import numpy as np

                # Update task state
                task_self.update_state(state='PROCESSING', meta={'progress': 0})

                # Deserialize images
                source_bytes = base64.b64decode(source_b64)
                target_bytes = base64.b64decode(target_b64)

                source_array = np.frombuffer(source_bytes, dtype=np.uint8)
                target_array = np.frombuffer(target_bytes, dtype=np.uint8)

                source_img = cv2.imdecode(source_array, cv2.IMREAD_COLOR)
                target_img = cv2.imdecode(target_array, cv2.IMREAD_COLOR)

                # Build config
                config = TransferConfig(
                    algorithm=TransferAlgorithm(config_dict['algorithm']),
                    blend_factor=config_dict.get('blend_factor', 1.0)
                )

                # Progress callback
                def progress_callback(status: str, percent: int):
                    task_self.update_state(
                        state='PROCESSING',
                        meta={'progress': percent, 'status': status}
                    )

                # Perform transfer
                orchestrator = TransferOrchestrator()
                result = orchestrator.transfer(
                    source_img,
                    target_img,
                    config=config,
                    progress_callback=progress_callback,
                    interface_type='DISTRIBUTED'
                )

                # Serialize result
                _, buffer = cv2.imencode('.png', result.result_image)
                result_b64 = base64.b64encode(buffer).decode('utf-8')

                return {
                    'result_image': result_b64,
                    'metrics': {
                        'execution_time_ms': result.metrics.execution_time_ms,
                        'memory_used_mb': result.metrics.memory_used_mb
                    }
                }

            except Exception as e:
                logger.error(f"Transfer task failed: {e}")
                raise

        self.transfer_task = transfer_task

    def submit_transfer(
        self,
        source_b64: str,
        target_b64: str,
        config: Dict[str, Any],
        priority: int = 5
    ) -> Optional['AsyncResult']:
        """
        Submit transfer task to distributed queue.

        Parameters:
        -----------
        source_b64 : str
            Base64 encoded source image
        target_b64 : str
            Base64 encoded target image
        config : dict
            Transfer configuration
        priority : int
            Task priority (0-9, higher = more priority)

        Returns:
        --------
        AsyncResult or None
            Task result handle
        """
        if not CELERY_AVAILABLE or self.app is None:
            logger.error("Celery not available")
            return None

        result = self.transfer_task.apply_async(
            args=[source_b64, target_b64, config],
            priority=priority,
            countdown=0
        )

        # Track task
        self.task_history.append({
            'task_id': result.id,
            'submitted_at': datetime.now(),
            'priority': priority
        })

        return result

    def get_result(
        self,
        task_id: str,
        timeout: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get result of completed task.

        Parameters:
        -----------
        task_id : str
            Task ID
        timeout : float, optional
            Timeout in seconds

        Returns:
        --------
        dict or None
            Task result
        """
        if not CELERY_AVAILABLE:
            return None

        result = AsyncResult(task_id, app=self.app)

        try:
            return result.get(timeout=timeout)
        except Exception as e:
            logger.error(f"Failed to get result for {task_id}: {e}")
            return None

    def analyze_workload(
        self,
        arrival_rate: float,
        avg_processing_time: float
    ) -> WorkloadMetrics:
        """
        Analyze workload and recommend optimal worker count.

        Mathematical Analysis (Knuth):
        --------------------------------
        Given:
        - λ: arrival rate (tasks/second)
        - μ: service rate = 1/avg_processing_time (tasks/second)

        Find optimal c (worker count) such that:
        1. System is stable: λ < c*μ
        2. Utilization is reasonable: ρ ∈ [0.7, 0.9]
        3. Expected wait time is acceptable: W < threshold

        Parameters:
        -----------
        arrival_rate : float
            Expected task arrival rate (tasks/second)
        avg_processing_time : float
            Average task processing time (seconds)

        Returns:
        --------
        WorkloadMetrics
            Workload analysis with recommendations
        """
        service_rate = 1.0 / avg_processing_time  # μ

        # Calculate minimum workers for stability
        min_workers = int(np.ceil(arrival_rate / service_rate)) + 1

        # Find optimal workers for target utilization (0.75)
        target_utilization = 0.75
        optimal_workers = int(np.ceil(arrival_rate / (service_rate * target_utilization)))

        # Use maximum of minimum and optimal, capped at max_workers
        recommended_workers = min(
            max(min_workers, optimal_workers),
            self.max_workers
        )

        metrics = WorkloadMetrics(
            arrival_rate=arrival_rate,
            service_rate=service_rate,
            num_workers=recommended_workers
        )

        logger.info(
            f"Workload Analysis:\n"
            f"  Arrival Rate: {arrival_rate:.2f} tasks/s\n"
            f"  Service Rate: {service_rate:.2f} tasks/s/worker\n"
            f"  Recommended Workers: {recommended_workers}\n"
            f"  Utilization: {metrics.utilization:.2%}\n"
            f"  Expected Queue Length: {metrics.expected_queue_length:.2f}\n"
            f"  Expected Wait Time: {metrics.expected_wait_time:.2f}s"
        )

        return metrics

    def get_queue_length(self) -> int:
        """Get current queue length."""
        if not CELERY_AVAILABLE or self.app is None:
            return 0

        # This requires Celery inspector
        try:
            inspect = self.app.control.inspect()
            active = inspect.active()
            reserved = inspect.reserved()

            if active and reserved:
                total = sum(len(tasks) for tasks in active.values())
                total += sum(len(tasks) for tasks in reserved.values())
                return total
        except:
            pass

        return 0

    def get_worker_stats(self) -> Dict[str, Any]:
        """Get worker statistics."""
        if not CELERY_AVAILABLE or self.app is None:
            return {}

        try:
            inspect = self.app.control.inspect()
            stats = inspect.stats()
            active = inspect.active()

            return {
                'workers': stats,
                'active_tasks': active,
                'total_workers': len(stats) if stats else 0
            }
        except Exception as e:
            logger.error(f"Failed to get worker stats: {e}")
            return {}
