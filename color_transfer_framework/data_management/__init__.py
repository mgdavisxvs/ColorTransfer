"""
Data Management Module
======================

Data persistence, caching, and cleanup features:
- Result caching (avoid reprocessing)
- Image deduplication using hashes
- Automatic cleanup of old results
- Export/import of run history
- Database migrations
"""

from .cache_manager import CacheManager
from .hash_deduplicator import HashDeduplicator
from .cleanup_manager import CleanupManager
from .history_exporter import HistoryExporter

__all__ = [
    'CacheManager',
    'HashDeduplicator',
    'CleanupManager',
    'HistoryExporter'
]
