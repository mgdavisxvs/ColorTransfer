"""
Cleanup Manager
===============

Automatic cleanup of old results and temporary files.
"""

import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class CleanupManager:
    """Manage automatic cleanup of old results."""

    def __init__(self, results_dir: str = None):
        if results_dir is None:
            results_dir = Path.home() / '.color_transfer' / 'results'
        self.results_dir = Path(results_dir)

    def cleanup_old_files(self, days: int = 30) -> Dict[str, Any]:
        """Delete files older than specified days."""
        if not self.results_dir.exists():
            return {'removed': 0, 'freed_mb': 0}

        cutoff_date = datetime.now() - timedelta(days=days)
        removed = 0
        freed_bytes = 0

        for file_path in self.results_dir.rglob('*'):
            if file_path.is_file():
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                if mtime < cutoff_date:
                    size = file_path.stat().st_size
                    file_path.unlink()
                    removed += 1
                    freed_bytes += size

        freed_mb = freed_bytes / (1024 * 1024)
        logger.info(f"Cleanup: removed {removed} files, freed {freed_mb:.2f} MB")

        return {'removed': removed, 'freed_mb': freed_mb}

    def cleanup_empty_dirs(self) -> int:
        """Remove empty directories."""
        count = 0
        for dir_path in sorted(self.results_dir.rglob('*'), reverse=True):
            if dir_path.is_dir() and not any(dir_path.iterdir()):
                dir_path.rmdir()
                count += 1

        if count > 0:
            logger.info(f"Removed {count} empty directories")
        return count

    def get_disk_usage(self) -> Dict[str, Any]:
        """Get current disk usage statistics."""
        if not self.results_dir.exists():
            return {'total_files': 0, 'total_size_mb': 0}

        total_size = 0
        total_files = 0

        for file_path in self.results_dir.rglob('*'):
            if file_path.is_file():
                total_size += file_path.stat().st_size
                total_files += 1

        return {
            'total_files': total_files,
            'total_size_mb': total_size / (1024 * 1024),
            'location': str(self.results_dir)
        }
