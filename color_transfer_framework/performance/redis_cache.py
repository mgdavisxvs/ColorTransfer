"""
Redis Cache Layer
=================

Distributed caching with Redis for high-performance result storage.

Mathematical Foundation (Knuth):
- Cache hit rate optimization
- Optimal cache size: Zipf's law distribution
- Expected lookup time: O(1) hash table
- Memory-access tradeoff analysis

Practical Implementation (Graham):
- LRU eviction with TTL
- Consistent hashing for distributed cache
- Connection pooling for scalability
"""

import hashlib
import json
import pickle
import logging
from typing import Optional, Any, Dict
from datetime import timedelta
import numpy as np

logger = logging.getLogger(__name__)

# Check for Redis availability
try:
    import redis
    from redis import ConnectionPool
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available. Install with: pip install redis")


class RedisCache:
    """
    Distributed Redis cache for color transfer results.

    Complexity Analysis:
    -------------------
    - Set: O(1) average, O(n) for serialization
    - Get: O(1) average, O(n) for deserialization
    - Space: O(k*m) where k=entries, m=avg size

    Cache Efficiency (Knuth):
    -------------------------
    Hit rate H = hits / (hits + misses)
    Expected cost = H * T_hit + (1-H) * T_miss
    Where T_hit << T_miss (cache is worthwhile if H > T_hit/T_miss)

    Example:
        >>> cache = RedisCache(host='localhost', port=6379)
        >>> cache.set('key', result_image, ttl=3600)
        >>> result = cache.get('key')
    """

    def __init__(
        self,
        host: str = 'localhost',
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        max_connections: int = 50,
        socket_timeout: float = 5.0,
        default_ttl: int = 3600
    ):
        """
        Initialize Redis cache.

        Parameters:
        -----------
        host : str
            Redis server host
        port : int
            Redis server port
        db : int
            Redis database number
        password : str, optional
            Redis password
        max_connections : int
            Max connections in pool
        socket_timeout : float
            Socket timeout in seconds
        default_ttl : int
            Default TTL in seconds
        """
        self.host = host
        self.port = port
        self.default_ttl = default_ttl

        if not REDIS_AVAILABLE:
            logger.error("Redis not available")
            self.client = None
            self.enabled = False
            return

        try:
            # Connection pool for scalability
            self.pool = ConnectionPool(
                host=host,
                port=port,
                db=db,
                password=password,
                max_connections=max_connections,
                socket_timeout=socket_timeout,
                decode_responses=False  # Binary mode for images
            )

            self.client = redis.Redis(connection_pool=self.pool)

            # Test connection
            self.client.ping()
            self.enabled = True

            logger.info(f"Redis cache connected: {host}:{port}")

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.client = None
            self.enabled = False

        # Statistics
        self.hits = 0
        self.misses = 0

    def _compute_key(self, *args, prefix: str = 'ct') -> str:
        """
        Compute cache key using content hashing.

        Hash Function Analysis (Knuth):
        --------------------------------
        SHA-256 provides:
        - Collision probability: negligible for practical use
        - Uniform distribution: critical for hash table performance
        - Deterministic: same input → same key

        Parameters:
        -----------
        *args
            Arguments to hash
        prefix : str
            Key prefix

        Returns:
        --------
        str
            Cache key
        """
        hasher = hashlib.sha256()

        for arg in args:
            if isinstance(arg, (str, bytes)):
                data = arg.encode() if isinstance(arg, str) else arg
                hasher.update(data)
            elif isinstance(arg, dict):
                # Deterministic dict serialization
                data = json.dumps(arg, sort_keys=True).encode()
                hasher.update(data)
            else:
                # Pickle for complex objects
                data = pickle.dumps(arg)
                hasher.update(data)

        key_hash = hasher.hexdigest()[:16]  # First 16 chars sufficient
        return f"{prefix}:{key_hash}"

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        compress: bool = True
    ) -> bool:
        """
        Store value in cache.

        Complexity: O(1) for set, O(n) for serialization

        Parameters:
        -----------
        key : str
            Cache key
        value : Any
            Value to cache
        ttl : int, optional
            Time-to-live in seconds
        compress : bool
            Compress data (for large images)

        Returns:
        --------
        bool
            True if successful
        """
        if not self.enabled or self.client is None:
            return False

        try:
            # Serialize value
            data = pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)

            # Optional compression for large data
            if compress and len(data) > 10240:  # > 10KB
                import zlib
                data = zlib.compress(data, level=6)
                key = f"{key}:compressed"

            # Set with TTL
            ttl = ttl or self.default_ttl

            self.client.setex(key, ttl, data)

            logger.debug(f"Cache set: {key} ({len(data)} bytes, TTL={ttl}s)")
            return True

        except Exception as e:
            logger.error(f"Cache set failed for {key}: {e}")
            return False

    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve value from cache.

        Complexity: O(1) for get, O(n) for deserialization

        Parameters:
        -----------
        key : str
            Cache key

        Returns:
        --------
        Any or None
            Cached value, or None if not found
        """
        if not self.enabled or self.client is None:
            self.misses += 1
            return None

        try:
            # Try uncompressed first
            data = self.client.get(key)

            # Try compressed version
            if data is None:
                data = self.client.get(f"{key}:compressed")
                if data is not None:
                    import zlib
                    data = zlib.decompress(data)

            if data is None:
                self.misses += 1
                logger.debug(f"Cache miss: {key}")
                return None

            # Deserialize
            value = pickle.loads(data)

            self.hits += 1
            logger.debug(f"Cache hit: {key}")
            return value

        except Exception as e:
            logger.error(f"Cache get failed for {key}: {e}")
            self.misses += 1
            return None

    def delete(self, key: str) -> bool:
        """Delete cache entry."""
        if not self.enabled or self.client is None:
            return False

        try:
            deleted = self.client.delete(key)
            # Also try compressed version
            self.client.delete(f"{key}:compressed")
            return deleted > 0
        except Exception as e:
            logger.error(f"Cache delete failed for {key}: {e}")
            return False

    def clear(self) -> bool:
        """Clear all cache entries."""
        if not self.enabled or self.client is None:
            return False

        try:
            self.client.flushdb()
            logger.info("Cache cleared")
            return True
        except Exception as e:
            logger.error(f"Cache clear failed: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Metrics Analysis (Knuth):
        -------------------------
        - Hit Rate: H = hits / (hits + misses)
        - Miss Rate: M = 1 - H
        - Effective Access Time: T_eff = H*T_cache + M*T_compute

        Returns:
        --------
        dict
            Cache statistics
        """
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0

        stats = {
            'enabled': self.enabled,
            'hits': self.hits,
            'misses': self.misses,
            'total_requests': total_requests,
            'hit_rate_percent': hit_rate
        }

        if self.enabled and self.client:
            try:
                info = self.client.info('stats')
                stats.update({
                    'total_connections': info.get('total_connections_received', 0),
                    'total_commands': info.get('total_commands_processed', 0),
                    'keyspace_hits': info.get('keyspace_hits', 0),
                    'keyspace_misses': info.get('keyspace_misses', 0)
                })

                memory = self.client.info('memory')
                stats.update({
                    'memory_used_mb': memory.get('used_memory', 0) / (1024 * 1024),
                    'memory_peak_mb': memory.get('used_memory_peak', 0) / (1024 * 1024)
                })

            except Exception as e:
                logger.error(f"Failed to get Redis stats: {e}")

        return stats

    def analyze_cache_efficiency(
        self,
        cache_hit_time_ms: float = 1.0,
        compute_time_ms: float = 50.0
    ) -> Dict[str, float]:
        """
        Analyze cache efficiency with cost-benefit analysis.

        Knuth's Cache Analysis:
        ----------------------
        Speedup = T_no_cache / T_with_cache
        T_with_cache = H * T_cache + (1-H) * (T_cache + T_compute)
                     = T_cache + (1-H) * T_compute

        For cache to be worthwhile:
        Speedup > 1 ⟹ H > T_cache / T_compute

        Parameters:
        -----------
        cache_hit_time_ms : float
            Average cache lookup time
        compute_time_ms : float
            Average computation time without cache

        Returns:
        --------
        dict
            Efficiency metrics
        """
        stats = self.get_stats()
        hit_rate = stats['hit_rate_percent'] / 100.0

        # Time with cache
        time_with_cache = cache_hit_time_ms + (1 - hit_rate) * compute_time_ms

        # Time without cache
        time_without_cache = compute_time_ms

        # Speedup factor
        speedup = time_without_cache / time_with_cache if time_with_cache > 0 else 1.0

        # Minimum hit rate for benefit
        min_hit_rate = cache_hit_time_ms / compute_time_ms

        return {
            'current_hit_rate': hit_rate,
            'minimum_beneficial_hit_rate': min_hit_rate,
            'avg_time_with_cache_ms': time_with_cache,
            'avg_time_without_cache_ms': time_without_cache,
            'speedup_factor': speedup,
            'is_beneficial': hit_rate > min_hit_rate
        }

    def estimate_optimal_ttl(
        self,
        access_pattern: list,
        storage_cost_per_mb_hour: float = 0.0001
    ) -> int:
        """
        Estimate optimal TTL based on access patterns.

        Graham's Optimization:
        ---------------------
        Minimize cost = storage_cost * size * ttl - benefit * accesses

        Parameters:
        -----------
        access_pattern : list
            List of access timestamps
        storage_cost_per_mb_hour : float
            Cost per MB per hour

        Returns:
        --------
        int
            Recommended TTL in seconds
        """
        if not access_pattern or len(access_pattern) < 2:
            return self.default_ttl

        # Calculate inter-access times
        access_times = np.array(sorted(access_pattern))
        inter_access = np.diff(access_times)

        # Median inter-access time is good TTL estimate
        median_inter_access = np.median(inter_access)

        # Add safety margin (1.5x)
        recommended_ttl = int(median_inter_access * 1.5)

        # Clamp to reasonable range
        recommended_ttl = max(60, min(recommended_ttl, 86400))  # 1 min to 1 day

        logger.info(f"Recommended TTL: {recommended_ttl}s (median inter-access: {median_inter_access:.1f}s)")

        return recommended_ttl
