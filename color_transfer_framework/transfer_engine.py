"""
TransferEngine Module
====================

Performs color transfer transformations between images.

Responsibilities:
- Execute core color transfer algorithms
- Support multiple transfer methods (Reinhard, LCH, RGB, Histogram)
- Handle blending and masking
- Batch processing
- Algorithm selection via Strategy pattern

Design Principles:
- Strategy Pattern: Different algorithms implement common interface
- Template Method: Common transfer pipeline
- Builder Pattern: Configuration building
"""

import numpy as np
import cv2
from typing import Optional, List, Dict, Tuple
from enum import Enum
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

from .color_space_manager import ColorSpaceManager, ColorSpace
from .color_statistics_engine import ColorStatisticsEngine, ColorStatistics


class TransferAlgorithm(Enum):
    """Supported transfer algorithms."""
    REINHARD_LAB = "reinhard_lab"
    REINHARD_LCH = "reinhard_lch"
    RGB_DIRECT = "rgb_direct"
    HISTOGRAM_MATCH = "histogram_match"


@dataclass
class TransferConfig:
    """
    Configuration for color transfer.

    Attributes:
    ----------
    algorithm : TransferAlgorithm
        Transfer algorithm to use
    blend_factor : float
        Blending with original [0, 1] (1 = full transfer)
    clip_output : bool
        Whether to clip output to valid range
    preserve_luminance : bool
        Whether to preserve original luminance (LCH only)
    epsilon : float
        Small constant to prevent division by zero
    color_space : ColorSpace
        Target color space for processing
    """
    algorithm: TransferAlgorithm = TransferAlgorithm.REINHARD_LAB
    blend_factor: float = 1.0
    clip_output: bool = True
    preserve_luminance: bool = False
    epsilon: float = 1e-10
    color_space: ColorSpace = ColorSpace.LAB
    metadata: Dict = field(default_factory=dict)

    def __post_init__(self):
        """Validate configuration."""
        if not 0.0 <= self.blend_factor <= 1.0:
            raise ValueError(f"blend_factor must be in [0, 1], got {self.blend_factor}")

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'algorithm': self.algorithm.value,
            'blend_factor': self.blend_factor,
            'clip_output': self.clip_output,
            'preserve_luminance': self.preserve_luminance,
            'epsilon': self.epsilon,
            'color_space': self.color_space.value,
            'metadata': self.metadata,
        }


class TransferAlgorithmBase(ABC):
    """
    Abstract base class for transfer algorithms.

    This defines the interface that all transfer algorithms must implement.
    Uses the Strategy pattern for algorithm interchangeability.
    """

    def __init__(self, config: TransferConfig):
        """
        Initialize algorithm.

        Parameters:
        ----------
        config : TransferConfig
            Algorithm configuration
        """
        self.config = config
        self.color_manager = ColorSpaceManager(precision='float32')
        self.stats_engine = ColorStatisticsEngine(cache_stats=True)

    @abstractmethod
    def transfer(self,
                source: np.ndarray,
                target: np.ndarray,
                source_stats: Optional[ColorStatistics] = None,
                target_stats: Optional[ColorStatistics] = None) -> np.ndarray:
        """
        Perform color transfer.

        Parameters:
        ----------
        source : np.ndarray
            Source image (BGR uint8)
        target : np.ndarray
            Target image (BGR uint8)
        source_stats : Optional[ColorStatistics]
            Pre-computed source statistics (for efficiency)
        target_stats : Optional[ColorStatistics]
            Pre-computed target statistics (for efficiency)

        Returns:
        -------
        np.ndarray
            Transferred image (BGR uint8)
        """
        pass

    def _prepare_images(self,
                       source: np.ndarray,
                       target: np.ndarray,
                       color_space: ColorSpace) -> Tuple[np.ndarray, np.ndarray]:
        """
        Prepare images for processing.

        Parameters:
        ----------
        source : np.ndarray
            Source image (BGR uint8)
        target : np.ndarray
            Target image (BGR uint8)
        color_space : ColorSpace
            Target color space

        Returns:
        -------
        Tuple[np.ndarray, np.ndarray]
            (source_converted, target_converted) in float32
        """
        source_float = self.color_manager.to_float(source)
        target_float = self.color_manager.to_float(target)

        source_converted = self.color_manager.convert_to(
            source_float, color_space, ColorSpace.BGR
        )
        target_converted = self.color_manager.convert_to(
            target_float, color_space, ColorSpace.BGR
        )

        return source_converted, target_converted

    def _finalize_output(self,
                        result: np.ndarray,
                        color_space: ColorSpace,
                        clip: bool = True) -> np.ndarray:
        """
        Convert result back to BGR uint8.

        Parameters:
        ----------
        result : np.ndarray
            Result in given color space (float32)
        color_space : ColorSpace
            Current color space
        clip : bool
            Whether to clip to valid range

        Returns:
        -------
        np.ndarray
            BGR uint8 image
        """
        # Convert back to BGR
        bgr_float = self.color_manager.convert_to(
            result, ColorSpace.BGR, color_space
        )

        # Clip if requested
        if clip:
            bgr_float = np.clip(bgr_float, 0, 1)

        # Convert to uint8
        return self.color_manager.to_uint8(bgr_float)


