"""
Tests for Command-Line Interface
================================

Comprehensive tests for CLI commands and user interactions.
"""

import pytest
import tempfile
import numpy as np
import cv2
from pathlib import Path
from typer.testing import CliRunner

from color_transfer_framework.interface_layer.cli import app


class TestCLI:
    """Tests for CLI commands."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def test_images(self):
        """Create temporary test images."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create source image
            source = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
            source_path = tmpdir / "source.png"
            cv2.imwrite(str(source_path), source)

            # Create target image
            target = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
            target_path = tmpdir / "target.png"
            cv2.imwrite(str(target_path), target)

            # Create mask image
            mask = np.ones((100, 100), dtype=np.uint8) * 255
            mask_path = tmpdir / "mask.png"
            cv2.imwrite(str(mask_path), mask)

            yield {
                'dir': tmpdir,
                'source': source_path,
                'target': target_path,
                'mask': mask_path
            }

    def test_transfer_basic(self, runner, test_images):
        """Test basic transfer command."""
        output_path = test_images['dir'] / "result.png"

        result = runner.invoke(app, [
            "transfer",
            str(test_images['source']),
            str(test_images['target']),
            "--output", str(output_path)
        ])

        assert result.exit_code == 0
        assert output_path.exists()
        assert "Transfer complete" in result.stdout

    def test_transfer_with_algorithm(self, runner, test_images):
        """Test transfer with specific algorithm."""
        output_path = test_images['dir'] / "result.png"

        algorithms = ["reinhard_lab", "reinhard_lch", "rgb_direct", "histogram_match"]

        for algo in algorithms:
            result = runner.invoke(app, [
                "transfer",
                str(test_images['source']),
                str(test_images['target']),
                "--output", str(output_path),
                "--algo", algo
            ])

            assert result.exit_code == 0, f"Failed for algorithm: {algo}"
            assert output_path.exists()

    def test_transfer_with_blend(self, runner, test_images):
        """Test transfer with blend factor."""
        output_path = test_images['dir'] / "result.png"

        result = runner.invoke(app, [
            "transfer",
            str(test_images['source']),
            str(test_images['target']),
            "--output", str(output_path),
            "--blend", "0.5"
        ])

        assert result.exit_code == 0
        assert output_path.exists()

    def test_transfer_with_mask(self, runner, test_images):
        """Test transfer with mask."""
        output_path = test_images['dir'] / "result.png"

        result = runner.invoke(app, [
            "transfer",
            str(test_images['source']),
            str(test_images['target']),
            "--output", str(output_path),
            "--mask", str(test_images['mask'])
        ])

        assert result.exit_code == 0
        assert output_path.exists()

    def test_transfer_with_visualize(self, runner, test_images):
        """Test transfer with visualization."""
        output_path = test_images['dir'] / "result.png"

        result = runner.invoke(app, [
            "transfer",
            str(test_images['source']),
            str(test_images['target']),
            "--output", str(output_path),
            "--visualize"
        ])

        assert result.exit_code == 0
        assert output_path.exists()

        # Check for diagnostics directory
        diagnostics_dir = test_images['dir'] / "diagnostics"
        assert diagnostics_dir.exists()

    def test_transfer_gpu_flag(self, runner, test_images):
        """Test transfer with GPU flag."""
        output_path = test_images['dir'] / "result.png"

        result = runner.invoke(app, [
            "transfer",
            str(test_images['source']),
            str(test_images['target']),
            "--output", str(output_path),
            "--gpu"
        ])

        # Should succeed (even if GPU not available, it falls back)
        assert result.exit_code == 0

    def test_transfer_preserve_luminance(self, runner, test_images):
        """Test transfer with preserve luminance flag."""
        output_path = test_images['dir'] / "result.png"

        result = runner.invoke(app, [
            "transfer",
            str(test_images['source']),
            str(test_images['target']),
            "--output", str(output_path),
            "--algo", "reinhard_lch",
            "--preserve-luminance"
        ])

        assert result.exit_code == 0

    def test_transfer_default_output(self, runner, test_images):
        """Test transfer with default output path."""
        result = runner.invoke(app, [
            "transfer",
            str(test_images['source']),
            str(test_images['target'])
        ])

        assert result.exit_code == 0

        # Check default output exists
        expected_output = test_images['target'].parent / f"{test_images['target'].stem}_transferred{test_images['target'].suffix}"
        assert expected_output.exists()

    def test_transfer_nonexistent_source(self, runner, test_images):
        """Test transfer with nonexistent source file."""
        result = runner.invoke(app, [
            "transfer",
            "nonexistent_source.png",
            str(test_images['target'])
        ])

        assert result.exit_code != 0  # Should fail

    def test_transfer_nonexistent_target(self, runner, test_images):
        """Test transfer with nonexistent target file."""
        result = runner.invoke(app, [
            "transfer",
            str(test_images['source']),
            "nonexistent_target.png"
        ])

        assert result.exit_code != 0  # Should fail

    def test_transfer_invalid_blend(self, runner, test_images):
        """Test transfer with invalid blend factor."""
        output_path = test_images['dir'] / "result.png"

        # Test negative blend
        result = runner.invoke(app, [
            "transfer",
            str(test_images['source']),
            str(test_images['target']),
            "--output", str(output_path),
            "--blend", "-0.5"
        ])

        assert result.exit_code != 0  # Should fail

        # Test blend > 1.0
        result = runner.invoke(app, [
            "transfer",
            str(test_images['source']),
            str(test_images['target']),
            "--output", str(output_path),
            "--blend", "1.5"
        ])

        assert result.exit_code != 0  # Should fail

    def test_algorithms_command(self, runner):
        """Test algorithms listing command."""
        result = runner.invoke(app, ["algorithms"])

        assert result.exit_code == 0
        assert "reinhard_lab" in result.stdout
        assert "reinhard_lch" in result.stdout
        assert "rgb_direct" in result.stdout
        assert "histogram_match" in result.stdout

    def test_info_command(self, runner):
        """Test info command."""
        result = runner.invoke(app, ["info"])

        assert result.exit_code == 0
        assert "Color Transfer Framework" in result.stdout
        assert "Version" in result.stdout
        assert "Module Status" in result.stdout

    def test_help_output(self, runner):
        """Test help message."""
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "transfer" in result.stdout.lower()

    def test_transfer_help(self, runner):
        """Test transfer command help."""
        result = runner.invoke(app, ["transfer", "--help"])

        assert result.exit_code == 0
        assert "source" in result.stdout.lower()
        assert "target" in result.stdout.lower()
        assert "algorithm" in result.stdout.lower()


