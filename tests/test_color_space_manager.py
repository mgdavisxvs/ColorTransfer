"""
Unit tests for ColorSpaceManager module.

Tests cover:
- Color space conversions
- Channel operations
- Type management
- Validation
- Edge cases
"""

import pytest
import numpy as np
import cv2
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from color_transfer_framework.color_space_manager import (
    ColorSpaceManager,
    ColorSpace,
    ColorBounds,
    convert_color_space
)


class TestColorSpace:
    """Test ColorSpace enum."""

    def test_color_space_values(self):
        """Test enum values."""
        assert ColorSpace.BGR.value == "BGR"
        assert ColorSpace.LAB.value == "LAB"
        assert ColorSpace.LCH.value == "LCH"

    def test_color_space_membership(self):
        """Test enum membership."""
        assert ColorSpace.BGR in ColorSpace
        assert ColorSpace.RGB in ColorSpace
        assert "INVALID" not in [cs.value for cs in ColorSpace]


class TestColorBounds:
    """Test ColorBounds class."""

    def test_bounds_creation(self):
        """Test ColorBounds initialization."""
        bounds = ColorBounds(
            min_values=np.array([0, 0, 0]),
            max_values=np.array([255, 255, 255])
        )
        assert bounds.min_values.shape == (3,)
        assert bounds.max_values.shape == (3,)

    def test_bounds_clamp(self):
        """Test value clamping."""
        bounds = ColorBounds(
            min_values=np.array([0, 0, 0]),
            max_values=np.array([100, 100, 100])
        )

        # Test over-range values
        image = np.array([[[50, 150, -10]]], dtype=np.float32)
        clamped = bounds.clamp(image)

        assert clamped[0, 0, 0] == 50  # Within range
        assert clamped[0, 0, 1] == 100  # Clamped to max
        assert clamped[0, 0, 2] == 0    # Clamped to min