class ReinhardLabAlgorithm(TransferAlgorithmBase):
    """
    Reinhard et al. (2001) color transfer in Lab space.

    This is the classic statistical matching algorithm that preserves
    mean and variance in perceptually uniform Lab space.

    Algorithm:
    ---------
    For each channel c ∈ {L*, a*, b*}:
        T'_c = (σ_S,c / σ_T,c) × (T_c - μ_T,c) + μ_S,c

    Complexity: O(n) where n = number of pixels
    """

    def transfer(self,
                source: np.ndarray,
                target: np.ndarray,
                source_stats: Optional[ColorStatistics] = None,
                target_stats: Optional[ColorStatistics] = None) -> np.ndarray:
        """Transfer color using Reinhard Lab method."""

        # Convert to Lab
        source_lab, target_lab = self._prepare_images(
            source, target, ColorSpace.LAB
        )

        # Compute statistics if not provided
        if source_stats is None:
            source_stats = self.stats_engine.compute_stats(source_lab)
        if target_stats is None:
            target_stats = self.stats_engine.compute_stats(target_lab)

        # Compute scale factors
        scale = source_stats.std / (target_stats.std + self.config.epsilon)

        # Apply transformation using broadcasting
        # (h, w, 3) - (3,) broadcasts correctly
        result_lab = scale * (target_lab - target_stats.mean) + source_stats.mean

        # Convert back to BGR
        result = self._finalize_output(result_lab, ColorSpace.LAB, self.config.clip_output)

        return result


class ReinhardLCHAlgorithm(TransferAlgorithmBase):
    """
    Reinhard algorithm in cylindrical LCH space.

    LCH = Cylindrical representation of Lab:
    - L: Lightness (same as Lab)
    - C: Chroma = sqrt(a² + b²)
    - H: Hue = atan2(b, a)

    Advantages:
    ----------
    - Preserves hue more accurately (angular coordinate)
    - Better for artistic color grading
    - Can optionally preserve original luminance
    """

    def transfer(self,
                source: np.ndarray,
                target: np.ndarray,
                source_stats: Optional[ColorStatistics] = None,
                target_stats: Optional[ColorStatistics] = None) -> np.ndarray:
        """Transfer color using LCH method."""

        # Convert to LCH
        source_lch, target_lch = self._prepare_images(
            source, target, ColorSpace.LCH
        )

        # Compute statistics
        if source_stats is None:
            source_stats = self.stats_engine.compute_stats(source_lch)
        if target_stats is None:
            target_stats = self.stats_engine.compute_stats(target_lch)

        # Separate channels
        L_target, C_target, H_target = self.color_manager.separate_channels(target_lch)

        # Transfer L and C, preserve H
        scale_L = source_stats.std[0] / (target_stats.std[0] + self.config.epsilon)
        scale_C = source_stats.std[1] / (target_stats.std[1] + self.config.epsilon)

        if self.config.preserve_luminance:
            # Keep original luminance, only transfer chroma
            L_result = L_target
        else:
            # Transfer both luminance and chroma
            L_result = scale_L * (L_target - target_stats.mean[0]) + source_stats.mean[0]

        C_result = scale_C * (C_target - target_stats.mean[1]) + source_stats.mean[1]

        # Hue is preserved from target
        H_result = H_target

        # Merge channels
        result_lch = self.color_manager.merge_channels([L_result, C_result, H_result])

        # Convert back
        result = self._finalize_output(result_lch, ColorSpace.LCH, self.config.clip_output)

        return result


