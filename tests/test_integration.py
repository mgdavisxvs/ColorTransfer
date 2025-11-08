"""
Integration tests for Color Transfer Framework.

Tests full pipeline integration across all modules:
- ColorSpaceManager + ColorStatisticsEngine
- TransferEngine + OptimizerEngine
- DiagnosticsVisualizer integration
- ComplexityAnalyzer integration
- End-to-end workflows
"""

import pytest
import numpy as np
import cv2
import sys
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from color_transfer_framework import (
    ColorSpaceManager,
    ColorSpace,
    ColorStatisticsEngine,
    TransferEngine,
    TransferConfig,
    TransferAlgorithm,
    OptimizerEngine,
    OptimizationMode,
    transfer_color,
    benchmark_transfer
)

# Import additional modules
from color_transfer_framework.diagnostics_visualizer import DiagnosticsVisualizer
from color_transfer_framework.complexity_analyzer import (
    ComplexityAnalyzer,
    analyze_transfer_convergence
)


class TestFullPipeline:
    """Test complete color transfer pipeline."""

    @pytest.fixture
    def test_images(self):
        """Create test images."""
        # Source: Blue gradient
        source = np.zeros((200, 200, 3), dtype=np.uint8)
        for i in range(200):
            source[i, :, 0] = int(50 + 150 * i / 200)  # B
            source[i, :, 1] = int(30 + 100 * i / 200)  # G
            source[i, :, 2] = int(20 + 80 * i / 200)   # R

        # Target: Red gradient
        target = np.zeros((200, 200, 3), dtype=np.uint8)
        for i in range(200):
            target[i, :, 0] = int(20 + 80 * i / 200)   # B
            target[i, :, 1] = int(40 + 120 * i / 200)  # G
            target[i, :, 2] = int(100 + 150 * i / 200) # R

        return source, target

    def test_end_to_end_transfer(self, test_images):
        """Test complete transfer pipeline."""
        source, target = test_images

        # Initialize all components
        color_manager = ColorSpaceManager()
        stats_engine = ColorStatisticsEngine()
        transfer_engine = TransferEngine()

        # Convert to Lab
        source_lab = color_manager.convert_to(
            color_manager.to_float(source), ColorSpace.LAB
        )
        target_lab = color_manager.convert_to(
            color_manager.to_float(target), ColorSpace.LAB
        )

        # Compute statistics
        source_stats = stats_engine.compute_stats(source_lab)
        target_stats = stats_engine.compute_stats(target_lab)

        # Transfer
        config = TransferConfig(algorithm=TransferAlgorithm.REINHARD_LAB)
        result = transfer_engine.transfer(source, target, config)

        # Verify result
        assert result.dtype == np.uint8
        assert result.shape == target.shape

        # Verify statistics preservation
        result_lab = color_manager.convert_to(
            color_manager.to_float(result), ColorSpace.LAB
        )
        result_stats = stats_engine.compute_stats(result_lab)

        # Mean should be close
        np.testing.assert_allclose(result_stats.mean, source_stats.mean, rtol=0.1)

    def test_all_algorithms_integration(self, test_images):
        """Test all algorithms work together."""
        source, target = test_images

        engine = TransferEngine()

        # Test all algorithms
        for algorithm in TransferAlgorithm:
            config = TransferConfig(algorithm=algorithm)
            result = engine.transfer(source, target, config)

            assert result.dtype == np.uint8
            assert result.shape == target.shape
            assert not np.array_equal(result, target)  # Should be different

    def test_batch_with_statistics(self, test_images):
        """Test batch processing with statistics engine."""
        source, target = test_images

        # Create multiple targets
        targets = [
            target.copy(),
            target + np.random.randint(-10, 10, target.shape, dtype=np.int16).clip(0, 255).astype(np.uint8),
            target + np.random.randint(-20, 20, target.shape, dtype=np.int16).clip(0, 255).astype(np.uint8)
        ]

        engine = TransferEngine()
        results = engine.batch_transfer(source, targets)

        assert len(results) == len(targets)

        # Verify statistics for each result
        stats_engine = ColorStatisticsEngine()
        color_manager = ColorSpaceManager()

        source_lab = color_manager.convert_to(
            color_manager.to_float(source), ColorSpace.LAB
        )
        source_stats = stats_engine.compute_stats(source_lab)

        for result in results:
            result_lab = color_manager.convert_to(
                color_manager.to_float(result), ColorSpace.LAB
            )
            result_stats = stats_engine.compute_stats(result_lab)

            # All results should have similar mean to source
            np.testing.assert_allclose(result_stats.mean, source_stats.mean, rtol=0.2)


