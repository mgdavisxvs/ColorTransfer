"""
ColorSpaceManager Module
========================

Handles all color space conversions and channel operations.

Responsibilities:
- Convert between color spaces (RGB ↔ Lab ↔ LCH ↔ HSV ↔ YCrCb)
- Manage channel separation and merging
- Ensure numeric precision and valid ranges
- Handle different data types (uint8, float32, float64)

Design Principles:
- Single Responsibility: Only handles color space operations
- Dependency Inversion: Depends on OpenCV/NumPy abstractions
- Open/Closed: Extensible for new color spaces via strategy pattern
"""

import numpy as np
import cv2
from typing import Tuple, Optional, Union, List
from enum import Enum
from dataclasses import dataclass


class ColorSpace(Enum):
    """Supported color spaces."""
    BGR = "BGR"
    RGB = "RGB"
    LAB = "LAB"
    LCH = "LCH"
    HSV = "HSV"
    YCrCb = "YCrCb"
    GRAY = "GRAY"


@dataclass
class ColorBounds:
    """Valid value ranges for each color space."""
    min_values: np.ndarray
    max_values: np.ndarray

    def clamp(self, image: np.ndarray) -> np.ndarray:
        """Clamp image values to valid range."""
        return np.clip(image, self.min_values, self.max_values)


