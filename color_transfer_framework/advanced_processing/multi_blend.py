"""
Multi-Image Blender
===================

Blend color information from multiple source images.

Features:
- Multiple source image blending
- Weighted blending
- Statistical blending (mean, median, mode)
- Region-based blending
"""

import cv2
import numpy as np
from pathlib import Path
from typing import List, Optional, Union, Dict
import logging

from ..transfer_engine import TransferConfig
from ..interface_layer.orchestrator import TransferOrchestrator
from ..color_space_manager import ColorSpaceManager

logger = logging.getLogger(__name__)


class MultiBlender:
    """
    Blend color transfer from multiple source images.

    Example:
        >>> blender = MultiBlender()
        >>> result = blender.blend_transfer(
        ...     sources=["palette1.jpg", "palette2.jpg", "palette3.jpg"],
        ...     target="target.jpg",
        ...     weights=[0.5, 0.3, 0.2]
        ... )
    """

    def __init__(
        self,
        orchestrator: Optional[TransferOrchestrator] = None,
        color_manager: Optional[ColorSpaceManager] = None
    ):
        """
        Initialize multi-blender.

        Parameters:
        -----------
        orchestrator : TransferOrchestrator, optional
            Orchestrator instance to use
        color_manager : ColorSpaceManager, optional
            Color space manager instance
        """
        self.orchestrator = orchestrator or TransferOrchestrator()
        self.color_manager = color_manager or ColorSpaceManager()

    def blend_transfer(
        self,
        sources: List[str],
        target: str,
        weights: Optional[List[float]] = None,
        config: Optional[TransferConfig] = None,
        blend_mode: str = 'weighted'
    ) -> np.ndarray:
        """
        Apply color transfer from multiple sources and blend results.

        Parameters:
        -----------
        sources : List[str]
            List of source image paths
        target : str
            Target image path
        weights : List[float], optional
            Blending weights for each source (must sum to 1.0)
        config : TransferConfig, optional
            Transfer configuration
        blend_mode : str
            Blending mode ('weighted', 'mean', 'median', 'max', 'min')

        Returns:
        --------
        np.ndarray
            Blended result image
        """
        if not sources:
            raise ValueError("At least one source image required")

        # Validate and normalize weights
        if weights is None:
            weights = [1.0 / len(sources)] * len(sources)
        else:
            if len(weights) != len(sources):
                raise ValueError("Number of weights must match number of sources")
            weight_sum = sum(weights)
            if abs(weight_sum - 1.0) > 0.01:
                logger.warning(f"Weights sum to {weight_sum}, normalizing to 1.0")
                weights = [w / weight_sum for w in weights]

        # Load target image
        target_img = cv2.imread(target)
        if target_img is None:
            raise ValueError(f"Failed to load target image: {target}")

        # Apply transfer from each source
        results = []
        for source_path in sources:
            source_img = cv2.imread(source_path)
            if source_img is None:
                logger.warning(f"Failed to load source image: {source_path}, skipping")
                continue

            result = self.orchestrator.transfer(
                source_image=source_img,
                target_image=target_img,
                config=config,
                generate_diagnostics=False,
                interface_type="MULTI_BLEND"
            )
            results.append(result.result_image)

        if not results:
            raise ValueError("No valid results to blend")

        # Blend results
        if blend_mode == 'weighted':
            return self._blend_weighted(results, weights)
        elif blend_mode == 'mean':
            return self._blend_mean(results)
        elif blend_mode == 'median':
            return self._blend_median(results)
        elif blend_mode == 'max':
            return self._blend_max(results)
        elif blend_mode == 'min':
            return self._blend_min(results)
        else:
            raise ValueError(f"Unknown blend mode: {blend_mode}")

    def blend_statistics(
        self,
        sources: List[str],
        target: str,
        config: Optional[TransferConfig] = None,
        method: str = 'mean'
    ) -> np.ndarray:
        """
        Blend source images statistically before transfer.

        Instead of transferring from each source separately, this method
        combines the color statistics of all sources first.

        Parameters:
        -----------
        sources : List[str]
            List of source image paths
        target : str
            Target image path
        config : TransferConfig, optional
            Transfer configuration
        method : str
            Statistical method ('mean', 'median')

        Returns:
        --------
        np.ndarray
            Result image
        """
        if not sources:
            raise ValueError("At least one source image required")

        # Load target
        target_img = cv2.imread(target)
        if target_img is None:
            raise ValueError(f"Failed to load target: {target}")

        # Load all sources
        source_images = []
        for source_path in sources:
            img = cv2.imread(source_path)
            if img is not None:
                source_images.append(img)
            else:
                logger.warning(f"Failed to load source: {source_path}")

        if not source_images:
            raise ValueError("No valid source images loaded")

        # Create blended source
        if method == 'mean':
            blended_source = np.mean(source_images, axis=0).astype(np.uint8)
        elif method == 'median':
            blended_source = np.median(source_images, axis=0).astype(np.uint8)
        else:
            raise ValueError(f"Unknown method: {method}")

        # Apply transfer with blended source
        result = self.orchestrator.transfer(
            source_image=blended_source,
            target_image=target_img,
            config=config,
            generate_diagnostics=False,
            interface_type="MULTI_BLEND"
        )

        return result.result_image

    def _blend_weighted(
        self,
        images: List[np.ndarray],
        weights: List[float]
    ) -> np.ndarray:
        """Blend images with weights."""
        result = np.zeros_like(images[0], dtype=np.float32)

        for img, weight in zip(images, weights):
            result += img.astype(np.float32) * weight

        return np.clip(result, 0, 255).astype(np.uint8)

    def _blend_mean(self, images: List[np.ndarray]) -> np.ndarray:
        """Blend images using mean."""
        return np.mean(images, axis=0).astype(np.uint8)

    def _blend_median(self, images: List[np.ndarray]) -> np.ndarray:
        """Blend images using median."""
        return np.median(images, axis=0).astype(np.uint8)

    def _blend_max(self, images: List[np.ndarray]) -> np.ndarray:
        """Blend images using maximum."""
        return np.maximum.reduce(images).astype(np.uint8)

    def _blend_min(self, images: List[np.ndarray]) -> np.ndarray:
        """Blend images using minimum."""
        return np.minimum.reduce(images).astype(np.uint8)

    def region_blend(
        self,
        sources: List[str],
        target: str,
        regions: List[np.ndarray],
        config: Optional[TransferConfig] = None
    ) -> np.ndarray:
        """
        Blend different sources in different regions.

        Parameters:
        -----------
        sources : List[str]
            List of source image paths
        target : str
            Target image path
        regions : List[np.ndarray]
            List of binary masks defining regions for each source
        config : TransferConfig, optional
            Transfer configuration

        Returns:
        --------
        np.ndarray
            Blended result image
        """
        if len(sources) != len(regions):
            raise ValueError("Number of sources must match number of regions")

        target_img = cv2.imread(target)
        if target_img is None:
            raise ValueError(f"Failed to load target: {target}")

        result = target_img.copy()

        for source_path, region_mask in zip(sources, regions):
            source_img = cv2.imread(source_path)
            if source_img is None:
                logger.warning(f"Failed to load source: {source_path}")
                continue

            # Apply transfer
            transfer_result = self.orchestrator.transfer(
                source_image=source_img,
                target_image=target_img,
                config=config,
                mask=region_mask,
                generate_diagnostics=False,
                interface_type="MULTI_BLEND"
            )

            # Blend into result using mask
            mask_3ch = cv2.cvtColor(region_mask, cv2.COLOR_GRAY_BGR) if len(region_mask.shape) == 2 else region_mask
            mask_norm = mask_3ch.astype(np.float32) / 255.0

            result = (
                result.astype(np.float32) * (1 - mask_norm) +
                transfer_result.result_image.astype(np.float32) * mask_norm
            ).astype(np.uint8)

        return result