class TestOptimizerIntegration:
    """Test OptimizerEngine integration."""

    @pytest.fixture
    def test_images(self):
        """Create test images."""
        source = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        target = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        return source, target

    def test_optimizer_with_transfer(self, test_images):
        """Test optimizer integration with transfer engine."""
        source, target = test_images

        optimizer = OptimizerEngine(mode=OptimizationMode.CPU)
        engine = TransferEngine()

        # Profile transfer
        metrics = optimizer.profile_transfer(engine, source, target, n_iterations=5)

        assert metrics.execution_time_ms > 0
        assert metrics.memory_used_mb > 0
        assert metrics.throughput_images_per_sec > 0

    def test_benchmark_all_algorithms(self, test_images):
        """Test benchmarking integration."""
        source, target = test_images

        optimizer = OptimizerEngine()

        # Benchmark all algorithms
        results = optimizer.benchmark_algorithms(source, target, n_iterations=3)

        assert len(results) == 4  # Four algorithms
        assert 'reinhard_lab' in results
        assert 'reinhard_lch' in results

        # All should have valid metrics
        for algo_name, metrics in results.items():
            assert metrics.execution_time_ms > 0


class TestVisualizationIntegration:
    """Test DiagnosticsVisualizer integration."""

    @pytest.fixture
    def test_images(self):
        """Create test images."""
        source = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        target = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        return source, target

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for output."""
        temp = tempfile.mkdtemp()
        yield temp
        shutil.rmtree(temp)

    def test_visualization_after_transfer(self, test_images, temp_dir):
        """Test visualization integration."""
        source, target = test_images

        # Transfer
        result = transfer_color(source, target)

        # Visualize
        viz = DiagnosticsVisualizer()

        # Test histogram
        fig = viz.plot_histogram_comparison(source, target, result)
        assert fig is not None

        # Test side by side
        fig = viz.plot_side_by_side(source, target, result)
        assert fig is not None

    def test_comprehensive_report_generation(self, test_images, temp_dir):
        """Test comprehensive report generation."""
        source, target = test_images

        # Transfer
        result = transfer_color(source, target)

        # Generate report
        viz = DiagnosticsVisualizer()
        files = viz.generate_comprehensive_report(source, target, result, temp_dir)

        # Verify files created
        assert 'histogram' in files
        assert 'side_by_side' in files
        assert 'delta_e' in files

        # Verify files exist
        for file_path in files.values():
            assert Path(file_path).exists()


class TestComplexityAnalyzerIntegration:
    """Test ComplexityAnalyzer integration."""

    @pytest.fixture
    def test_images(self):
        """Create test images."""
        source = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        target = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        return source, target

    def test_iteration_analysis(self, test_images):
        """Test iteration analysis."""
        source, target = test_images

        analyzer = ComplexityAnalyzer()

        # Iterate transfer
        data = analyzer.iterate_transfer(source, target, n_iterations=5, collect_images=False)

        assert len(data) == 5
        assert all(d.statistics is not None for d in data)
        assert all(d.entropy >= 0 for d in data)

    def test_convergence_analysis(self, test_images):
        """Test convergence analysis."""
        source, target = test_images

        # Quick convergence test
        report = analyze_transfer_convergence(source, target, n_iterations=5)

        assert isinstance(report.converged, bool)
        assert report.iterations_to_convergence >= 0
        assert report.final_mean_error >= 0

        # Summary should be readable
        summary = report.summary()
        assert 'Convergence' in summary

    def test_entropy_evolution(self, test_images):
        """Test entropy evolution tracking."""
        source, target = test_images

        analyzer = ComplexityAnalyzer()
        data = analyzer.iterate_transfer(source, target, n_iterations=5, collect_images=False)

        # Analyze entropy
        entropy_analysis = analyzer.analyze_entropy_evolution(data)

        assert 'initial_entropy' in entropy_analysis
        assert 'final_entropy' in entropy_analysis
        assert 'entropy_change' in entropy_analysis

    def test_n_way_cycle_analysis(self, test_images):
        """Test n-way cycle analysis."""
        source, target = test_images

        # Create third image
        third = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)

        analyzer = ComplexityAnalyzer()

        # Analyze 3-way cycle
        result = analyzer.analyze_n_way_cycle([source, target, third], n_iterations=3)

        assert result['n_images'] == 3
        assert result['n_iterations'] == 3
        assert 'converged_to_common' in result
        assert len(result['final_statistics']) == 3


class TestConvenienceFunctions:
    """Test convenience functions integrate well."""

    @pytest.fixture
    def test_images(self):
        """Create test images."""
        source = np.random.randint(0, 256, (50, 50, 3), dtype=np.uint8)
        target = np.random.randint(0, 256, (50, 50, 3), dtype=np.uint8)
        return source, target

    def test_transfer_color_function(self, test_images):
        """Test transfer_color convenience function."""
        source, target = test_images

        result = transfer_color(source, target)

        assert result.dtype == np.uint8
        assert result.shape == target.shape

    def test_benchmark_transfer_function(self, test_images):
        """Test benchmark_transfer convenience function."""
        source, target = test_images

        metrics = benchmark_transfer(source, target, 'reinhard_lab', n_iterations=3)

        assert metrics.execution_time_ms > 0
        assert metrics.throughput_images_per_sec > 0


class TestEdgeCasesIntegration:
    """Test edge cases across multiple modules."""

    def test_single_pixel_pipeline(self):
        """Test pipeline with single pixel image."""
        source = np.array([[[100, 150, 200]]], dtype=np.uint8)
        target = np.array([[[50, 80, 120]]], dtype=np.uint8)

        result = transfer_color(source, target)

        assert result.shape == target.shape

    def test_large_image_pipeline(self):
        """Test pipeline with larger image."""
        # 1000x1000 image
        source = np.random.randint(0, 256, (1000, 1000, 3), dtype=np.uint8)
        target = np.random.randint(0, 256, (1000, 1000, 3), dtype=np.uint8)

        # Should not crash or timeout
        result = transfer_color(source, target)

        assert result.shape == target.shape

    def test_different_sized_images(self):
        """Test with different sized images."""
        source = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        target = np.random.randint(0, 256, (200, 200, 3), dtype=np.uint8)

        # Should work (statistics are size-independent)
        result = transfer_color(source, target)

        assert result.shape == target.shape


class TestMemoryEfficiency:
    """Test memory efficiency of pipeline."""

    def test_batch_memory_efficiency(self):
        """Test batch processing doesn't leak memory."""
        source = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        targets = [np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
                  for _ in range(10)]

        engine = TransferEngine()

        # Should not increase memory dramatically
        results = engine.batch_transfer(source, targets)

        assert len(results) == 10

    def test_iteration_memory_efficiency(self):
        """Test iteration without collecting images."""
        source = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        target = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)

        analyzer = ComplexityAnalyzer()

        # With collect_images=False, should use minimal memory
        data = analyzer.iterate_transfer(source, target, n_iterations=20,
                                        collect_images=False)

        assert len(data) == 20
        assert all(d.image is None for d in data)  # No images stored


class TestRobustness:
    """Test robustness of integrated system."""

    def test_constant_image_handling(self):
        """Test handling of constant images."""
        source = np.ones((50, 50, 3), dtype=np.uint8) * 100
        target = np.ones((50, 50, 3), dtype=np.uint8) * 150

        # Should not crash
        result = transfer_color(source, target)

        assert result.dtype == np.uint8

    def test_extreme_contrast(self):
        """Test with extreme contrast images."""
        # Very dark source
        source = np.ones((50, 50, 3), dtype=np.uint8) * 10

        # Very bright target
        target = np.ones((50, 50, 3), dtype=np.uint8) * 250

        result = transfer_color(source, target)

        assert result.dtype == np.uint8
        assert 0 <= np.min(result) <= 255
        assert 0 <= np.max(result) <= 255


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
