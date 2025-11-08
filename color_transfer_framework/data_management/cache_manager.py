"""
Cache Manager
=============

Intelligent caching system to avoid reprocessing identical operations.

Features:
- Content-based cache keys (hashing inputs + config)
- LRU eviction policy
- Disk-based persistent cache
- Cache statistics and management
"""

import hashlib
import json
import pickle
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
import logging
from collections import OrderedDict
import cv2
import numpy as np

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Manage result caching to avoid reprocessing identical operations.

    Example:
        >>> cache = CacheManager()
        >>> result = cache.get(source_img, target_img, config)
        >>> if result is None:
        ...     result = perform_transfer(...)
        ...     cache.set(source_img, target_img, config, result)
    """

    def __init__(
        self,
        cache_dir: Optional[str] = None,
        max_entries: int = 1000,
        max_size_mb: int = 5000,
        ttl_days: int = 30
    ):
        """
        Initialize cache manager.

        Parameters:
        -----------
        cache_dir : str, optional
            Directory to store cache (default: ~/.color_transfer/cache)
        max_entries : int
            Maximum number of cached entries
        max_size_mb : int
            Maximum cache size in MB
        ttl_days : int
            Time-to-live for cache entries in days
        """
        if cache_dir is None:
            cache_dir = Path.home() / '.color_transfer' / 'cache'
        else:
            cache_dir = Path(cache_dir)

        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.max_entries = max_entries
        self.max_size_mb = max_size_mb
        self.ttl_days = ttl_days

        # Index file
        self.index_file = self.cache_dir / 'index.json'
        self.index: OrderedDict = self._load_index()

        # Statistics
        self.hits = 0
        self.misses = 0

    def _compute_key(
        self,
        source: np.ndarray,
        target: np.ndarray,
        config: Dict[str, Any]
    ) -> str:
        """
        Compute cache key from inputs.

        Uses content hashing to create unique key.
        """
        hasher = hashlib.sha256()

        # Hash source image
        hasher.update(source.tobytes())

        # Hash target image
        hasher.update(target.tobytes())

        # Hash config
        config_str = json.dumps(config, sort_keys=True)
        hasher.update(config_str.encode())

        return hasher.hexdigest()

    def get(
        self,
        source: np.ndarray,
        target: np.ndarray,
        config: Dict[str, Any]
    ) -> Optional[np.ndarray]:
        """
        Get cached result if available.

        Parameters:
        -----------
        source : np.ndarray
            Source image
        target : np.ndarray
            Target image
        config : Dict[str, Any]
            Transfer configuration

        Returns:
        --------
        np.ndarray or None
            Cached result, or None if not found
        """
        key = self._compute_key(source, target, config)

        if key not in self.index:
            self.misses += 1
            return None

        # Check TTL
        entry = self.index[key]
        created_at = datetime.fromisoformat(entry['created_at'])
        age = datetime.now() - created_at

        if age.days > self.ttl_days:
            # Expired
            logger.info(f"Cache entry expired: {key}")
            self.remove(key)
            self.misses += 1
            return None

        # Load from disk
        cache_file = self.cache_dir / f"{key}.pkl"
        if not cache_file.exists():
            logger.warning(f"Cache file missing: {cache_file}")
            del self.index[key]
            self.misses += 1
            return None

        try:
            with open(cache_file, 'rb') as f:
                result = pickle.load(f)

            # Move to end (LRU)
            self.index.move_to_end(key)
            self._save_index()

            self.hits += 1
            logger.info(f"Cache hit: {key}")
            return result

        except Exception as e:
            logger.error(f"Failed to load cache entry {key}: {e}")
            self.remove(key)
            self.misses += 1
            return None

    def set(
        self,
        source: np.ndarray,
        target: np.ndarray,
        config: Dict[str, Any],
        result: np.ndarray
    ) -> bool:
        """
        Store result in cache.

        Parameters:
        -----------
        source : np.ndarray
            Source image
        target : np.ndarray
            Target image
        config : Dict[str, Any]
            Transfer configuration
        result : np.ndarray
            Result image to cache

        Returns:
        --------
        bool
            True if cached successfully
        """
        key = self._compute_key(source, target, config)

        # Check if cache is full
        if len(self.index) >= self.max_entries:
            self._evict_oldest()

        # Save to disk
        cache_file = self.cache_dir / f"{key}.pkl"

        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(result, f, protocol=pickle.HIGHEST_PROTOCOL)

            file_size_mb = cache_file.stat().st_size / (1024 * 1024)

            # Update index
            self.index[key] = {
                'created_at': datetime.now().isoformat(),
                'size_mb': file_size_mb,
                'source_shape': source.shape,
                'target_shape': target.shape
            }

            self._save_index()

            # Check total size
            self._enforce_size_limit()

            logger.info(f"Cached result: {key} ({file_size_mb:.2f} MB)")
            return True

        except Exception as e:
            logger.error(f"Failed to cache result: {e}")
            return False

    def remove(self, key: str) -> bool:
        """Remove cache entry."""
        if key not in self.index:
            return False

        cache_file = self.cache_dir / f"{key}.pkl"
        if cache_file.exists():
            cache_file.unlink()

        del self.index[key]
        self._save_index()
        return True

    def clear(self) -> int:
        """Clear entire cache."""
        count = 0

        for key in list(self.index.keys()):
            if self.remove(key):
                count += 1

        logger.info(f"Cleared cache: {count} entries removed")
        return count

    def _evict_oldest(self):
        """Evict oldest (least recently used) entry."""
        if not self.index:
            return

        oldest_key = next(iter(self.index))
        self.remove(oldest_key)
        logger.info(f"Evicted oldest cache entry: {oldest_key}")

    def _enforce_size_limit(self):
        """Enforce maximum cache size."""
        total_size = sum(entry['size_mb'] for entry in self.index.values())

        while total_size > self.max_size_mb and self.index:
            self._evict_oldest()
            total_size = sum(entry['size_mb'] for entry in self.index.values())

    def _load_index(self) -> OrderedDict:
        """Load cache index from disk."""
        if not self.index_file.exists():
            return OrderedDict()

        try:
            with open(self.index_file, 'r') as f:
                data = json.load(f)
                return OrderedDict(data)
        except Exception as e:
            logger.error(f"Failed to load cache index: {e}")
            return OrderedDict()

    def _save_index(self):
        """Save cache index to disk."""
        try:
            with open(self.index_file, 'w') as f:
                json.dump(self.index, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save cache index: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_size = sum(entry['size_mb'] for entry in self.index.values())
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0

        return {
            'entries': len(self.index),
            'total_size_mb': total_size,
            'max_entries': self.max_entries,
            'max_size_mb': self.max_size_mb,
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate_percent': hit_rate,
            'ttl_days': self.ttl_days
        }

    def cleanup_expired(self) -> int:
        """Remove expired cache entries."""
        count = 0
        now = datetime.now()

        for key, entry in list(self.index.items()):
            created_at = datetime.fromisoformat(entry['created_at'])
            age = now - created_at

            if age.days > self.ttl_days:
                self.remove(key)
                count += 1

        if count > 0:
            logger.info(f"Cleaned up {count} expired cache entries")

        return count