class ColorSpaceManager:
    """
    Manages color space conversions and channel operations.

    This class provides a unified interface for all color space transformations,
    ensuring numerical precision and valid ranges throughout the pipeline.

    Example:
    -------
    >>> manager = ColorSpaceManager(precision='float32')
    >>> lab_image = manager.convert_to(bgr_image, ColorSpace.LAB)
    >>> channels = manager.separate_channels(lab_image)
    >>> merged = manager.merge_channels(channels)
    """

    # Define valid ranges for each color space
    COLOR_BOUNDS = {
        ColorSpace.BGR: ColorBounds(
            min_values=np.array([0, 0, 0]),
            max_values=np.array([255, 255, 255])
        ),
        ColorSpace.RGB: ColorBounds(
            min_values=np.array([0, 0, 0]),
            max_values=np.array([255, 255, 255])
        ),
        ColorSpace.LAB: ColorBounds(
            min_values=np.array([0, -128, -128]),
            max_values=np.array([100, 127, 127])
        ),
        ColorSpace.HSV: ColorBounds(
            min_values=np.array([0, 0, 0]),
            max_values=np.array([180, 255, 255])
        ),
        ColorSpace.YCrCb: ColorBounds(
            min_values=np.array([0, 0, 0]),
            max_values=np.array([255, 255, 255])
        ),
    }

    # OpenCV conversion codes
    CONVERSION_CODES = {
        (ColorSpace.BGR, ColorSpace.RGB): cv2.COLOR_BGR2RGB,
        (ColorSpace.BGR, ColorSpace.LAB): cv2.COLOR_BGR2LAB,
        (ColorSpace.BGR, ColorSpace.HSV): cv2.COLOR_BGR2HSV,
        (ColorSpace.BGR, ColorSpace.YCrCb): cv2.COLOR_BGR2YCrCb,
        (ColorSpace.BGR, ColorSpace.GRAY): cv2.COLOR_BGR2GRAY,

        (ColorSpace.RGB, ColorSpace.BGR): cv2.COLOR_RGB2BGR,
        (ColorSpace.RGB, ColorSpace.LAB): cv2.COLOR_RGB2LAB,
        (ColorSpace.RGB, ColorSpace.HSV): cv2.COLOR_RGB2HSV,

        (ColorSpace.LAB, ColorSpace.BGR): cv2.COLOR_LAB2BGR,
        (ColorSpace.LAB, ColorSpace.RGB): cv2.COLOR_LAB2RGB,

        (ColorSpace.HSV, ColorSpace.BGR): cv2.COLOR_HSV2BGR,
        (ColorSpace.HSV, ColorSpace.RGB): cv2.COLOR_HSV2RGB,

        (ColorSpace.YCrCb, ColorSpace.BGR): cv2.COLOR_YCrCb2BGR,

        (ColorSpace.GRAY, ColorSpace.BGR): cv2.COLOR_GRAY2BGR,
    }

    def __init__(self, precision: str = 'float32', normalize: bool = True):
        """
        Initialize ColorSpaceManager.

        Parameters:
        ----------
        precision : str
            Floating point precision: 'float16', 'float32', or 'float64'
        normalize : bool
            Whether to normalize images to [0, 1] for processing
        """
        self.precision = np.dtype(precision)
        self.normalize = normalize

        # Validate precision
        if self.precision not in [np.float16, np.float32, np.float64]:
            raise ValueError(f"Unsupported precision: {precision}")

    def convert_to(self,
                   image: np.ndarray,
                   target_space: ColorSpace,
                   source_space: ColorSpace = ColorSpace.BGR,
                   validate: bool = True) -> np.ndarray:
        """
        Convert image from source color space to target color space.

        Parameters:
        ----------
        image : np.ndarray
            Input image
        target_space : ColorSpace
            Target color space
        source_space : ColorSpace
            Source color space (default: BGR)
        validate : bool
            Whether to validate output range

        Returns:
        -------
        np.ndarray
            Converted image

        Raises:
        ------
        ValueError
            If conversion path is not supported
        """
        # Handle identity conversion
        if source_space == target_space:
            return image.copy()

        # Prepare image for conversion
        img = self._prepare_image(image)

        # Handle LCH conversion (not directly supported by OpenCV)
        if target_space == ColorSpace.LCH:
            return self._convert_to_lch(img, source_space)
        elif source_space == ColorSpace.LCH:
            return self._convert_from_lch(img, target_space)

        # Get conversion code
        conv_key = (source_space, target_space)
        if conv_key not in self.CONVERSION_CODES:
            raise ValueError(f"Unsupported conversion: {source_space} → {target_space}")

        # Perform conversion
        converted = cv2.cvtColor(img, self.CONVERSION_CODES[conv_key])

        # Validate and clamp if requested
        if validate and target_space in self.COLOR_BOUNDS:
            converted = self.COLOR_BOUNDS[target_space].clamp(converted)

        return converted

    def _prepare_image(self, image: np.ndarray) -> np.ndarray:
        """Prepare image for conversion (normalize and set dtype)."""
        img = image.astype(self.precision, copy=True)

        if self.normalize and img.max() > 1.0:
            img = img / 255.0

        return img

    def _convert_to_lch(self,
                       image: np.ndarray,
                       source_space: ColorSpace) -> np.ndarray:
        """
        Convert to LCH (Cylindrical Lab).

        LCH representation:
        - L: Lightness (same as Lab)
        - C: Chroma = sqrt(a² + b²)
        - H: Hue = atan2(b, a)
        """
        # First convert to Lab
        if source_space != ColorSpace.LAB:
            lab = self.convert_to(image, ColorSpace.LAB, source_space)
        else:
            lab = image.copy()

        # Extract Lab channels
        L, a, b = self.separate_channels(lab)

        # Compute LCH
        C = np.sqrt(a**2 + b**2)
        H = np.arctan2(b, a)

        # Merge LCH
        lch = self.merge_channels([L, C, H])

        return lch

    def _convert_from_lch(self,
                         lch_image: np.ndarray,
                         target_space: ColorSpace) -> np.ndarray:
        """
        Convert from LCH to target color space.
        """
        # Extract LCH channels
        L, C, H = self.separate_channels(lch_image)

        # Convert to Lab
        a = C * np.cos(H)
        b = C * np.sin(H)

        lab = self.merge_channels([L, a, b])

        # Convert from Lab to target
        if target_space != ColorSpace.LAB:
            return self.convert_to(lab, target_space, ColorSpace.LAB)
        else:
            return lab

    def separate_channels(self, image: np.ndarray) -> List[np.ndarray]:
        """
        Separate image into individual channels.

        Parameters:
        ----------
        image : np.ndarray
            Multi-channel image

        Returns:
        -------
        List[np.ndarray]
            List of individual channel arrays
        """
        if len(image.shape) == 2:
            # Grayscale image
            return [image]
        elif len(image.shape) == 3:
            # Multi-channel image
            return cv2.split(image)
        else:
            raise ValueError(f"Unsupported image shape: {image.shape}")

    def merge_channels(self, channels: List[np.ndarray]) -> np.ndarray:
        """
        Merge individual channels into multi-channel image.

        Parameters:
        ----------
        channels : List[np.ndarray]
            List of individual channel arrays

        Returns:
        -------
        np.ndarray
            Merged multi-channel image
        """
        if len(channels) == 1:
            return channels[0]
        else:
            return cv2.merge(channels)

    def clamp_ranges(self,
                    image: np.ndarray,
                    color_space: ColorSpace,
                    bounds: Optional[ColorBounds] = None) -> np.ndarray:
        """
        Clamp image values to valid range for given color space.

        Parameters:
        ----------
        image : np.ndarray
            Image to clamp
        color_space : ColorSpace
            Color space of image
        bounds : Optional[ColorBounds]
            Custom bounds (if None, use default for color space)

        Returns:
        -------
        np.ndarray
            Clamped image
        """
        if bounds is None:
            if color_space not in self.COLOR_BOUNDS:
                # No default bounds, return as-is
                return image
            bounds = self.COLOR_BOUNDS[color_space]

        return bounds.clamp(image)

    def to_uint8(self, image: np.ndarray, denormalize: bool = True) -> np.ndarray:
        """
        Convert image to uint8 format.

        Parameters:
        ----------
        image : np.ndarray
            Image to convert
        denormalize : bool
            Whether to denormalize from [0, 1] to [0, 255]

        Returns:
        -------
        np.ndarray
            uint8 image
        """
        img = image.copy()

        if denormalize and img.max() <= 1.0:
            img = img * 255.0

        img = np.clip(img, 0, 255)
        return img.astype(np.uint8)

    def to_float(self,
                image: np.ndarray,
                normalize: bool = True,
                precision: Optional[str] = None) -> np.ndarray:
        """
        Convert image to floating point format.

        Parameters:
        ----------
        image : np.ndarray
            Image to convert
        normalize : bool
            Whether to normalize to [0, 1]
        precision : Optional[str]
            Float precision (if None, use self.precision)

        Returns:
        -------
        np.ndarray
            Float image
        """
        dtype = np.dtype(precision) if precision else self.precision
        img = image.astype(dtype, copy=True)

        if normalize and img.max() > 1.0:
            img = img / 255.0

        return img

    def validate_image(self,
                      image: np.ndarray,
                      color_space: ColorSpace,
                      raise_error: bool = False) -> bool:
        """
        Validate that image values are within valid range for color space.

        Parameters:
        ----------
        image : np.ndarray
            Image to validate
        color_space : ColorSpace
            Color space of image
        raise_error : bool
            Whether to raise ValueError if invalid

        Returns:
        -------
        bool
            True if valid, False otherwise

        Raises:
        ------
        ValueError
            If raise_error=True and image is invalid
        """
        if color_space not in self.COLOR_BOUNDS:
            # No bounds defined, consider valid
            return True

        bounds = self.COLOR_BOUNDS[color_space]

        # Check min values
        if np.any(image < bounds.min_values):
            if raise_error:
                raise ValueError(f"Image contains values below minimum for {color_space}")
            return False

        # Check max values
        if np.any(image > bounds.max_values):
            if raise_error:
                raise ValueError(f"Image contains values above maximum for {color_space}")
            return False

        return True

    def get_channel_names(self, color_space: ColorSpace) -> List[str]:
        """
        Get channel names for given color space.

        Parameters:
        ----------
        color_space : ColorSpace
            Color space

        Returns:
        -------
        List[str]
            Channel names
        """
        channel_names = {
            ColorSpace.BGR: ['B', 'G', 'R'],
            ColorSpace.RGB: ['R', 'G', 'B'],
            ColorSpace.LAB: ['L*', 'a*', 'b*'],
            ColorSpace.LCH: ['L*', 'C*', 'h*'],
            ColorSpace.HSV: ['H', 'S', 'V'],
            ColorSpace.YCrCb: ['Y', 'Cr', 'Cb'],
            ColorSpace.GRAY: ['Gray'],
        }

        return channel_names.get(color_space, [f'Ch{i}' for i in range(3)])

    def get_color_space_info(self, color_space: ColorSpace) -> dict:
        """
        Get comprehensive information about a color space.

        Parameters:
        ----------
        color_space : ColorSpace
            Color space

        Returns:
        -------
        dict
            Information including channels, bounds, description
        """
        descriptions = {
            ColorSpace.BGR: "Blue-Green-Red color space (OpenCV default)",
            ColorSpace.RGB: "Red-Green-Blue color space (standard)",
            ColorSpace.LAB: "Perceptually uniform L*a*b* color space (CIELAB)",
            ColorSpace.LCH: "Cylindrical L*C*h* representation of Lab",
            ColorSpace.HSV: "Hue-Saturation-Value color space",
            ColorSpace.YCrCb: "Luma-Chroma color space (Y'CbCr)",
            ColorSpace.GRAY: "Grayscale (single channel)",
        }

        return {
            'name': color_space.value,
            'channels': self.get_channel_names(color_space),
            'bounds': self.COLOR_BOUNDS.get(color_space),
            'description': descriptions.get(color_space, "Unknown"),
            'num_channels': len(self.get_channel_names(color_space)),
        }


# Convenience function for quick conversions
def convert_color_space(image: np.ndarray,
                       target: str,
                       source: str = 'BGR') -> np.ndarray:
    """
    Convenience function for quick color space conversion.

    Parameters:
    ----------
    image : np.ndarray
        Input image
    target : str
        Target color space name (e.g., 'LAB', 'HSV')
    source : str
        Source color space name (default: 'BGR')

    Returns:
    -------
    np.ndarray
        Converted image

    Example:
    -------
    >>> lab_img = convert_color_space(bgr_img, 'LAB')
    """
    manager = ColorSpaceManager()
    return manager.convert_to(
        image,
        ColorSpace[target],
        ColorSpace[source]
    )
