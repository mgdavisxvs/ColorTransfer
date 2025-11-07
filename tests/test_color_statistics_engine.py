"""
Unit tests for ColorStatisticsEngine module.

Tests cover:
- Statistics computation
- Histogram analysis
- Comparison metrics
- Caching
- Edge cases
"""

import pytest
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from color_transfer_framework.color_statistics_engine import (
    ColorStatisticsEngine,
    ColorStatistics,
    StatisticType,
    compute_image_stats
)


class TestColorStatistics:
    """Test ColorStatistics dataclass."""

    def test_statistics_creation(self):
        """Test creating ColorStatistics."""
        stats = ColorStatistics(
            mean=np.array([0.5, 0.6, 0.7]),
            std=np.array([0.1, 0.15, 0.2]),
            variance=np.array([0.01, 0.0225, 0.04]),
            num_pixels=10000,
            num_channels=3
        )

        assert stats.num_pixels == 10000
        assert stats.num_channels == 3
        np.testing.assert_array_equal(stats.mean, [0.5, 0.6, 0.7])

    def test_statistics_repr(self):
        """Test __repr__ method."""
        stats = ColorStatistics(
            mean=np.array([0.5]),
            std=np.array([0.1]),
            variance=np.array([0.01]),
            num_pixels=100,
            num_channels=1
        )

        repr_str = repr(stats)
        assert 'ColorStatistics' in repr_str
        assert 'pixels=100' in repr_str

    def test_statistics_summary(self):
        """Test summary generation."""
        stats = ColorStatistics(
            mean=np.array([0.5, 0.6]),
            std=np.array([0.1, 0.15]),
            variance=np.array([0.01, 0.0225]),
            num_pixels=1000,
            num_channels=2
        )

        summary = stats.summary()
        assert 'Color Statistics Summary' in summary
        assert 'Pixels: 1,000' in summary
        assert 'Channels: 2' in summary


