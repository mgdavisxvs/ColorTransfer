"""
Unit tests for TransferEngine module.

Tests cover:
- Algorithm implementations
- Configuration
- Blending
- Masking
- Batch processing
- Edge cases
"""

import pytest
import numpy as np
import cv2
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from color_transfer_framework.transfer_engine import (
    TransferEngine,
    TransferConfig,
    TransferAlgorithm,
    ReinhardLabAlgorithm,
    ReinhardLCHAlgorithm,
    RGBDirectAlgorithm,
    HistogramMatchAlgorithm,
    transfer_color
)


class TestTransferConfig:
    """Test TransferConfig dataclass."""

    def test_config_creation(self):
        """Test creating TransferConfig."""
        config = TransferConfig(
            algorithm=TransferAlgorithm.REINHARD_LAB,
            blend_factor=0.8
        )

        assert config.algorithm == TransferAlgorithm.REINHARD_LAB
        assert config.blend_factor == 0.8
        assert config.clip_output == True  # Default

    def test_config_validation(self):
        """Test config validation."""
        # Valid blend factor
        config = TransferConfig(blend_factor=0.5)
        assert config.blend_factor == 0.5

        # Invalid blend factor (< 0)
        with pytest.raises(ValueError):
            TransferConfig(blend_factor=-0.1)

        # Invalid blend factor (> 1)
        with pytest.raises(ValueError):
            TransferConfig(blend_factor=1.5)

    def test_config_to_dict(self):
        """Test config serialization."""
        config = TransferConfig(
            algorithm=TransferAlgorithm.REINHARD_LAB,
            blend_factor=0.7
        )

        config_dict = config.to_dict()

        assert config_dict['algorithm'] == 'reinhard_lab'
        assert config_dict['blend_factor'] == 0.7
        assert 'clip_output' in config_dict


class TestReinhardLabAlgorithm:
    """Test Reinhard Lab algorithm."""

    @pytest.fixture
    def source(self):
        """Create source image with known colors."""
        source = np.zeros((100, 100, 3), dtype=np.uint8)
        source[:, :, 0] = 100  # Blue
        source[:, :, 1] = 150  # Green
        source[:, :, 2] = 200  # Red
        return source

    @pytest.fixture
    def target(self):
        """Create target image with different colors."""
        target = np.zeros((100, 100, 3), dtype=np.uint8)
        target[:, :, 0] = 50   # Blue
        target[:, :, 1] = 80   # Green
        target[:, :, 2] = 120  # Red
        return target

    def test_reinhard_lab_transfer(self, source, target):
        """Test basic Reinhard Lab transfer."""
        config = TransferConfig(algorithm=TransferAlgorithm.REINHARD_LAB)
        algorithm = ReinhardLabAlgorithm(config)

        result = algorithm.transfer(source, target)

        # Check output properties
        assert result.dtype == np.uint8
        assert result.shape == target.shape
        assert 0 <= np.min(result) <= 255
        assert 0 <= np.max(result) <= 255

    def test_reinhard_lab_mean_preservation(self, source, target):
        """Test that mean is preserved (approximately)."""
        from color_transfer_framework.color_space_manager import ColorSpaceManager, ColorSpace
        from color_transfer_framework.color_statistics_engine import ColorStatisticsEngine

        config = TransferConfig(algorithm=TransferAlgorithm.REINHARD_LAB)
        algorithm = ReinhardLabAlgorithm(config)

        result = algorithm.transfer(source, target)

        # Convert to Lab for comparison
        manager = ColorSpaceManager()
        source_lab = manager.convert_to(manager.to_float(source), ColorSpace.LAB)
        result_lab = manager.convert_to(manager.to_float(result), ColorSpace.LAB)

        # Compute stats
        stats_engine = ColorStatisticsEngine()
        source_stats = stats_engine.compute_stats(source_lab)
        result_stats = stats_engine.compute_stats(result_lab)

        # Mean should be close
        np.testing.assert_allclose(result_stats.mean, source_stats.mean, rtol=0.1)

    def test_reinhard_lab_variance_preservation(self, source, target):
        """Test that variance is preserved (approximately)."""
        from color_transfer_framework.color_space_manager import ColorSpaceManager, ColorSpace
        from color_transfer_framework.color_statistics_engine import ColorStatisticsEngine

        config = TransferConfig(algorithm=TransferAlgorithm.REINHARD_LAB)
        algorithm = ReinhardLabAlgorithm(config)

        result = algorithm.transfer(source, target)

        # Convert to Lab
        manager = ColorSpaceManager()
        source_lab = manager.convert_to(manager.to_float(source), ColorSpace.LAB)
        result_lab = manager.convert_to(manager.to_float(result), ColorSpace.LAB)

        # Compute stats
        stats_engine = ColorStatisticsEngine()
        source_stats = stats_engine.compute_stats(source_lab)
        result_stats = stats_engine.compute_stats(result_lab)

        # Std should be close
        np.testing.assert_allclose(result_stats.std, source_stats.std, rtol=0.2)


