"""
ColorStatisticsEngine Module
============================

Computes and manages color statistics for images.

Responsibilities:
- Compute color statistics (mean, std, covariance, histograms)
- Handle region-of-interest (ROI) statistics
- Compare statistical distributions
- Provide efficient caching and reuse

Design Principles:
- Single Responsibility: Only statistical computations
- Performance: Vectorized NumPy operations
- Extensibility: Easy to add new statistics
"""

import numpy as np
import cv2
from typing import Optional, Tuple, Dict, List
from dataclasses import dataclass, field
from enum import Enum


class StatisticType(Enum):
    """Types of statistics that can be computed."""
    MEAN = "mean"
    STD = "std"
    VARIANCE = "variance"
    MEDIAN = "median"
    MODE = "mode"
    RANGE = "range"
    HISTOGRAM = "histogram"
    COVARIANCE = "covariance"
    ENTROPY = "entropy"


@dataclass
class ColorStatistics:
    """
    Container for color statistics.

    This dataclass holds all computed statistics for an image,
    providing a structured and type-safe interface.

    Attributes:
    ----------
    mean : np.ndarray
        Per-channel mean values
    std : np.ndarray
        Per-channel standard deviations
    variance : np.ndarray
        Per-channel variances
    median : Optional[np.ndarray]
        Per-channel median values
    histogram : Optional[Dict[int, np.ndarray]]
        Per-channel histograms
    covariance : Optional[np.ndarray]
        Covariance matrix between channels
    entropy : Optional[np.ndarray]
        Per-channel entropy values
    num_pixels : int
        Total number of pixels
    num_channels : int
        Number of color channels
    metadata : Dict
        Additional metadata
    """
    mean: np.ndarray
    std: np.ndarray
    variance: np.ndarray
    median: Optional[np.ndarray] = None
    histogram: Optional[Dict[int, np.ndarray]] = None
    covariance: Optional[np.ndarray] = None
    entropy: Optional[np.ndarray] = None
    num_pixels: int = 0
    num_channels: int = 0
    metadata: Dict = field(default_factory=dict)

    def __repr__(self) -> str:
        return (f"ColorStatistics(mean={self.mean}, std={self.std}, "
                f"pixels={self.num_pixels}, channels={self.num_channels})")

    def summary(self) -> str:
        """Return a human-readable summary of statistics."""
        lines = []
        lines.append(f"Color Statistics Summary")
        lines.append(f"{'='*50}")
        lines.append(f"Pixels: {self.num_pixels:,}")
        lines.append(f"Channels: {self.num_channels}")
        lines.append(f"\nPer-Channel Statistics:")
        for i in range(self.num_channels):
            lines.append(f"  Channel {i}:")
            lines.append(f"    Mean:     {self.mean[i]:.4f}")
            lines.append(f"    Std Dev:  {self.std[i]:.4f}")
            lines.append(f"    Variance: {self.variance[i]:.4f}")
            if self.median is not None:
                lines.append(f"    Median:   {self.median[i]:.4f}")
            if self.entropy is not None:
                lines.append(f"    Entropy:  {self.entropy[i]:.4f}")

        return "\n".join(lines)


