"""
Background Job Queue
====================

Asynchronous job queue for long-running operations.

Mathematical Foundation (Knuth):
- Priority queue: O(log n) insertion/extraction with heap
- FIFO queue: O(1) enqueue/dequeue with linked list
- Job scheduling: Earliest Deadline First (EDF) optimal

Practical Implementation (Graham):
- Graceful degradation under load
- Dead letter queue for failed jobs
- Exponential backoff for retries
"""

import logging
import time
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import heapq
from queue import PriorityQueue
import threading
import uuid

logger = logging.getLogger(__name__)


class JobStatus(Enum):
    """Job execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class JobPriority(Enum):
    """Job priority levels."""
    LOW = 3
    NORMAL = 2
    HIGH = 1
    URGENT = 0


@dataclass(order=True)
class Job:
    """
    Background job representation.

    Priority Queue Ordering (Knuth):
    --------------------------------
    Jobs ordered by: (priority, submit_time)
    Lower priority value = higher priority
    Earlier submit_time = processed first (FIFO within priority)
    """
    priority: int = field(compare=True)
    submit_time: float = field(compare=True)
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()), compare=False)
    task_name: str = field(default="", compare=False)
    args: tuple = field(default_factory=tuple, compare=False)
    kwargs: dict = field(default_factory=dict, compare=False)
    status: JobStatus = field(default=JobStatus.PENDING, compare=False)
    result: Any = field(default=None, compare=False)
    error: Optional[str] = field(default=None, compare=False)
    retry_count: int = field(default=0, compare=False)
    max_retries: int = field(default=3, compare=False)
    created_at: datetime = field(default_factory=datetime.now, compare=False)
    started_at: Optional[datetime] = field(default=None, compare=False)
    completed_at: Optional[datetime] = field(default=None, compare=False)

    @property
    def execution_time(self) -> Optional[float]:
        """Execution time in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def wait_time(self) -> Optional[float]:
        """Queue wait time in seconds."""
        if self.started_at:
            return (self.started_at - self.created_at).total_seconds()
        return None


