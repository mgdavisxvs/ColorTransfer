"""
Advanced Processing Module
===========================

Advanced features for production workflows:
- Batch directory processing
- Video frame-by-frame transfer
- Real-time webcam processing
- Plugin system for custom algorithms
- Color palette extraction
- Multi-image blending
"""

from .batch_processor import BatchProcessor
from .video_processor import VideoProcessor
from .webcam_processor import WebcamProcessor
from .plugin_manager import PluginManager
from .palette_extractor import PaletteExtractor
from .multi_blend import MultiBlender

__all__ = [
    'BatchProcessor',
    'VideoProcessor',
    'WebcamProcessor',
    'PluginManager',
    'PaletteExtractor',
    'MultiBlender'
]