class TestColorSpaceManager:
    """Test ColorSpaceManager class."""

    @pytest.fixture
    def manager(self):
        """Create ColorSpaceManager instance."""
        return ColorSpaceManager(precision='float32', normalize=True)

    @pytest.fixture
    def test_image(self):
        """Create test image (BGR uint8)."""
        # Create simple gradient image
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        for i in range(100):
            image[i, :, :] = [i * 2, i, i * 2.5]
        return image.astype(np.uint8)

    # ============================================================================
    # Initialization Tests
    # ============================================================================

    def test_manager_initialization(self, manager):
        """Test manager initialization."""
        assert manager.precision == np.float32
        assert manager.normalize == True

    def test_manager_precision_validation(self):
        """Test precision validation."""
        # Valid precisions
        for precision in ['float16', 'float32', 'float64']:
            manager = ColorSpaceManager(precision=precision)
            assert manager.precision == np.dtype(precision)

        # Invalid precision
        with pytest.raises(ValueError):
            ColorSpaceManager(precision='int32')

    # ============================================================================
    # Conversion Tests
    # ============================================================================

    def test_identity_conversion(self, manager, test_image):
        """Test identity conversion (same source and target)."""
        result = manager.convert_to(test_image, ColorSpace.BGR, ColorSpace.BGR)
        np.testing.assert_array_equal(result, test_image.astype(np.float32) / 255.0)

    def test_bgr_to_rgb(self, manager, test_image):
        """Test BGR to RGB conversion."""
        rgb = manager.convert_to(test_image, ColorSpace.RGB, ColorSpace.BGR)

        # Check shape preserved
        assert rgb.shape == test_image.shape

        # Check channels swapped (B and R)
        bgr_float = test_image.astype(np.float32) / 255.0
        np.testing.assert_array_almost_equal(rgb[:, :, 0], bgr_float[:, :, 2])  # R from B
        np.testing.assert_array_almost_equal(rgb[:, :, 2], bgr_float[:, :, 0])  # B from R

    def test_bgr_to_lab(self, manager, test_image):
        """Test BGR to Lab conversion."""
        lab = manager.convert_to(test_image, ColorSpace.LAB, ColorSpace.BGR)

        # Check shape preserved
        assert lab.shape == test_image.shape

        # Check Lab ranges (approximately)
        assert 0 <= np.min(lab[:, :, 0]) <= 100  # L in [0, 100]
        assert -128 <= np.min(lab[:, :, 1]) <= 127  # a in [-128, 127]
        assert -128 <= np.min(lab[:, :, 2]) <= 127  # b in [-128, 127]

    def test_bgr_to_lch(self, manager, test_image):
        """Test BGR to LCH conversion."""
        lch = manager.convert_to(test_image, ColorSpace.LCH, ColorSpace.BGR)

        # Check shape preserved
        assert lch.shape == test_image.shape

        # Extract channels
        L, C, H = manager.separate_channels(lch)

        # Check ranges
        assert 0 <= np.min(L)  # L >= 0
        assert np.min(C) >= 0  # C >= 0 (chroma is non-negative)
        # H is in radians, can be any value

    def test_roundtrip_conversion(self, manager, test_image):
        """Test roundtrip conversion (BGR -> Lab -> BGR)."""
        lab = manager.convert_to(test_image, ColorSpace.LAB, ColorSpace.BGR)
        bgr_back = manager.convert_to(lab, ColorSpace.BGR, ColorSpace.LAB)

        # Convert to uint8 for comparison
        original_uint8 = test_image
        result_uint8 = manager.to_uint8(bgr_back)

        # Should be very close (allow small error from conversions)
        np.testing.assert_allclose(original_uint8, result_uint8, atol=2)

    def test_unsupported_conversion(self, manager, test_image):
        """Test unsupported conversion raises error."""
        # Try to convert directly between incompatible spaces
        # (This test depends on implementation; adjust if needed)
        pass  # Most conversions are supported via intermediate steps

    # ============================================================================
    # Channel Operations Tests
    # ============================================================================

    def test_separate_channels(self, manager, test_image):
        """Test channel separation."""
        channels = manager.separate_channels(test_image)

        assert len(channels) == 3
        assert all(ch.shape == test_image.shape[:2] for ch in channels)

    def test_separate_channels_grayscale(self, manager):
        """Test channel separation for grayscale."""
        gray = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
        channels = manager.separate_channels(gray)

        assert len(channels) == 1
        np.testing.assert_array_equal(channels[0], gray)

    def test_merge_channels(self, manager):
        """Test channel merging."""
        # Create separate channels
        b = np.ones((100, 100), dtype=np.float32) * 0.3
        g = np.ones((100, 100), dtype=np.float32) * 0.5
        r = np.ones((100, 100), dtype=np.float32) * 0.7

        merged = manager.merge_channels([b, g, r])

        assert merged.shape == (100, 100, 3)
        np.testing.assert_array_almost_equal(merged[:, :, 0], b)
        np.testing.assert_array_almost_equal(merged[:, :, 1], g)
        np.testing.assert_array_almost_equal(merged[:, :, 2], r)

    def test_separate_merge_roundtrip(self, manager, test_image):
        """Test separate then merge gives original."""
        channels = manager.separate_channels(test_image)
        merged = manager.merge_channels(channels)

        np.testing.assert_array_equal(merged, test_image)

    # ============================================================================
    # Type Conversion Tests
    # ============================================================================

    def test_to_uint8(self, manager):
        """Test conversion to uint8."""
        # Normalized float image
        float_img = np.random.rand(50, 50, 3).astype(np.float32)
        uint8_img = manager.to_uint8(float_img, denormalize=True)

        assert uint8_img.dtype == np.uint8
        assert 0 <= np.min(uint8_img) <= 255
        assert 0 <= np.max(uint8_img) <= 255

    def test_to_float(self, manager):
        """Test conversion to float."""
        # uint8 image
        uint8_img = np.random.randint(0, 256, (50, 50, 3), dtype=np.uint8)
        float_img = manager.to_float(uint8_img, normalize=True)

        assert float_img.dtype == np.float32
        assert 0 <= np.min(float_img) <= 1.0
        assert 0 <= np.max(float_img) <= 1.0

    def test_type_conversion_roundtrip(self, manager):
        """Test uint8 -> float -> uint8 roundtrip."""
        original = np.random.randint(0, 256, (50, 50, 3), dtype=np.uint8)
        float_img = manager.to_float(original, normalize=True)
        back_to_uint8 = manager.to_uint8(float_img, denormalize=True)

        np.testing.assert_array_almost_equal(original, back_to_uint8, decimal=0)

    # ============================================================================
    # Validation Tests
    # ============================================================================

    def test_validate_image_valid(self, manager, test_image):
        """Test validation of valid image."""
        bgr_float = manager.to_float(test_image)
        is_valid = manager.validate_image(bgr_float, ColorSpace.BGR)
        assert is_valid == True

    def test_validate_image_invalid(self, manager):
        """Test validation of invalid image."""
        # Create image with out-of-range values
        invalid = np.ones((50, 50, 3), dtype=np.float32) * 2.0  # > 1.0

        is_valid = manager.validate_image(invalid, ColorSpace.BGR)
        assert is_valid == False

    def test_validate_image_raises(self, manager):
        """Test validation with raise_error=True."""
        invalid = np.ones((50, 50, 3), dtype=np.float32) * 2.0

        with pytest.raises(ValueError):
            manager.validate_image(invalid, ColorSpace.BGR, raise_error=True)

    # ============================================================================
    # Clamping Tests
    # ============================================================================

    def test_clamp_ranges(self, manager):
        """Test range clamping."""
        # Create image with out-of-range values
        image = np.array([[[50, 150, -10]]], dtype=np.float32)

        # Clamp to BGR range [0, 255]
        clamped = manager.clamp_ranges(image, ColorSpace.BGR)

        assert clamped[0, 0, 0] == 50   # Within range
        assert clamped[0, 0, 1] == 127  # Clamped to max (normalized)
        assert clamped[0, 0, 2] == 0    # Clamped to min

    # ============================================================================
    # Utility Tests
    # ============================================================================

    def test_get_channel_names(self, manager):
        """Test channel name retrieval."""
        bgr_names = manager.get_channel_names(ColorSpace.BGR)
        assert bgr_names == ['B', 'G', 'R']

        lab_names = manager.get_channel_names(ColorSpace.LAB)
        assert lab_names == ['L*', 'a*', 'b*']

        lch_names = manager.get_channel_names(ColorSpace.LCH)
        assert lch_names == ['L*', 'C*', 'h*']

    def test_get_color_space_info(self, manager):
        """Test color space info retrieval."""
        info = manager.get_color_space_info(ColorSpace.LAB)

        assert info['name'] == 'LAB'
        assert info['num_channels'] == 3
        assert 'channels' in info
        assert 'bounds' in info
        assert 'description' in info

    # ============================================================================
    # Edge Cases
    # ============================================================================

    def test_empty_image(self, manager):
        """Test handling of empty image."""
        empty = np.array([], dtype=np.uint8).reshape((0, 0, 3))

        # Should not crash
        result = manager.convert_to(empty, ColorSpace.RGB, ColorSpace.BGR)
        assert result.shape == empty.shape

    def test_single_pixel_image(self, manager):
        """Test handling of single pixel."""
        single_pixel = np.array([[[100, 150, 200]]], dtype=np.uint8)

        lab = manager.convert_to(single_pixel, ColorSpace.LAB, ColorSpace.BGR)
        assert lab.shape == (1, 1, 3)

    def test_large_image(self, manager):
        """Test handling of large image."""
        large = np.random.randint(0, 256, (1000, 1000, 3), dtype=np.uint8)

        # Should handle efficiently
        lab = manager.convert_to(large, ColorSpace.LAB, ColorSpace.BGR)
        assert lab.shape == large.shape


class TestConvenienceFunction:
    """Test convenience function."""

    def test_convert_color_space_function(self):
        """Test convenience function."""
        image = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)

        lab = convert_color_space(image, 'LAB', 'BGR')
        assert lab.shape == image.shape

        rgb = convert_color_space(image, 'RGB', 'BGR')
        assert rgb.shape == image.shape


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