class BackgroundJobQueue:
    """
    Priority-based job queue for long-running operations.

    Complexity Analysis:
    -------------------
    - Enqueue: O(log n) - heap insertion
    - Dequeue: O(log n) - heap extraction
    - Status check: O(1) - dict lookup
    - Space: O(n) for n jobs

    Scheduling Theory (Knuth):
    --------------------------
    For jobs with deadlines, EDF is optimal:
    - Sort by deadline
    - Process in order
    - Meets all deadlines if any schedule can

    Example:
        >>> queue = BackgroundJobQueue(num_workers=4)
        >>> job_id = queue.submit(process_video, 'input.mp4', priority='high')
        >>> result = queue.wait_for_job(job_id, timeout=60)
    """

    def __init__(
        self,
        num_workers: int = 4,
        max_queue_size: int = 1000,
        enable_dead_letter: bool = True
    ):
        """
        Initialize job queue.

        Parameters:
        -----------
        num_workers : int
            Number of worker threads
        max_queue_size : int
            Maximum queue size
        enable_dead_letter : bool
            Enable dead letter queue for failed jobs
        """
        self.num_workers = num_workers
        self.max_queue_size = max_queue_size
        self.enable_dead_letter = enable_dead_letter

        # Priority queue
        self.queue: PriorityQueue = PriorityQueue(maxsize=max_queue_size)

        # Job registry
        self.jobs: Dict[str, Job] = {}

        # Dead letter queue
        self.dead_letter: List[Job] = []

        # Task registry
        self.tasks: Dict[str, Callable] = {}

        # Worker threads
        self.workers: List[threading.Thread] = []
        self.running = False

        # Statistics
        self.total_submitted = 0
        self.total_completed = 0
        self.total_failed = 0

        logger.info(f"Job queue initialized: {num_workers} workers, max_queue={max_queue_size}")

    def register_task(self, name: str, func: Callable):
        """
        Register task function.

        Parameters:
        -----------
        name : str
            Task name
        func : callable
            Task function
        """
        self.tasks[name] = func
        logger.info(f"Registered task: {name}")

    def submit(
        self,
        task_name: str,
        *args,
        priority: str = 'normal',
        max_retries: int = 3,
        **kwargs
    ) -> str:
        """
        Submit job to queue.

        Complexity: O(log n) for priority queue insertion

        Parameters:
        -----------
        task_name : str
            Registered task name
        *args
            Task arguments
        priority : str
            Job priority (urgent, high, normal, low)
        max_retries : int
            Maximum retry attempts
        **kwargs
            Task keyword arguments

        Returns:
        --------
        str
            Job ID
        """
        if task_name not in self.tasks:
            raise ValueError(f"Unknown task: {task_name}")

        # Convert priority
        priority_value = getattr(JobPriority, priority.upper(), JobPriority.NORMAL).value

        # Create job
        job = Job(
            priority=priority_value,
            submit_time=time.time(),
            task_name=task_name,
            args=args,
            kwargs=kwargs,
            max_retries=max_retries
        )

        # Add to queue
        try:
            self.queue.put(job, block=False)
            self.jobs[job.job_id] = job
            self.total_submitted += 1

            logger.info(
                f"Job submitted: {job.job_id} "
                f"(task={task_name}, priority={priority})"
            )

            return job.job_id

        except:
            logger.error("Queue full, cannot submit job")
            raise RuntimeError("Job queue full")

    def start(self):
        """Start worker threads."""
        if self.running:
            logger.warning("Job queue already running")
            return

        self.running = True

        # Start workers
        for i in range(self.num_workers):
            worker = threading.Thread(
                target=self._worker_loop,
                name=f"JobWorker-{i}",
                daemon=True
            )
            worker.start()
            self.workers.append(worker)

        logger.info(f"Started {self.num_workers} worker threads")

    def stop(self, timeout: float = 10.0):
        """
        Stop worker threads.

        Parameters:
        -----------
        timeout : float
            Shutdown timeout in seconds
        """
        logger.info("Stopping job queue...")
        self.running = False

        # Wait for workers to finish
        for worker in self.workers:
            worker.join(timeout=timeout / self.num_workers)

        self.workers.clear()
        logger.info("Job queue stopped")

    def _worker_loop(self):
        """Worker thread main loop."""
        while self.running:
            try:
                # Get next job (with timeout to check running flag)
                job = self.queue.get(timeout=1.0)

                # Execute job
                self._execute_job(job)

            except:
                # Queue empty or timeout, continue
                continue

    def _execute_job(self, job: Job):
        """
        Execute a job.

        Retry Strategy (Graham):
        -----------------------
        Exponential backoff: delay = base * 2^retry_count
        Prevents thundering herd on failures.

        Parameters:
        -----------
        job : Job
            Job to execute
        """
        job.status = JobStatus.RUNNING
        job.started_at = datetime.now()

        logger.info(f"Executing job: {job.job_id} (task={job.task_name})")

        try:
            # Get task function
            task_func = self.tasks[job.task_name]

            # Execute
            result = task_func(*job.args, **job.kwargs)

            # Success
            job.status = JobStatus.COMPLETED
            job.result = result
            job.completed_at = datetime.now()
            self.total_completed += 1

            logger.info(
                f"Job completed: {job.job_id} "
                f"(time={job.execution_time:.2f}s)"
            )

        except Exception as e:
            logger.error(f"Job failed: {job.job_id}: {e}")

            job.error = str(e)
            job.retry_count += 1

            # Retry logic with exponential backoff
            if job.retry_count < job.max_retries:
                job.status = JobStatus.RETRYING

                # Exponential backoff: 1s, 2s, 4s, 8s, ...
                backoff_delay = min(2 ** job.retry_count, 60)  # Cap at 60s

                logger.info(
                    f"Retrying job {job.job_id} "
                    f"(attempt {job.retry_count}/{job.max_retries}, "
                    f"delay={backoff_delay}s)"
                )

                # Requeue with delay
                time.sleep(backoff_delay)
                self.queue.put(job)

            else:
                # Max retries exceeded
                job.status = JobStatus.FAILED
                job.completed_at = datetime.now()
                self.total_failed += 1

                # Add to dead letter queue
                if self.enable_dead_letter:
                    self.dead_letter.append(job)

                logger.error(
                    f"Job failed permanently: {job.job_id} "
                    f"(retries exhausted)"
                )

    def get_job_status(self, job_id: str) -> Optional[JobStatus]:
        """Get job status."""
        job = self.jobs.get(job_id)
        return job.status if job else None

    def get_job_result(self, job_id: str) -> Optional[Any]:
        """Get job result."""
        job = self.jobs.get(job_id)
        if job and job.status == JobStatus.COMPLETED:
            return job.result
        return None

    def wait_for_job(
        self,
        job_id: str,
        timeout: Optional[float] = None
    ) -> Optional[Any]:
        """
        Wait for job completion and return result.

        Parameters:
        -----------
        job_id : str
            Job ID
        timeout : float, optional
            Timeout in seconds

        Returns:
        --------
        Any or None
            Job result
        """
        start_time = time.time()

        while True:
            job = self.jobs.get(job_id)

            if not job:
                return None

            if job.status == JobStatus.COMPLETED:
                return job.result

            if job.status == JobStatus.FAILED:
                raise RuntimeError(f"Job failed: {job.error}")

            if timeout and (time.time() - start_time) > timeout:
                raise TimeoutError(f"Job timeout: {job_id}")

            time.sleep(0.1)

    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel pending job.

        Note: Cannot cancel running jobs.

        Parameters:
        -----------
        job_id : str
            Job ID

        Returns:
        --------
        bool
            True if cancelled
        """
        job = self.jobs.get(job_id)

        if not job:
            return False

        if job.status == JobStatus.PENDING:
            job.status = JobStatus.CANCELLED
            logger.info(f"Job cancelled: {job_id}")
            return True

        logger.warning(f"Cannot cancel job {job_id}: status={job.status}")
        return False

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get queue statistics.

        Little's Law (Knuth):
        --------------------
        L = λ * W
        Where:
        - L: avg queue length
        - λ: arrival rate
        - W: avg wait time

        Returns:
        --------
        dict
            Queue statistics
        """
        pending = sum(1 for j in self.jobs.values() if j.status == JobStatus.PENDING)
        running = sum(1 for j in self.jobs.values() if j.status == JobStatus.RUNNING)

        # Calculate average wait and execution times
        completed_jobs = [j for j in self.jobs.values() if j.status == JobStatus.COMPLETED]

        if completed_jobs:
            avg_wait = sum(j.wait_time for j in completed_jobs) / len(completed_jobs)
            avg_exec = sum(j.execution_time for j in completed_jobs) / len(completed_jobs)
        else:
            avg_wait = avg_exec = 0

        return {
            'total_submitted': self.total_submitted,
            'total_completed': self.total_completed,
            'total_failed': self.total_failed,
            'success_rate': (self.total_completed / self.total_submitted * 100)
                           if self.total_submitted > 0 else 0,
            'pending_jobs': pending,
            'running_jobs': running,
            'dead_letter_size': len(self.dead_letter),
            'avg_wait_time_s': avg_wait,
            'avg_execution_time_s': avg_exec,
            'num_workers': self.num_workers
        }
