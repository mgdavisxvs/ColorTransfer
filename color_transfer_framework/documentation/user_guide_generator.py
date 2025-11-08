"""
User Guide Generator
====================

Generate comprehensive user guides and tutorials.
"""

from pathlib import Path
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class UserGuideGenerator:
    """
    Generate user guides and tutorials.

    Example:
        >>> generator = UserGuideGenerator()
        >>> generator.generate_quick_start()
        >>> generator.save('docs/user_guide.md')
    """

    def __init__(self):
        self.sections: List[str] = []

    def generate_quick_start(self) -> str:
        """Generate quick start guide."""
        self.sections = []

        self._add("# Quick Start Guide\n")

        self._add("## Installation\n")
        self._add("```bash")
        self._add("pip install -r requirements.txt")
        self._add("```\n")

        self._add("## Basic Usage\n")

        self._add("### Command Line\n")
        self._add("```bash")
        self._add("# Simple transfer")
        self._add("color-transfer transfer source.jpg target.jpg -o result.jpg")
        self._add("")
        self._add("# With options")
        self._add("color-transfer transfer source.jpg target.jpg \\")
        self._add("    --algo reinhard_lab \\")
        self._add("    --blend 0.8 \\")
        self._add("    --visualize")
        self._add("```\n")

        self._add("### Python API\n")
        self._add("```python")
        self._add("from color_transfer_framework.transfer_engine import TransferEngine, TransferConfig")
        self._add("import cv2")
        self._add("")
        self._add("# Load images")
        self._add("source = cv2.imread('source.jpg')")
        self._add("target = cv2.imread('target.jpg')")
        self._add("")
        self._add("# Configure transfer")
        self._add("config = TransferConfig(")
        self._add("    algorithm='reinhard_lab',")
        self._add("    blend_factor=0.8")
        self._add(")")
        self._add("")
        self._add("# Apply transfer")
        self._add("engine = TransferEngine()")
        self._add("result = engine.transfer(source, target, config)")
        self._add("")
        self._add("# Save result")
        self._add("cv2.imwrite('result.jpg', result)")
        self._add("```\n")

        self._add("### Web Interface\n")
        self._add("```bash")
        self._add("# Start web server")
        self._add("python -m color_transfer_framework.interface_layer.web_enhanced")
        self._add("")
        self._add("# Visit http://localhost:5000")
        self._add("```\n")

        return '\n'.join(self.sections)

    def generate_advanced_guide(self) -> str:
        """Generate advanced usage guide."""
        self.sections = []

        self._add("# Advanced Usage Guide\n")

        self._add("## Batch Processing\n")
        self._add("```bash")
        self._add("color-transfer batch source.jpg ./photos \\")
        self._add("    --output ./results \\")
        self._add("    --workers 8 \\")
        self._add("    --recursive")
        self._add("```\n")

        self._add("## Video Processing\n")
        self._add("```bash")
        self._add("color-transfer video palette.jpg input.mp4 \\")
        self._add("    --output result.mp4 \\")
        self._add("    --codec mp4v")
        self._add("```\n")

        self._add("## Webcam Processing\n")
        self._add("```bash")
        self._add("color-transfer webcam palette.jpg \\")
        self._add("    --camera 0 \\")
        self._add("    --fps \\")
        self._add("    --record output.mp4")
        self._add("```\n")

        self._add("## Palette Extraction\n")
        self._add("```bash")
        self._add("color-transfer palette image.jpg \\")
        self._add("    --colors 5 \\")
        self._add("    --method kmeans \\")
        self._add("    --json")
        self._add("```\n")

        self._add("## Multi-Image Blending\n")
        self._add("```bash")
        self._add("color-transfer multi-blend \\")
        self._add("    palette1.jpg palette2.jpg palette3.jpg \\")
        self._add("    target.jpg \\")
        self._add("    --weights 0.5,0.3,0.2")
        self._add("```\n")

        self._add("## Deep Learning Transfer\n")
        self._add("```python")
        self._add("from color_transfer_framework.ml_hybrid import DeepColorTransfer")
        self._add("")
        self._add("deep_transfer = DeepColorTransfer(use_gpu=True)")
        self._add("result = deep_transfer.transfer(source, target, method='neural')")
        self._add("```\n")

        return '\n'.join(self.sections)

    def generate_api_examples(self) -> str:
        """Generate API usage examples."""
        self.sections = []

        self._add("# API Examples\n")

        self._add("## REST API\n")
        self._add("### Transfer Image\n")
        self._add("```python")
        self._add("import requests")
        self._add("import base64")
        self._add("")
        self._add("# Encode images")
        self._add("with open('source.jpg', 'rb') as f:")
        self._add("    source_b64 = base64.b64encode(f.read()).decode()")
        self._add("")
        self._add("with open('target.jpg', 'rb') as f:")
        self._add("    target_b64 = base64.b64encode(f.read()).decode()")
        self._add("")
        self._add("# Request transfer")
        self._add("response = requests.post('http://localhost:8000/api/v1/transfer', json={")
        self._add("    'source_image': source_b64,")
        self._add("    'target_image': target_b64,")
        self._add("    'config': {'algorithm': 'reinhard_lab', 'blend_factor': 0.8}")
        self._add("})")
        self._add("")
        self._add("# Get result")
        self._add("result_b64 = response.json()['result_image']")
        self._add("```\n")

        self._add("### WebSocket Progress\n")
        self._add("```javascript")
        self._add("const ws = new WebSocket('ws://localhost:8000/api/v1/ws/progress/client_123');")
        self._add("")
        self._add("ws.onmessage = (event) => {")
        self._add("    const {status, percent} = JSON.parse(event.data);")
        self._add("    console.log(`${percent}%: ${status}`);")
        self._add("};")
        self._add("```\n")

        return '\n'.join(self.sections)

    def _add(self, line: str):
        """Add line to guide."""
        self.sections.append(line)

    def save(self, output_path: str):
        """Save guide to file."""
        content = '\n'.join(self.sections)
        Path(output_path).write_text(content)
        logger.info(f"User guide saved to {output_path}")
