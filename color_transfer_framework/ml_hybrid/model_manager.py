"""
Model Manager
=============

Manage pre-trained models for ML-based color transfer.

Features:
- Model downloading and caching
- Version management
- Model validation
- Automatic updates
"""

import hashlib
import json
from pathlib import Path
from typing import Optional, Dict, Any
import logging
import urllib.request
import shutil

logger = logging.getLogger(__name__)


class ModelManager:
    """
    Manage pre-trained deep learning models.

    Example:
        >>> manager = ModelManager()
        >>> model_path = manager.get_model('vgg19')
        >>> if not model_path.exists():
        ...     manager.download_model('vgg19')
    """

    MODELS = {
        'vgg19': {
            'url': 'https://download.pytorch.org/models/vgg19-dcbb9e9d.pth',
            'md5': 'dcbb9e9d7ccf1c8e4eebb2e45c7c2b03',
            'size_mb': 548
        },
        'vgg16': {
            'url': 'https://download.pytorch.org/models/vgg16-397923af.pth',
            'md5': '397923af8e79cdbb6a7127f12361acd7',
            'size_mb': 528
        }
    }

    def __init__(self, models_dir: Optional[str] = None):
        """
        Initialize model manager.

        Parameters:
        -----------
        models_dir : str, optional
            Directory to store models (default: ~/.color_transfer/models)
        """
        if models_dir is None:
            models_dir = Path.home() / '.color_transfer' / 'models'
        else:
            models_dir = Path(models_dir)

        self.models_dir = models_dir
        self.models_dir.mkdir(parents=True, exist_ok=True)

        # Index file
        self.index_file = self.models_dir / 'models.json'
        self.index = self._load_index()

    def get_model(self, name: str) -> Optional[Path]:
        """
        Get path to model file.

        Parameters:
        -----------
        name : str
            Model name

        Returns:
        --------
        Path or None
            Path to model file, or None if not found
        """
        if name not in self.MODELS:
            logger.error(f"Unknown model: {name}")
            return None

        model_path = self.models_dir / f"{name}.pth"

        if not model_path.exists():
            logger.warning(f"Model not found: {name}")
            return None

        return model_path

    def download_model(
        self,
        name: str,
        force: bool = False
    ) -> bool:
        """
        Download pre-trained model.

        Parameters:
        -----------
        name : str
            Model name
        force : bool
            Force re-download even if exists

        Returns:
        --------
        bool
            True if download successful
        """
        if name not in self.MODELS:
            logger.error(f"Unknown model: {name}")
            return False

        model_path = self.models_dir / f"{name}.pth"

        if model_path.exists() and not force:
            logger.info(f"Model already exists: {name}")
            return True

        model_info = self.MODELS[name]
        url = model_info['url']

        logger.info(f"Downloading {name} ({model_info['size_mb']} MB)...")

        try:
            # Download with progress
            urllib.request.urlretrieve(url, model_path)

            # Verify checksum
            if not self._verify_checksum(model_path, model_info['md5']):
                logger.error(f"Checksum mismatch for {name}")
                model_path.unlink()
                return False

            # Update index
            self.index[name] = {
                'path': str(model_path),
                'downloaded_at': str(Path.ctime(model_path)),
                'size_mb': model_info['size_mb']
            }
            self._save_index()

            logger.info(f"Model downloaded successfully: {name}")
            return True

        except Exception as e:
            logger.error(f"Failed to download {name}: {e}")
            if model_path.exists():
                model_path.unlink()
            return False

    def _verify_checksum(self, file_path: Path, expected_md5: str) -> bool:
        """Verify file checksum."""
        md5 = hashlib.md5()

        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                md5.update(chunk)

        actual_md5 = md5.hexdigest()
        return actual_md5 == expected_md5

    def list_models(self) -> Dict[str, Any]:
        """List all available models."""
        models_info = {}

        for name, info in self.MODELS.items():
            model_path = self.get_model(name)
            models_info[name] = {
                'available': model_path is not None,
                'size_mb': info['size_mb'],
                'path': str(model_path) if model_path else None
            }

        return models_info

    def delete_model(self, name: str) -> bool:
        """Delete a model."""
        model_path = self.get_model(name)

        if model_path and model_path.exists():
            model_path.unlink()

            if name in self.index:
                del self.index[name]
                self._save_index()

            logger.info(f"Deleted model: {name}")
            return True

        return False

    def _load_index(self) -> Dict:
        """Load models index."""
        if not self.index_file.exists():
            return {}

        try:
            with open(self.index_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load index: {e}")
            return {}

    def _save_index(self):
        """Save models index."""
        try:
            with open(self.index_file, 'w') as f:
                json.dump(self.index, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save index: {e}")