class ColorStatisticsEngine:
    """
    Computes color statistics for images.

    This engine provides comprehensive statistical analysis of images,
    supporting masked regions, multiple statistics types, and efficient
    caching for repeated queries.

    Example:
    -------
    >>> engine = ColorStatisticsEngine()
    >>> stats = engine.compute_stats(image)
    >>> print(stats.summary())
    >>> hist = engine.get_distribution(image, channel=0)
    """

    def __init__(self, cache_stats: bool = True):
        """
        Initialize ColorStatisticsEngine.

        Parameters:
        ----------
        cache_stats : bool
            Whether to cache computed statistics for reuse
        """
        self.cache_stats = cache_stats
        self._stats_cache: Dict[int, ColorStatistics] = {}

    def compute_stats(self,
                     image: np.ndarray,
                     mask: Optional[np.ndarray] = None,
                     compute_all: bool = False) -> ColorStatistics:
        """
        Compute color statistics for an image.

        Parameters:
        ----------
        image : np.ndarray
            Input image (can be multi-channel or grayscale)
        mask : Optional[np.ndarray]
            Binary mask for region of interest (None = full image)
        compute_all : bool
            Whether to compute all statistics (expensive)

        Returns:
        -------
        ColorStatistics
            Computed statistics

        Complexity:
        ----------
        Time: O(n) where n = number of pixels
        Space: O(n) for histogram storage (if computed)
        """
        # Check cache
        if self.cache_stats and mask is None:
            cache_key = hash(image.tobytes())
            if cache_key in self._stats_cache:
                return self._stats_cache[cache_key]

        # Prepare image data
        if len(image.shape) == 2:
            # Grayscale
            pixels = image.reshape(-1, 1)
            num_channels = 1
        else:
            # Multi-channel
            pixels = image.reshape(-1, image.shape[2])
            num_channels = image.shape[2]

        # Apply mask if provided
        if mask is not None:
            mask_flat = mask.reshape(-1)
            pixels = pixels[mask_flat > 0]

        num_pixels = pixels.shape[0]

        # Convert to float64 for precision
        pixels_float = pixels.astype(np.float64)

        # Compute basic statistics (always computed)
        mean = np.mean(pixels_float, axis=0)
        std = np.std(pixels_float, axis=0, ddof=0)  # Population std
        variance = std ** 2

        # Optional statistics
        median = None
        histogram = None
        covariance = None
        entropy = None

        if compute_all:
            # Median (expensive for large images)
            median = np.median(pixels_float, axis=0)

            # Histogram
            histogram = self._compute_histogram(pixels, num_channels)

            # Covariance matrix (only for multi-channel)
            if num_channels > 1:
                covariance = np.cov(pixels_float.T)

            # Entropy
            entropy = self._compute_entropy_from_pixels(pixels, num_channels)

        # Create statistics object
        stats = ColorStatistics(
            mean=mean,
            std=std,
            variance=variance,
            median=median,
            histogram=histogram,
            covariance=covariance,
            entropy=entropy,
            num_pixels=num_pixels,
            num_channels=num_channels,
            metadata={
                'masked': mask is not None,
                'image_shape': image.shape,
            }
        )

        # Cache if enabled
        if self.cache_stats and mask is None:
            cache_key = hash(image.tobytes())
            self._stats_cache[cache_key] = stats

        return stats

    def _compute_histogram(self,
                          pixels: np.ndarray,
                          num_channels: int,
                          bins: int = 256) -> Dict[int, np.ndarray]:
        """
        Compute per-channel histograms.

        Parameters:
        ----------
        pixels : np.ndarray
            Pixel array (n_pixels, n_channels)
        num_channels : int
            Number of channels
        bins : int
            Number of histogram bins

        Returns:
        -------
        Dict[int, np.ndarray]
            Dictionary mapping channel index to histogram
        """
        histograms = {}

        for c in range(num_channels):
            channel_data = pixels[:, c]
            hist, _ = np.histogram(channel_data, bins=bins, density=True)
            histograms[c] = hist

        return histograms

    def _compute_entropy_from_pixels(self,
                                    pixels: np.ndarray,
                                    num_channels: int,
                                    bins: int = 256) -> np.ndarray:
        """
        Compute Shannon entropy per channel.

        H(X) = -Σ p(x) log₂ p(x)

        Parameters:
        ----------
        pixels : np.ndarray
            Pixel array
        num_channels : int
            Number of channels
        bins : int
            Number of histogram bins

        Returns:
        -------
        np.ndarray
            Per-channel entropy values
        """
        entropies = np.zeros(num_channels)

        for c in range(num_channels):
            channel_data = pixels[:, c]
            hist, _ = np.histogram(channel_data, bins=bins, density=True)

            # Avoid log(0) by adding small epsilon
            hist = hist + 1e-10

            # Shannon entropy
            entropy = -np.sum(hist * np.log2(hist))
            entropies[c] = entropy

        return entropies

    def get_distribution(self,
                        image: np.ndarray,
                        channel: int = 0,
                        bins: int = 256,
                        normalized: bool = True) -> Tuple[np.ndarray, np.ndarray]:
        """
        Get histogram distribution for a specific channel.

        Parameters:
        ----------
        image : np.ndarray
            Input image
        channel : int
            Channel index
        bins : int
            Number of histogram bins
        normalized : bool
            Whether to normalize histogram (density)

        Returns:
        -------
        Tuple[np.ndarray, np.ndarray]
            (histogram, bin_edges)
        """
        if len(image.shape) == 2:
            channel_data = image.flatten()
        else:
            channel_data = image[:, :, channel].flatten()

        hist, bin_edges = np.histogram(
            channel_data,
            bins=bins,
            density=normalized
        )

        return hist, bin_edges

    def compare_stats(self,
                     stats1: ColorStatistics,
                     stats2: ColorStatistics) -> Dict[str, float]:
        """
        Compare two sets of color statistics.

        Parameters:
        ----------
        stats1 : ColorStatistics
            First statistics
        stats2 : ColorStatistics
            Second statistics

        Returns:
        -------
        Dict[str, float]
            Comparison metrics including:
            - mean_error: Euclidean distance between means
            - std_ratio: Ratio of standard deviations
            - kl_divergence: KL divergence (if histograms available)
        """
        metrics = {}

        # Mean error (Euclidean distance)
        metrics['mean_error'] = np.linalg.norm(stats1.mean - stats2.mean)

        # Standard deviation ratio
        metrics['std_ratio'] = np.mean(stats2.std / (stats1.std + 1e-10))

        # Variance ratio
        metrics['variance_ratio'] = np.mean(stats2.variance / (stats1.variance + 1e-10))

        # KL divergence (if histograms available)
        if stats1.histogram is not None and stats2.histogram is not None:
            kl_divs = []
            for c in stats1.histogram.keys():
                if c in stats2.histogram:
                    kl = self._kl_divergence(
                        stats1.histogram[c],
                        stats2.histogram[c]
                    )
                    kl_divs.append(kl)

            if kl_divs:
                metrics['kl_divergence'] = np.mean(kl_divs)

        # Entropy difference (if available)
        if stats1.entropy is not None and stats2.entropy is not None:
            metrics['entropy_diff'] = np.linalg.norm(stats1.entropy - stats2.entropy)

        return metrics

    def _kl_divergence(self, p: np.ndarray, q: np.ndarray) -> float:
        """
        Compute KL divergence: D_KL(P || Q) = Σ P(x) log(P(x) / Q(x))

        Parameters:
        ----------
        p : np.ndarray
            Probability distribution P
        q : np.ndarray
            Probability distribution Q

        Returns:
        -------
        float
            KL divergence
        """
        # Avoid division by zero and log(0)
        p = p + 1e-10
        q = q + 1e-10

        # Normalize
        p = p / np.sum(p)
        q = q / np.sum(q)

        # Compute KL divergence
        kl = np.sum(p * np.log(p / q))

        return kl

    def compute_delta_e(self,
                       image1: np.ndarray,
                       image2: np.ndarray,
                       method: str = 'cie76') -> float:
        """
        Compute perceptual color difference (ΔE).

        Parameters:
        ----------
        image1 : np.ndarray
            First image (assumed in Lab space)
        image2 : np.ndarray
            Second image (assumed in Lab space)
        method : str
            ΔE method: 'cie76', 'cie94', 'ciede2000' (simplified)

        Returns:
        -------
        float
            Average ΔE across all pixels
        """
        if image1.shape != image2.shape:
            raise ValueError("Images must have same shape")

        if method == 'cie76':
            # Simple Euclidean distance in Lab space
            delta_e = np.sqrt(np.sum((image1 - image2)**2, axis=2))
        else:
            # For now, fall back to CIE76
            # Full CIEDE2000 implementation is complex
            delta_e = np.sqrt(np.sum((image1 - image2)**2, axis=2))

        return np.mean(delta_e)

    def clear_cache(self):
        """Clear statistics cache."""
        self._stats_cache.clear()

    def get_cache_size(self) -> int:
        """Get number of cached statistics."""
        return len(self._stats_cache)


# Convenience function
def compute_image_stats(image: np.ndarray,
                       mask: Optional[np.ndarray] = None) -> ColorStatistics:
    """
    Convenience function to compute image statistics.

    Parameters:
    ----------
    image : np.ndarray
        Input image
    mask : Optional[np.ndarray]
        Region of interest mask

    Returns:
    -------
    ColorStatistics
        Computed statistics

    Example:
    -------
    >>> stats = compute_image_stats(image)
    >>> print(f"Mean: {stats.mean}, Std: {stats.std}")
    """
    engine = ColorStatisticsEngine()
    return engine.compute_stats(image, mask)