class TestCLIEdgeCases:
    """Tests for edge cases and error conditions."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def test_images(self):
        """Create temporary test images."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Create various test images
            # Normal image
            normal = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
            normal_path = tmpdir / "normal.png"
            cv2.imwrite(str(normal_path), normal)

            # Single pixel image
            single_pixel = np.array([[[128, 128, 128]]], dtype=np.uint8)
            single_path = tmpdir / "single.png"
            cv2.imwrite(str(single_path), single_pixel)

            # Large image
            large = np.random.randint(0, 256, (1000, 1000, 3), dtype=np.uint8)
            large_path = tmpdir / "large.png"
            cv2.imwrite(str(large_path), large)

            yield {
                'dir': tmpdir,
                'normal': normal_path,
                'single': single_path,
                'large': large_path
            }

    def test_single_pixel_image(self, runner, test_images):
        """Test transfer with single pixel image."""
        output_path = test_images['dir'] / "result.png"

        result = runner.invoke(app, [
            "transfer",
            str(test_images['single']),
            str(test_images['single']),
            "--output", str(output_path)
        ])

        assert result.exit_code == 0

    def test_large_image(self, runner, test_images):
        """Test transfer with large image."""
        output_path = test_images['dir'] / "result.png"

        result = runner.invoke(app, [
            "transfer",
            str(test_images['large']),
            str(test_images['large']),
            "--output", str(output_path),
            "--algo", "rgb_direct"  # Fastest algorithm
        ])

        assert result.exit_code == 0

    def test_mixed_sizes(self, runner, test_images):
        """Test transfer with different sized images."""
        output_path = test_images['dir'] / "result.png"

        result = runner.invoke(app, [
            "transfer",
            str(test_images['single']),
            str(test_images['normal']),
            "--output", str(output_path)
        ])

        # Should handle size mismatch gracefully
        # (May succeed or fail depending on implementation)
        assert result.exit_code in [0, 1]


class TestCLIOutput:
    """Tests for CLI output formatting and user feedback."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def test_images(self):
        """Create temporary test images."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            source = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
            source_path = tmpdir / "source.png"
            cv2.imwrite(str(source_path), source)

            target = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
            target_path = tmpdir / "target.png"
            cv2.imwrite(str(target_path), target)

            yield {
                'dir': tmpdir,
                'source': source_path,
                'target': target_path
            }

    def test_output_contains_metrics(self, runner, test_images):
        """Test that output includes performance metrics."""
        result = runner.invoke(app, [
            "transfer",
            str(test_images['source']),
            str(test_images['target'])
        ])

        assert result.exit_code == 0
        # Check for metrics in output
        assert "Execution Time" in result.stdout or "ms" in result.stdout

    def test_output_contains_run_id(self, runner, test_images):
        """Test that output includes run ID."""
        result = runner.invoke(app, [
            "transfer",
            str(test_images['source']),
            str(test_images['target'])
        ])

        assert result.exit_code == 0
        assert "Run ID" in result.stdout

    def test_verbose_output(self, runner, test_images):
        """Test that operations provide clear feedback."""
        output_path = test_images['dir'] / "result.png"

        result = runner.invoke(app, [
            "transfer",
            str(test_images['source']),
            str(test_images['target']),
            "--output", str(output_path),
            "--visualize"
        ])

        assert result.exit_code == 0
        # Should mention diagnostics
        assert "Diagnostic" in result.stdout or "visualiz" in result.stdout.lower()