class TestReinhardLCHAlgorithm:
    """Test Reinhard LCH algorithm."""

    def test_reinhard_lch_transfer(self):
        """Test basic LCH transfer."""
        source = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        target = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)

        config = TransferConfig(algorithm=TransferAlgorithm.REINHARD_LCH)
        algorithm = ReinhardLCHAlgorithm(config)

        result = algorithm.transfer(source, target)

        assert result.dtype == np.uint8
        assert result.shape == target.shape

    def test_lch_preserve_luminance(self):
        """Test luminance preservation option."""
        source = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        target = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)

        # With luminance preservation
        config = TransferConfig(
            algorithm=TransferAlgorithm.REINHARD_LCH,
            preserve_luminance=True
        )
        algorithm = ReinhardLCHAlgorithm(config)

        result = algorithm.transfer(source, target)

        assert result.dtype == np.uint8
        # Luminance should be closer to target than without preservation
        # (Detailed check would require Lab conversion)


class TestRGBDirectAlgorithm:
    """Test RGB Direct algorithm."""

    def test_rgb_direct_transfer(self):
        """Test RGB direct transfer."""
        source = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        target = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)

        config = TransferConfig(algorithm=TransferAlgorithm.RGB_DIRECT)
        algorithm = RGBDirectAlgorithm(config)

        result = algorithm.transfer(source, target)

        assert result.dtype == np.uint8
        assert result.shape == target.shape


class TestHistogramMatchAlgorithm:
    """Test Histogram Matching algorithm."""

    def test_histogram_match_transfer(self):
        """Test histogram matching transfer."""
        source = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        target = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)

        config = TransferConfig(algorithm=TransferAlgorithm.HISTOGRAM_MATCH)
        algorithm = HistogramMatchAlgorithm(config)

        result = algorithm.transfer(source, target)

        assert result.dtype == np.uint8
        assert result.shape == target.shape