class RGBDirectAlgorithm(TransferAlgorithmBase):
    """
    Direct RGB color transfer (baseline).

    This method applies statistical matching directly in RGB space.
    NOT recommended for production use as RGB is not perceptually uniform.

    Use case: Baseline for comparison only.
    """

    def transfer(self,
                source: np.ndarray,
                target: np.ndarray,
                source_stats: Optional[ColorStatistics] = None,
                target_stats: Optional[ColorStatistics] = None) -> np.ndarray:
        """Transfer color in RGB space."""

        # Convert to RGB (float32)
        source_rgb = self.color_manager.to_float(source)
        target_rgb = self.color_manager.to_float(target)

        # Compute statistics
        if source_stats is None:
            source_stats = self.stats_engine.compute_stats(source_rgb)
        if target_stats is None:
            target_stats = self.stats_engine.compute_stats(target_rgb)

        # Apply transformation
        scale = source_stats.std / (target_stats.std + self.config.epsilon)
        result_rgb = scale * (target_rgb - target_stats.mean) + source_stats.mean

        # Clip and convert
        if self.config.clip_output:
            result_rgb = np.clip(result_rgb, 0, 1)

        return self.color_manager.to_uint8(result_rgb)


class HistogramMatchAlgorithm(TransferAlgorithmBase):
    """
    Histogram matching color transfer.

    This method matches the cumulative distribution function (CDF) of the
    target to the source for each channel independently.

    Algorithm:
    ---------
    1. Compute CDF of source and target
    2. For each target pixel value:
       - Find its position in target CDF
       - Map to corresponding value in source CDF

    Complexity: O(n + k) where k = number of bins
    """

    def transfer(self,
                source: np.ndarray,
                target: np.ndarray,
                source_stats: Optional[ColorStatistics] = None,
                target_stats: Optional[ColorStatistics] = None) -> np.ndarray:
        """Transfer color using histogram matching."""

        # Convert to Lab for perceptually uniform matching
        source_lab, target_lab = self._prepare_images(
            source, target, ColorSpace.LAB
        )

        # Separate channels
        source_channels = self.color_manager.separate_channels(source_lab)
        target_channels = self.color_manager.separate_channels(target_lab)

        # Match each channel independently
        result_channels = []
        for src_ch, tgt_ch in zip(source_channels, target_channels):
            matched_ch = self._match_histogram(src_ch, tgt_ch)
            result_channels.append(matched_ch)

        # Merge channels
        result_lab = self.color_manager.merge_channels(result_channels)

        # Convert back
        result = self._finalize_output(result_lab, ColorSpace.LAB, self.config.clip_output)

        return result

    def _match_histogram(self,
                        source: np.ndarray,
                        target: np.ndarray,
                        bins: int = 256) -> np.ndarray:
        """
        Match histogram of target to source.

        Parameters:
        ----------
        source : np.ndarray
            Source channel (2D array)
        target : np.ndarray
            Target channel (2D array)
        bins : int
            Number of histogram bins

        Returns:
        -------
        np.ndarray
            Target with matched histogram
        """
        # Flatten
        src_flat = source.flatten()
        tgt_flat = target.flatten()

        # Compute histograms
        src_hist, src_bins = np.histogram(src_flat, bins=bins, density=True)
        tgt_hist, tgt_bins = np.histogram(tgt_flat, bins=bins, density=True)

        # Compute CDFs
        src_cdf = np.cumsum(src_hist)
        src_cdf = src_cdf / src_cdf[-1]  # Normalize

        tgt_cdf = np.cumsum(tgt_hist)
        tgt_cdf = tgt_cdf / tgt_cdf[-1]

        # Create mapping using interpolation
        # For each target value, find its CDF position
        # Then map to source value with same CDF position
        tgt_bin_centers = (tgt_bins[:-1] + tgt_bins[1:]) / 2
        src_bin_centers = (src_bins[:-1] + src_bins[1:]) / 2

        # Interpolate to create mapping function
        mapping = np.interp(tgt_cdf, src_cdf, src_bin_centers)

        # Apply mapping to target
        tgt_bin_indices = np.digitize(tgt_flat, tgt_bins) - 1
        tgt_bin_indices = np.clip(tgt_bin_indices, 0, len(mapping) - 1)

        matched_flat = mapping[tgt_bin_indices]
        matched = matched_flat.reshape(target.shape)

        return matched


