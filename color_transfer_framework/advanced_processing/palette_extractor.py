"""
Palette Extractor
=================

Extract dominant color palettes from images.

Features:
- K-means clustering for color extraction
- Multiple palette size options
- Color histogram analysis
- Export to various formats
"""

import cv2
import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional
import logging
from sklearn.cluster import KMeans
from collections import Counter

logger = logging.getLogger(__name__)


class PaletteExtractor:
    """
    Extract dominant color palettes from images.

    Example:
        >>> extractor = PaletteExtractor()
        >>> palette = extractor.extract_palette("image.jpg", n_colors=5)
        >>> extractor.visualize_palette(palette, "palette.png")
    """

    def extract_palette(
        self,
        image_path: str,
        n_colors: int = 5,
        method: str = 'kmeans',
        sample_fraction: float = 0.1
    ) -> List[Tuple[int, int, int]]:
        """
        Extract dominant colors from image.

        Parameters:
        -----------
        image_path : str
            Path to input image
        n_colors : int
            Number of colors to extract
        method : str
            Extraction method ('kmeans', 'histogram')
        sample_fraction : float
            Fraction of pixels to sample (for performance)

        Returns:
        --------
        List[Tuple[int, int, int]]
            List of RGB color tuples
        """
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Failed to load image: {image_path}")

        # Convert BGR to RGB
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        if method == 'kmeans':
            return self._extract_kmeans(img_rgb, n_colors, sample_fraction)
        elif method == 'histogram':
            return self._extract_histogram(img_rgb, n_colors)
        else:
            raise ValueError(f"Unknown method: {method}")

    def _extract_kmeans(
        self,
        image: np.ndarray,
        n_colors: int,
        sample_fraction: float
    ) -> List[Tuple[int, int, int]]:
        """Extract colors using k-means clustering."""
        # Reshape image to list of pixels
        pixels = image.reshape(-1, 3)

        # Sample pixels for performance
        if sample_fraction < 1.0:
            n_samples = int(len(pixels) * sample_fraction)
            indices = np.random.choice(len(pixels), n_samples, replace=False)
            pixels = pixels[indices]

        # Perform k-means clustering
        kmeans = KMeans(n_clusters=n_colors, random_state=42, n_init=10)
        kmeans.fit(pixels)

        # Get cluster centers (dominant colors)
        colors = kmeans.cluster_centers_.astype(int)

        # Sort by cluster size (most common first)
        labels = kmeans.labels_
        label_counts = Counter(labels)
        sorted_colors = [colors[i] for i, _ in label_counts.most_common()]

        return [tuple(color) for color in sorted_colors]

    def _extract_histogram(
        self,
        image: np.ndarray,
        n_colors: int
    ) -> List[Tuple[int, int, int]]:
        """Extract colors using histogram analysis."""
        # Quantize colors to reduce color space
        quantized = (image // 32) * 32  # 8 bins per channel

        # Reshape and count colors
        pixels = quantized.reshape(-1, 3)
        unique_colors, counts = np.unique(pixels, axis=0, return_counts=True)

        # Sort by frequency
        sorted_indices = np.argsort(-counts)
        top_colors = unique_colors[sorted_indices[:n_colors]]

        return [tuple(color) for color in top_colors]

    def visualize_palette(
        self,
        palette: List[Tuple[int, int, int]],
        output_path: str,
        swatch_size: int = 100
    ) -> None:
        """
        Create visual representation of color palette.

        Parameters:
        -----------
        palette : List[Tuple[int, int, int]]
            List of RGB colors
        output_path : str
            Path to save visualization
        swatch_size : int
            Size of each color swatch in pixels
        """
        n_colors = len(palette)
        width = swatch_size * n_colors
        height = swatch_size

        # Create image
        img = np.zeros((height, width, 3), dtype=np.uint8)

        # Draw color swatches
        for i, color in enumerate(palette):
            x_start = i * swatch_size
            x_end = x_start + swatch_size
            img[:, x_start:x_end] = color

        # Convert RGB to BGR for OpenCV
        img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

        # Save
        cv2.imwrite(output_path, img_bgr)
        logger.info(f"Palette visualization saved: {output_path}")

    def create_palette_image(
        self,
        palette: List[Tuple[int, int, int]],
        size: Tuple[int, int] = (512, 512)
    ) -> np.ndarray:
        """
        Create an image filled with palette colors.

        Parameters:
        -----------
        palette : List[Tuple[int, int, int]]
            List of RGB colors
        size : Tuple[int, int]
            Output image size (width, height)

        Returns:
        --------
        np.ndarray
            BGR image filled with palette colors
        """
        n_colors = len(palette)
        width, height = size

        # Create image
        img = np.zeros((height, width, 3), dtype=np.uint8)

        # Fill with colors in stripes
        stripe_width = width // n_colors

        for i, color in enumerate(palette):
            x_start = i * stripe_width
            x_end = x_start + stripe_width if i < n_colors - 1 else width
            img[:, x_start:x_end] = color

        # Convert RGB to BGR
        return cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    def export_palette_json(
        self,
        palette: List[Tuple[int, int, int]],
        output_path: str,
        name: str = "Palette"
    ) -> None:
        """
        Export palette to JSON format.

        Parameters:
        -----------
        palette : List[Tuple[int, int, int]]
            List of RGB colors
        output_path : str
            Path to save JSON file
        name : str
            Palette name
        """
        import json

        data = {
            "name": name,
            "colors": [
                {
                    "rgb": color,
                    "hex": "#{:02x}{:02x}{:02x}".format(*color)
                }
                for color in palette
            ]
        }

        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)

        logger.info(f"Palette exported to JSON: {output_path}")