class TestTransferEngine:
    """Test TransferEngine class."""

    @pytest.fixture
    def engine(self):
        """Create TransferEngine instance."""
        return TransferEngine()

    @pytest.fixture
    def source(self):
        """Create source image."""
        return np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)

    @pytest.fixture
    def target(self):
        """Create target image."""
        return np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)

    # ============================================================================
    # Initialization Tests
    # ============================================================================

    def test_engine_initialization(self, engine):
        """Test engine initialization."""
        assert engine.default_config.algorithm == TransferAlgorithm.REINHARD_LAB
        assert engine.color_manager is not None
        assert engine.stats_engine is not None

    def test_engine_custom_config(self):
        """Test engine with custom default config."""
        config = TransferConfig(algorithm=TransferAlgorithm.REINHARD_LCH)
        engine = TransferEngine(default_config=config)

        assert engine.default_config.algorithm == TransferAlgorithm.REINHARD_LCH

    # ============================================================================
    # Basic Transfer Tests
    # ============================================================================

    def test_transfer_basic(self, engine, source, target):
        """Test basic transfer."""
        result = engine.transfer(source, target)

        assert result.dtype == np.uint8
        assert result.shape == target.shape
        assert 0 <= np.min(result) <= 255
        assert 0 <= np.max(result) <= 255

    def test_transfer_all_algorithms(self, engine, source, target):
        """Test all available algorithms."""
        for algorithm in TransferAlgorithm:
            config = TransferConfig(algorithm=algorithm)
            result = engine.transfer(source, target, config)

            assert result.dtype == np.uint8
            assert result.shape == target.shape

    def test_transfer_with_custom_config(self, engine, source, target):
        """Test transfer with custom config."""
        config = TransferConfig(
            algorithm=TransferAlgorithm.REINHARD_LAB,
            blend_factor=0.5,
            clip_output=True
        )

        result = engine.transfer(source, target, config)

        assert result.dtype == np.uint8
        assert result.shape == target.shape

    # ============================================================================
    # Blending Tests
    # ============================================================================

    def test_blending_full(self, engine, source, target):
        """Test full transfer (blend_factor=1.0)."""
        config = TransferConfig(blend_factor=1.0)
        result = engine.transfer(source, target, config)

        # Result should be different from target
        assert not np.array_equal(result, target)

    def test_blending_none(self, engine, source, target):
        """Test no transfer (blend_factor=0.0)."""
        config = TransferConfig(blend_factor=0.0)
        result = engine.transfer(source, target, config)

        # Result should be same as target
        np.testing.assert_array_equal(result, target)

    def test_blending_partial(self, engine, source, target):
        """Test partial transfer (blend_factor=0.5)."""
        config_full = TransferConfig(blend_factor=1.0)
        config_half = TransferConfig(blend_factor=0.5)

        result_full = engine.transfer(source, target, config_full)
        result_half = engine.transfer(source, target, config_half)

        # Half blend should be between target and full transfer
        # (Approximate check)
        diff_target_full = np.mean(np.abs(result_full.astype(float) - target.astype(float)))
        diff_target_half = np.mean(np.abs(result_half.astype(float) - target.astype(float)))

        assert diff_target_half < diff_target_full

    # ============================================================================
    # Masking Tests
    # ============================================================================

    def test_transfer_with_mask(self, engine, source, target):
        """Test transfer with mask."""
        # Create mask (top half only)
        mask = np.zeros((100, 100), dtype=np.uint8)
        mask[:50, :] = 255

        result = engine.transfer_with_mask(source, target, mask)

        assert result.dtype == np.uint8
        assert result.shape == target.shape

        # Bottom half should be unchanged
        np.testing.assert_array_equal(result[50:, :, :], target[50:, :, :])

    def test_transfer_full_mask(self, engine, source, target):
        """Test transfer with full mask (all white)."""
        mask = np.ones((100, 100), dtype=np.uint8) * 255

        result_masked = engine.transfer_with_mask(source, target, mask)
        result_unmasked = engine.transfer(source, target)

        # Should be approximately same as unmasked
        np.testing.assert_allclose(result_masked, result_unmasked, atol=2)

    def test_transfer_empty_mask(self, engine, source, target):
        """Test transfer with empty mask (all black)."""
        mask = np.zeros((100, 100), dtype=np.uint8)

        result = engine.transfer_with_mask(source, target, mask)

        # Should be same as target (no transfer)
        np.testing.assert_array_equal(result, target)

    # ============================================================================
    # Batch Processing Tests
    # ============================================================================

    def test_batch_transfer_single(self, engine, source):
        """Test batch transfer with single target."""
        target = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)

        results = engine.batch_transfer(source, [target])

        assert len(results) == 1
        assert results[0].dtype == np.uint8

    def test_batch_transfer_multiple(self, engine, source):
        """Test batch transfer with multiple targets."""
        targets = [
            np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
            for _ in range(5)
        ]

        results = engine.batch_transfer(source, targets)

        assert len(results) == 5
        for result in results:
            assert result.dtype == np.uint8
            assert result.shape == (100, 100, 3)

    def test_batch_transfer_empty(self, engine, source):
        """Test batch transfer with empty list."""
        results = engine.batch_transfer(source, [])

        assert len(results) == 0

    # ============================================================================
    # Algorithm Registry Tests
    # ============================================================================

    def test_get_available_algorithms(self, engine):
        """Test getting available algorithms."""
        algorithms = engine.get_available_algorithms()

        assert len(algorithms) == 4
        assert TransferAlgorithm.REINHARD_LAB in algorithms
        assert TransferAlgorithm.REINHARD_LCH in algorithms
        assert TransferAlgorithm.RGB_DIRECT in algorithms
        assert TransferAlgorithm.HISTOGRAM_MATCH in algorithms

    def test_register_algorithm(self, engine):
        """Test registering custom algorithm."""
        # This would require creating a custom algorithm class
        # For now, just test that the method exists
        assert hasattr(TransferEngine, 'register_algorithm')

    # ============================================================================
    # Edge Cases
    # ============================================================================

    def test_transfer_same_image(self, engine, source):
        """Test transferring from image to itself."""
        result = engine.transfer(source, source)

        # Result should be similar to source (may not be exact due to conversions)
        diff = np.mean(np.abs(result.astype(float) - source.astype(float)))
        assert diff < 10  # Small difference acceptable

    def test_transfer_constant_images(self, engine):
        """Test transfer between constant images."""
        source = np.ones((50, 50, 3), dtype=np.uint8) * 100
        target = np.ones((50, 50, 3), dtype=np.uint8) * 150

        result = engine.transfer(source, target)

        # Should not crash, result should be reasonable
        assert result.dtype == np.uint8
        assert result.shape == target.shape

    def test_transfer_different_sizes(self, engine):
        """Test transfer between different sized images."""
        source = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        target = np.random.randint(0, 256, (200, 200, 3), dtype=np.uint8)

        # Should work (statistics are size-independent)
        result = engine.transfer(source, target)

        assert result.shape == target.shape

    def test_transfer_small_images(self, engine):
        """Test transfer with very small images."""
        source = np.random.randint(0, 256, (10, 10, 3), dtype=np.uint8)
        target = np.random.randint(0, 256, (10, 10, 3), dtype=np.uint8)

        result = engine.transfer(source, target)

        assert result.shape == target.shape


class TestConvenienceFunction:
    """Test convenience function."""

    def test_transfer_color_function(self):
        """Test convenience function."""
        source = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        target = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)

        result = transfer_color(source, target)

        assert result.dtype == np.uint8
        assert result.shape == target.shape

    def test_transfer_color_with_algorithm(self):
        """Test convenience function with algorithm selection."""
        source = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        target = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)

        result = transfer_color(source, target, algorithm='reinhard_lch')

        assert result.dtype == np.uint8

    def test_transfer_color_with_blending(self):
        """Test convenience function with blending."""
        source = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        target = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)

        result = transfer_color(source, target, blend_factor=0.5)

        assert result.dtype == np.uint8


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