class TestColorStatisticsEngine:
    """Test ColorStatisticsEngine class."""

    @pytest.fixture
    def engine(self):
        """Create ColorStatisticsEngine instance."""
        return ColorStatisticsEngine(cache_stats=True)

    @pytest.fixture
    def test_image(self):
        """Create test image with known statistics."""
        # Create image with known mean and std
        image = np.random.randn(100, 100, 3).astype(np.float32)
        image = (image - image.mean()) / image.std() * 0.1 + 0.5  # Normalize
        image = np.clip(image, 0, 1)
        return image

    @pytest.fixture
    def constant_image(self):
        """Create constant image (zero variance)."""
        return np.ones((50, 50, 3), dtype=np.float32) * 0.5

    # ============================================================================
    # Initialization Tests
    # ============================================================================

    def test_engine_initialization(self, engine):
        """Test engine initialization."""
        assert engine.cache_stats == True
        assert len(engine._stats_cache) == 0

    def test_engine_no_cache(self):
        """Test engine without caching."""
        engine = ColorStatisticsEngine(cache_stats=False)
        assert engine.cache_stats == False

    # ============================================================================
    # Basic Statistics Tests
    # ============================================================================

    def test_compute_stats_basic(self, engine, test_image):
        """Test basic statistics computation."""
        stats = engine.compute_stats(test_image)

        # Check structure
        assert isinstance(stats, ColorStatistics)
        assert stats.num_channels == 3
        assert stats.num_pixels == 100 * 100

        # Check statistics shapes
        assert stats.mean.shape == (3,)
        assert stats.std.shape == (3,)
        assert stats.variance.shape == (3,)

    def test_compute_stats_grayscale(self, engine):
        """Test statistics for grayscale image."""
        gray = np.random.rand(100, 100).astype(np.float32)
        stats = engine.compute_stats(gray)

        assert stats.num_channels == 1
        assert stats.mean.shape == (1,)

    def test_compute_stats_known_values(self, engine):
        """Test statistics with known values."""
        # Create image with known statistics
        image = np.ones((100, 100, 3), dtype=np.float32)
        image[:, :, 0] = 0.3  # Channel 0: constant 0.3
        image[:, :, 1] = 0.5  # Channel 1: constant 0.5
        image[:, :, 2] = 0.7  # Channel 2: constant 0.7

        stats = engine.compute_stats(image)

        # Mean should match
        np.testing.assert_array_almost_equal(stats.mean, [0.3, 0.5, 0.7])

        # Std should be zero (constant images)
        np.testing.assert_array_almost_equal(stats.std, [0, 0, 0], decimal=10)

    # ============================================================================
    # Comprehensive Statistics Tests
    # ============================================================================

    def test_compute_stats_comprehensive(self, engine, test_image):
        """Test comprehensive statistics computation."""
        stats = engine.compute_stats(test_image, compute_all=True)

        # Check all statistics are computed
        assert stats.median is not None
        assert stats.histogram is not None
        assert stats.covariance is not None
        assert stats.entropy is not None

        # Check shapes
        assert stats.median.shape == (3,)
        assert len(stats.histogram) == 3  # One per channel
        assert stats.covariance.shape == (3, 3)
        assert stats.entropy.shape == (3,)

    def test_histogram_computation(self, engine, test_image):
        """Test histogram computation."""
        stats = engine.compute_stats(test_image, compute_all=True)

        # Check histogram structure
        assert 0 in stats.histogram  # Channel 0
        assert 1 in stats.histogram  # Channel 1
        assert 2 in stats.histogram  # Channel 2

        # Check histogram properties
        for hist in stats.histogram.values():
            assert len(hist) == 256  # Default bins
            assert hist.sum() > 0   # Non-empty

    def test_entropy_computation(self, engine, test_image):
        """Test entropy computation."""
        stats = engine.compute_stats(test_image, compute_all=True)

        # Entropy should be positive
        assert np.all(stats.entropy > 0)

        # Entropy should be reasonable (typically 5-10 bits for natural images)
        assert np.all(stats.entropy < 15)

    def test_covariance_computation(self, engine, test_image):
        """Test covariance matrix computation."""
        stats = engine.compute_stats(test_image, compute_all=True)

        # Covariance should be symmetric
        np.testing.assert_array_almost_equal(
            stats.covariance,
            stats.covariance.T
        )

        # Diagonal should be variances
        np.testing.assert_array_almost_equal(
            np.diag(stats.covariance),
            stats.variance
        )

    # ============================================================================
    # Masked Statistics Tests
    # ============================================================================

    def test_compute_stats_with_mask(self, engine, test_image):
        """Test statistics with mask."""
        # Create mask (top half only)
        mask = np.zeros((100, 100), dtype=np.uint8)
        mask[:50, :] = 255

        stats = engine.compute_stats(test_image, mask=mask)

        # Should compute stats only for masked region
        assert stats.num_pixels == 50 * 100  # Half the pixels

    def test_masked_vs_unmasked(self, engine, test_image):
        """Test masked vs unmasked statistics differ."""
        # Full image stats
        stats_full = engine.compute_stats(test_image)

        # Masked stats (top half)
        mask = np.zeros((100, 100), dtype=np.uint8)
        mask[:50, :] = 255
        stats_masked = engine.compute_stats(test_image, mask=mask)

        # Means should differ (unless image is perfectly uniform)
        assert not np.allclose(stats_full.mean, stats_masked.mean)

    # ============================================================================
    # Caching Tests
    # ============================================================================

    def test_caching_enabled(self, engine, test_image):
        """Test caching works."""
        # First computation
        stats1 = engine.compute_stats(test_image)
        cache_size_after_first = engine.get_cache_size()

        # Second computation (should hit cache)
        stats2 = engine.compute_stats(test_image)
        cache_size_after_second = engine.get_cache_size()

        # Cache size should remain same (hit)
        assert cache_size_after_first == cache_size_after_second
        assert cache_size_after_first == 1

        # Stats should be identical (same object)
        assert stats1 is stats2

    def test_caching_disabled(self):
        """Test caching can be disabled."""
        engine = ColorStatisticsEngine(cache_stats=False)
        image = np.random.rand(50, 50, 3).astype(np.float32)

        stats1 = engine.compute_stats(image)
        stats2 = engine.compute_stats(image)

        # Should not be same object
        assert stats1 is not stats2

        # But should have same values
        np.testing.assert_array_equal(stats1.mean, stats2.mean)

    def test_clear_cache(self, engine, test_image):
        """Test cache clearing."""
        engine.compute_stats(test_image)
        assert engine.get_cache_size() == 1

        engine.clear_cache()
        assert engine.get_cache_size() == 0

    # ============================================================================
    # Distribution Tests
    # ============================================================================

    def test_get_distribution(self, engine, test_image):
        """Test getting distribution for channel."""
        hist, bins = engine.get_distribution(test_image, channel=0)

        assert len(hist) == 256  # Default bins
        assert len(bins) == 257  # Bin edges (n+1)
        assert hist.sum() > 0

    def test_get_distribution_normalized(self, engine, test_image):
        """Test normalized distribution."""
        hist, bins = engine.get_distribution(test_image, channel=0, normalized=True)

        # Should be normalized (density)
        # Note: For density, integral = sum(hist) * bin_width ≈ 1
        bin_width = bins[1] - bins[0]
        integral = np.sum(hist) * bin_width
        np.testing.assert_almost_equal(integral, 1.0, decimal=1)

    # ============================================================================
    # Comparison Tests
    # ============================================================================

    def test_compare_stats_same_image(self, engine, test_image):
        """Test comparing identical images."""
        stats1 = engine.compute_stats(test_image)
        stats2 = engine.compute_stats(test_image)

        comparison = engine.compare_stats(stats1, stats2)

        # Should be identical
        np.testing.assert_almost_equal(comparison['mean_error'], 0.0, decimal=10)
        np.testing.assert_almost_equal(comparison['std_ratio'], 1.0, decimal=10)

    def test_compare_stats_different_images(self, engine):
        """Test comparing different images."""
        image1 = np.random.rand(100, 100, 3).astype(np.float32) * 0.5
        image2 = np.random.rand(100, 100, 3).astype(np.float32) * 0.8

        stats1 = engine.compute_stats(image1)
        stats2 = engine.compute_stats(image2)

        comparison = engine.compare_stats(stats1, stats2)

        # Should have measurable differences
        assert comparison['mean_error'] > 0
        assert comparison['std_ratio'] != 1.0

    def test_compare_stats_with_histograms(self, engine):
        """Test comparison with histogram-based metrics."""
        image1 = np.random.rand(100, 100, 3).astype(np.float32)
        image2 = np.random.rand(100, 100, 3).astype(np.float32)

        stats1 = engine.compute_stats(image1, compute_all=True)
        stats2 = engine.compute_stats(image2, compute_all=True)

        comparison = engine.compare_stats(stats1, stats2)

        # Should include KL divergence
        assert 'kl_divergence' in comparison
        assert comparison['kl_divergence'] >= 0

    # ============================================================================
    # Delta E Tests
    # ============================================================================

    def test_compute_delta_e_identical(self, engine):
        """Test ΔE for identical images."""
        image = np.random.rand(50, 50, 3).astype(np.float32)

        delta_e = engine.compute_delta_e(image, image)

        # Should be zero
        np.testing.assert_almost_equal(delta_e, 0.0, decimal=10)

    def test_compute_delta_e_different(self, engine):
        """Test ΔE for different images."""
        image1 = np.random.rand(50, 50, 3).astype(np.float32) * 0.3
        image2 = np.random.rand(50, 50, 3).astype(np.float32) * 0.7

        delta_e = engine.compute_delta_e(image1, image2)

        # Should be non-zero
        assert delta_e > 0

    def test_compute_delta_e_shape_mismatch(self, engine):
        """Test ΔE with mismatched shapes."""
        image1 = np.random.rand(50, 50, 3).astype(np.float32)
        image2 = np.random.rand(100, 100, 3).astype(np.float32)

        with pytest.raises(ValueError):
            engine.compute_delta_e(image1, image2)

    # ============================================================================
    # Edge Cases
    # ============================================================================

    def test_constant_image_statistics(self, engine, constant_image):
        """Test statistics for constant image."""
        stats = engine.compute_stats(constant_image)

        # Mean should be 0.5
        np.testing.assert_array_almost_equal(stats.mean, [0.5, 0.5, 0.5])

        # Std should be zero
        np.testing.assert_array_almost_equal(stats.std, [0, 0, 0], decimal=10)

    def test_single_pixel_image(self, engine):
        """Test statistics for single pixel."""
        single_pixel = np.array([[[0.5, 0.6, 0.7]]], dtype=np.float32)

        stats = engine.compute_stats(single_pixel)

        np.testing.assert_array_almost_equal(stats.mean, [0.5, 0.6, 0.7])
        np.testing.assert_array_almost_equal(stats.std, [0, 0, 0])

    def test_empty_mask(self, engine, test_image):
        """Test with empty mask (no pixels selected)."""
        # Create all-zero mask
        mask = np.zeros((100, 100), dtype=np.uint8)

        stats = engine.compute_stats(test_image, mask=mask)

        # Should have zero pixels
        assert stats.num_pixels == 0

    def test_extreme_values(self, engine):
        """Test with extreme values."""
        # Image with very large values
        image = np.ones((50, 50, 3), dtype=np.float32) * 1000

        stats = engine.compute_stats(image)

        # Should handle gracefully
        np.testing.assert_array_almost_equal(stats.mean, [1000, 1000, 1000])


class TestConvenienceFunction:
    """Test convenience function."""

    def test_compute_image_stats_function(self):
        """Test convenience function."""
        image = np.random.rand(100, 100, 3).astype(np.float32)

        stats = compute_image_stats(image)

        assert isinstance(stats, ColorStatistics)
        assert stats.num_channels == 3
        assert stats.num_pixels == 100 * 100

    def test_compute_image_stats_with_mask(self):
        """Test convenience function with mask."""
        image = np.random.rand(100, 100, 3).astype(np.float32)
        mask = np.ones((100, 100), dtype=np.uint8)
        mask[50:, :] = 0

        stats = compute_image_stats(image, mask=mask)

        assert stats.num_pixels == 50 * 100


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
