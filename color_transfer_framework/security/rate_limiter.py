"""
Rate Limiting Implementation - Mathematical Analysis (Knuth/Graham)

Implements multiple rate limiting algorithms with mathematical analysis:
1. Token Bucket - Allows bursts, smooth long-term rate
2. Sliding Window - Precise request counting
3. Fixed Window - Simple but has boundary issues

Mathematical Analysis (Knuth):
- Throughput bounds
- Burst capacity
- Fairness guarantees
- Space complexity: O(n) for sliding window, O(1) for token bucket
- Time complexity: O(1) for all operations

Practical Implementation (Graham):
- Thread-safe operations
- Efficient memory usage
- Clear error messages
- Production-ready
"""

import time
import threading
from dataclasses import dataclass, field
from typing import Dict, Optional, List
from collections import deque
from enum import Enum


class RateLimitStrategy(Enum):
    """Rate limiting strategies"""
    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"


@dataclass
class RateLimitConfig:
    """
    Rate limit configuration

    Knuth's Analysis:
    - rate: Maximum requests per window (R)
    - window_seconds: Time window (T)
    - burst_size: Maximum burst capacity (B)

    Throughput bound: R/T requests per second
    Burst bound: B requests instantaneously
    """
    rate: int = 100  # Maximum requests per window
    window_seconds: float = 60.0  # Time window in seconds
    burst_size: Optional[int] = None  # Max burst (defaults to rate)

    def __post_init__(self):
        if self.burst_size is None:
            self.burst_size = self.rate

        # Validate configuration
        assert self.rate > 0, "Rate must be positive"
        assert self.window_seconds > 0, "Window must be positive"
        assert self.burst_size >= self.rate, "Burst size must be >= rate"


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded"""

    def __init__(self, retry_after: float):
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded. Retry after {retry_after:.2f} seconds")


class TokenBucketLimiter:
    """
    Token Bucket Rate Limiter

    Mathematical Model (Knuth):
    ========================

    Bucket capacity: B tokens
    Refill rate: r tokens/second

    Token dynamics:
    - tokens(t) = min(B, tokens(t-1) + r*Δt)
    - Request allowed if tokens(t) >= 1

    Properties:
    1. Burst handling: Up to B requests instantaneously
    2. Long-term rate: r requests/second
    3. Smoothing: Accumulates unused capacity

    Complexity:
    - Space: O(1) per client
    - Time: O(1) per check

    Fairness (Graham):
    - Fair over long time periods
    - Allows bursts for bursty workloads
    - No request dropping at boundaries
    """

    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.rate_per_second = config.rate / config.window_seconds

        # Per-client state: {client_id: (tokens, last_update_time)}
        self._buckets: Dict[str, tuple[float, float]] = {}
        self._lock = threading.Lock()

    def _refill_tokens(self, client_id: str, current_time: float) -> float:
        """
        Refill tokens based on elapsed time

        Knuth's Token Accumulation:
        tokens_new = min(B, tokens_old + r * Δt)

        where:
        - B = burst_size (bucket capacity)
        - r = rate_per_second
        - Δt = current_time - last_time
        """
        if client_id not in self._buckets:
            # Initialize with full bucket
            self._buckets[client_id] = (float(self.config.burst_size), current_time)
            return float(self.config.burst_size)

        tokens, last_time = self._buckets[client_id]
        elapsed = current_time - last_time

        # Refill tokens based on elapsed time
        new_tokens = min(
            self.config.burst_size,
            tokens + self.rate_per_second * elapsed
        )

        self._buckets[client_id] = (new_tokens, current_time)
        return new_tokens

    def check_rate_limit(self, client_id: str, cost: int = 1) -> bool:
        """
        Check if request is allowed under rate limit

        Args:
            client_id: Unique identifier for client
            cost: Token cost for this request (default 1)

        Returns:
            True if request allowed, False otherwise

        Raises:
            RateLimitExceeded: If rate limit exceeded (with retry time)
        """
        with self._lock:
            current_time = time.time()
            tokens = self._refill_tokens(client_id, current_time)

            if tokens >= cost:
                # Consume tokens and allow request
                self._buckets[client_id] = (tokens - cost, current_time)
                return True
            else:
                # Calculate retry-after time
                # tokens_needed = cost - tokens
                # time_needed = tokens_needed / rate_per_second
                retry_after = (cost - tokens) / self.rate_per_second
                raise RateLimitExceeded(retry_after)

    def get_stats(self, client_id: str) -> Dict[str, float]:
        """
        Get current statistics for client

        Returns:
            tokens_available: Current token count
            capacity_utilization: Fraction of capacity used (0-1)
            time_to_full: Seconds until bucket is full
        """
        with self._lock:
            current_time = time.time()
            tokens = self._refill_tokens(client_id, current_time)

            capacity_utilization = 1.0 - (tokens / self.config.burst_size)
            time_to_full = (self.config.burst_size - tokens) / self.rate_per_second

            return {
                'tokens_available': tokens,
                'capacity_utilization': capacity_utilization,
                'time_to_full': time_to_full,
                'burst_capacity': self.config.burst_size,
                'rate_per_second': self.rate_per_second
            }


class SlidingWindowLimiter:
    """
    Sliding Window Rate Limiter

    Mathematical Model (Knuth):
    ==========================

    Window size: W seconds
    Max requests: R

    Sliding window: [t - W, t]
    Request allowed if: count(requests in [t-W, t]) < R

    Properties:
    1. Precise: Exactly counts requests in window
    2. No boundary issues: Window slides continuously
    3. Memory: Stores all request timestamps

    Complexity:
    - Space: O(R) per client (stores R timestamps)
    - Time: O(n) per check (where n = requests in window)

    Improvement (Graham):
    - Use deque for O(1) append/popleft
    - Prune old requests automatically
    - Efficient timestamp storage
    """

    def __init__(self, config: RateLimitConfig):
        self.config = config

        # Per-client request timestamps: {client_id: deque[timestamp]}
        self._windows: Dict[str, deque] = {}
        self._lock = threading.Lock()

    def _prune_old_requests(self, client_id: str, current_time: float):
        """
        Remove requests older than window

        Pruning Strategy (Graham):
        - Use deque.popleft() for O(1) removal
        - Continue until oldest request is within window
        """
        if client_id not in self._windows:
            self._windows[client_id] = deque()
            return

        window = self._windows[client_id]
        cutoff_time = current_time - self.config.window_seconds

        # Remove old requests from left (oldest)
        while window and window[0] < cutoff_time:
            window.popleft()

    def check_rate_limit(self, client_id: str) -> bool:
        """
        Check if request is allowed under sliding window

        Algorithm:
        1. Prune requests older than window
        2. Check if count < rate
        3. If allowed, add current timestamp

        Time Complexity: O(n) where n = old requests to prune
        Amortized: O(1) if requests are evenly distributed
        """
        with self._lock:
            current_time = time.time()
            self._prune_old_requests(client_id, current_time)

            window = self._windows[client_id]

            if len(window) < self.config.rate:
                # Allow request and record timestamp
                window.append(current_time)
                return True
            else:
                # Calculate retry-after time
                # Oldest request will expire first
                oldest_request = window[0]
                retry_after = oldest_request + self.config.window_seconds - current_time
                raise RateLimitExceeded(max(0, retry_after))

    def get_stats(self, client_id: str) -> Dict[str, float]:
        """Get current statistics for client"""
        with self._lock:
            current_time = time.time()
            self._prune_old_requests(client_id, current_time)

            window = self._windows[client_id]
            request_count = len(window)

            remaining = self.config.rate - request_count
            utilization = request_count / self.config.rate

            return {
                'requests_in_window': request_count,
                'remaining_requests': remaining,
                'window_utilization': utilization,
                'max_requests': self.config.rate,
                'window_seconds': self.config.window_seconds
            }


class RateLimiter:
    """
    Unified Rate Limiter with Multiple Strategies

    Graham's Practical Approach:
    - Single interface for multiple algorithms
    - Easy strategy switching
    - Consistent error handling

    Usage:
        limiter = RateLimiter(strategy=RateLimitStrategy.TOKEN_BUCKET)

        try:
            limiter.check("user_123")
            # Process request
        except RateLimitExceeded as e:
            # Return 429 with Retry-After header
            return {"error": str(e), "retry_after": e.retry_after}
    """

    def __init__(
        self,
        config: Optional[RateLimitConfig] = None,
        strategy: RateLimitStrategy = RateLimitStrategy.TOKEN_BUCKET
    ):
        self.config = config or RateLimitConfig()
        self.strategy = strategy

        # Initialize appropriate limiter
        if strategy == RateLimitStrategy.TOKEN_BUCKET:
            self._limiter = TokenBucketLimiter(self.config)
        elif strategy == RateLimitStrategy.SLIDING_WINDOW:
            self._limiter = SlidingWindowLimiter(self.config)
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

    def check(self, client_id: str, cost: int = 1) -> bool:
        """
        Check rate limit for client

        Args:
            client_id: Unique client identifier (e.g., IP, user ID, API key)
            cost: Token cost (only for token bucket)

        Returns:
            True if request allowed

        Raises:
            RateLimitExceeded: If limit exceeded
        """
        if isinstance(self._limiter, TokenBucketLimiter):
            return self._limiter.check_rate_limit(client_id, cost)
        else:
            return self._limiter.check_rate_limit(client_id)

    def get_stats(self, client_id: str) -> Dict[str, float]:
        """Get statistics for client"""
        return self._limiter.get_stats(client_id)

    def reset(self, client_id: str):
        """Reset rate limit for client (useful for testing)"""
        if isinstance(self._limiter, TokenBucketLimiter):
            with self._limiter._lock:
                if client_id in self._limiter._buckets:
                    del self._limiter._buckets[client_id]
        elif isinstance(self._limiter, SlidingWindowLimiter):
            with self._limiter._lock:
                if client_id in self._limiter._windows:
                    del self._limiter._windows[client_id]


# Knuth's Comparative Analysis
"""
Rate Limiting Algorithm Comparison (Knuth):
===========================================

1. Token Bucket
   Pros:
   - O(1) space per client
   - Handles bursts elegantly
   - Smooths over time

   Cons:
   - Less precise than sliding window
   - Requires floating-point arithmetic

   Best for: APIs with bursty traffic

2. Sliding Window
   Pros:
   - Precise request counting
   - No boundary issues
   - Predictable behavior

   Cons:
   - O(R) space per client
   - O(n) time per check (n = pruned requests)

   Best for: Strict rate enforcement

3. Fixed Window (not implemented)
   Pros:
   - O(1) space and time
   - Very simple

   Cons:
   - Boundary issue: 2R requests in 2 windows
   - Unfair at boundaries

   Best for: Simple quotas

Graham's Recommendation:
- Use Token Bucket for general APIs (good burst handling)
- Use Sliding Window for strict compliance (e.g., external API limits)
- Monitor stats and adjust parameters based on actual traffic
"""