class TransferEngine:
    """
    Main color transfer engine.

    This class orchestrates the color transfer process, managing algorithm
    selection, configuration, and execution.

    Example:
    -------
    >>> engine = TransferEngine()
    >>> config = TransferConfig(algorithm=TransferAlgorithm.REINHARD_LAB)
    >>> result = engine.transfer(source, target, config)
    """

    # Algorithm registry
    ALGORITHMS = {
        TransferAlgorithm.REINHARD_LAB: ReinhardLabAlgorithm,
        TransferAlgorithm.REINHARD_LCH: ReinhardLCHAlgorithm,
        TransferAlgorithm.RGB_DIRECT: RGBDirectAlgorithm,
        TransferAlgorithm.HISTOGRAM_MATCH: HistogramMatchAlgorithm,
    }

    def __init__(self, default_config: Optional[TransferConfig] = None):
        """
        Initialize TransferEngine.

        Parameters:
        ----------
        default_config : Optional[TransferConfig]
            Default configuration (can be overridden per transfer)
        """
        self.default_config = default_config or TransferConfig()
        self.color_manager = ColorSpaceManager()
        self.stats_engine = ColorStatisticsEngine(cache_stats=True)

    def transfer(self,
                source: np.ndarray,
                target: np.ndarray,
                config: Optional[TransferConfig] = None) -> np.ndarray:
        """
        Perform color transfer.

        Parameters:
        ----------
        source : np.ndarray
            Source image (BGR uint8)
        target : np.ndarray
            Target image (BGR uint8)
        config : Optional[TransferConfig]
            Transfer configuration (uses default if None)

        Returns:
        -------
        np.ndarray
            Transferred image (BGR uint8)
        """
        cfg = config or self.default_config

        # Get algorithm instance
        algorithm_class = self.ALGORITHMS.get(cfg.algorithm)
        if algorithm_class is None:
            raise ValueError(f"Unknown algorithm: {cfg.algorithm}")

        algorithm = algorithm_class(cfg)

        # Perform transfer
        result = algorithm.transfer(source, target)

        # Apply blending if needed
        if cfg.blend_factor < 1.0:
            result = self._blend(target, result, cfg.blend_factor)

        return result

    def transfer_with_mask(self,
                          source: np.ndarray,
                          target: np.ndarray,
                          mask: np.ndarray,
                          config: Optional[TransferConfig] = None) -> np.ndarray:
        """
        Perform color transfer only in masked region.

        Parameters:
        ----------
        source : np.ndarray
            Source image (BGR uint8)
        target : np.ndarray
            Target image (BGR uint8)
        mask : np.ndarray
            Binary mask (uint8, 0 or 255)
        config : Optional[TransferConfig]
            Transfer configuration

        Returns:
        -------
        np.ndarray
            Transferred image (BGR uint8)
        """
        # Perform full transfer
        transferred = self.transfer(source, target, config)

        # Apply mask
        mask_3ch = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR) if len(mask.shape) == 2 else mask
        mask_normalized = mask_3ch.astype(np.float32) / 255.0

        # Blend using mask
        result = (transferred * mask_normalized + target * (1 - mask_normalized)).astype(np.uint8)

        return result

    def batch_transfer(self,
                      source: np.ndarray,
                      targets: List[np.ndarray],
                      config: Optional[TransferConfig] = None) -> List[np.ndarray]:
        """
        Transfer color from one source to multiple targets.

        Parameters:
        ----------
        source : np.ndarray
            Source image (BGR uint8)
        targets : List[np.ndarray]
            List of target images
        config : Optional[TransferConfig]
            Transfer configuration

        Returns:
        -------
        List[np.ndarray]
            List of transferred images

        Note:
        ----
        This method pre-computes source statistics once for efficiency.
        For GPU acceleration, use OptimizerEngine.
        """
        cfg = config or self.default_config

        # Pre-compute source statistics
        algorithm_class = self.ALGORITHMS[cfg.algorithm]
        algorithm = algorithm_class(cfg)

        # Convert source to appropriate color space
        source_converted = algorithm.color_manager.convert_to(
            algorithm.color_manager.to_float(source),
            cfg.color_space,
            ColorSpace.BGR
        )
        source_stats = self.stats_engine.compute_stats(source_converted)

        # Transfer to each target
        results = []
        for target in targets:
            result = algorithm.transfer(source, target, source_stats=source_stats)

            # Apply blending
            if cfg.blend_factor < 1.0:
                result = self._blend(target, result, cfg.blend_factor)

            results.append(result)

        return results

    def _blend(self,
              original: np.ndarray,
              transferred: np.ndarray,
              alpha: float) -> np.ndarray:
        """
        Blend original and transferred images.

        Parameters:
        ----------
        original : np.ndarray
            Original image (uint8)
        transferred : np.ndarray
            Transferred image (uint8)
        alpha : float
            Blending factor [0, 1] (0=original, 1=transferred)

        Returns:
        -------
        np.ndarray
            Blended image (uint8)
        """
        return cv2.addWeighted(original, 1 - alpha, transferred, alpha, 0)

    @classmethod
    def register_algorithm(cls,
                          algorithm_type: TransferAlgorithm,
                          algorithm_class: type):
        """
        Register a custom algorithm.

        Parameters:
        ----------
        algorithm_type : TransferAlgorithm
            Algorithm identifier
        algorithm_class : type
            Algorithm class (must inherit from TransferAlgorithmBase)
        """
        if not issubclass(algorithm_class, TransferAlgorithmBase):
            raise TypeError("Algorithm class must inherit from TransferAlgorithmBase")

        cls.ALGORITHMS[algorithm_type] = algorithm_class

    def get_available_algorithms(self) -> List[TransferAlgorithm]:
        """Get list of available algorithms."""
        return list(self.ALGORITHMS.keys())


# Convenience function
def transfer_color(source: np.ndarray,
                  target: np.ndarray,
                  algorithm: str = 'reinhard_lab',
                  blend_factor: float = 1.0) -> np.ndarray:
    """
    Convenience function for quick color transfer.

    Parameters:
    ----------
    source : np.ndarray
        Source image (BGR uint8)
    target : np.ndarray
        Target image (BGR uint8)
    algorithm : str
        Algorithm name ('reinhard_lab', 'reinhard_lch', 'rgb_direct', 'histogram_match')
    blend_factor : float
        Blending factor [0, 1]

    Returns:
    -------
    np.ndarray
        Transferred image (BGR uint8)

    Example:
    -------
    >>> result = transfer_color(source, target, algorithm='reinhard_lab')
    """
    config = TransferConfig(
        algorithm=TransferAlgorithm(algorithm),
        blend_factor=blend_factor
    )

    engine = TransferEngine()
    return engine.transfer(source, target, config)
