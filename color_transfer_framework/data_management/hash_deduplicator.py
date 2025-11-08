"""
Hash Deduplicator
=================

Detect and manage duplicate images using perceptual hashing.
"""

import hashlib
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class HashDeduplicator:
    """Detect duplicate images using content hashing."""

    def __init__(self):
        self.hashes: Dict[str, List[Path]] = defaultdict(list)

    def compute_hash(self, image_path: str, method: str = 'md5') -> str:
        """Compute hash of image file."""
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Failed to load: {image_path}")

        if method == 'md5':
            return hashlib.md5(img.tobytes()).hexdigest()
        elif method == 'sha256':
            return hashlib.sha256(img.tobytes()).hexdigest()
        elif method == 'perceptual':
            return self._perceptual_hash(img)
        else:
            raise ValueError(f"Unknown method: {method}")

    def _perceptual_hash(self, img: np.ndarray, hash_size: int = 8) -> str:
        """Compute perceptual hash (pHash)."""
        # Resize to hash_size x hash_size
        resized = cv2.resize(img, (hash_size, hash_size))
        # Convert to grayscale
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        # Compute average
        avg = gray.mean()
        # Create hash
        diff = gray > avg
        return ''.join('1' if d else '0' for d in diff.flatten())

    def scan_directory(self, directory: str, method: str = 'md5') -> Dict[str, List[Path]]:
        """Scan directory and group duplicates."""
        path = Path(directory)
        self.hashes.clear()

        for img_path in path.rglob('*'):
            if img_path.suffix.lower() in {'.jpg', '.jpeg', '.png', '.bmp'}:
                try:
                    h = self.compute_hash(str(img_path), method)
                    self.hashes[h].append(img_path)
                except Exception as e:
                    logger.warning(f"Failed to hash {img_path}: {e}")

        return {h: paths for h, paths in self.hashes.items() if len(paths) > 1}

    def get_duplicates(self) -> Dict[str, List[Path]]:
        """Get groups of duplicate images."""
        return {h: paths for h, paths in self.hashes.items() if len(paths) > 1}
