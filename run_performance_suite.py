#!/usr/bin/env python3
"""
Performance Benchmarking Suite
==============================

Comprehensive, automated benchmarking script for the Color Transfer Framework.

Benchmarks across:
- All algorithms (Reinhard L*a*b*, LCH, RGB Direct, Histogram Match)
- Execution modes (CPU, GPU)
- Image sizes (512x512, 1920x1080, 3840x2160)
- Batch sizes (1, 10, 50)

Outputs:
- benchmark_results.csv: Raw results
- BENCHMARKS.md: Human-readable summary report
"""

import argparse
import csv
import time
import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass, asdict
import numpy as np
import cv2
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from color_transfer_framework.transfer_engine import TransferEngine, TransferConfig, TransferAlgorithm
from color_transfer_framework.optimizer_engine import OptimizerEngine
from color_transfer_framework.interface_layer.orchestrator import TransferOrchestrator


@dataclass
class BenchmarkConfig:
    """Configuration for benchmark run."""
    algorithms: List[str]
    modes: List[str]
    image_sizes: List[Tuple[int, int]]  # [(width, height), ...]
    batch_sizes: List[int]
    output_dir: Path
    n_iterations: int = 5  # Iterations per test for averaging


@dataclass
class BenchmarkResult:
    """Single benchmark result."""
    algorithm: str
    mode: str
    image_size: str
    batch_size: int
    avg_execution_time_ms: float
    std_execution_time_ms: float
    throughput_images_per_sec: float
    peak_memory_mb: float
    peak_vram_mb: float = 0.0


class PerformanceBenchmarkingSuite:
    """
    Comprehensive benchmarking suite for the Color Transfer Framework.

    Tests all combinations of algorithms, execution modes, image sizes,
    and batch sizes to generate a complete performance profile.
    """

    # Standard image size presets
    SIZE_PRESETS = {
        "512x512": (512, 512),
        "small": (512, 512),
        "1080p": (1920, 1080),
        "hd": (1920, 1080),
        "4k": (3840, 2160),
    }

    def __init__(self, config: BenchmarkConfig):
        """
        Initialize benchmarking suite.

        Parameters:
        ----------
        config : BenchmarkConfig
            Benchmark configuration
        """
        self.config = config
        self.orchestrator = TransferOrchestrator()
        self.results: List[BenchmarkResult] = []

        # Create output directory
        self.config.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_synthetic_image(
        self,
        width: int,
        height: int,
        pattern: str = "gradient"
    ) -> np.ndarray:
        """
        Generate synthetic test image.

        Parameters:
        ----------
        width : int
            Image width
        height : int
            Image height
        pattern : str
            Pattern type ('gradient', 'noise', 'blocks')

        Returns:
        -------
        np.ndarray
            Generated image (BGR format)
        """
        if pattern == "gradient":
            # Linear gradient
            img = np.zeros((height, width, 3), dtype=np.uint8)
            for i in range(height):
                img[i, :, :] = int(255 * i / height)
            return img

        elif pattern == "noise":
            # Random noise
            return np.random.randint(0, 256, (height, width, 3), dtype=np.uint8)

        elif pattern == "blocks":
            # Color blocks
            img = np.zeros((height, width, 3), dtype=np.uint8)
            block_size = 100
            colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)]
            for i, color in enumerate(colors):
                y = (i // 2) * block_size
                x = (i % 2) * block_size
                img[y:y+block_size, x:x+block_size] = color
            return cv2.resize(img, (width, height))

        else:
            raise ValueError(f"Unknown pattern: {pattern}")

    def run_single_benchmark(
        self,
        algorithm: str,
        mode: str,
        image_size: Tuple[int, int],
        batch_size: int
    ) -> BenchmarkResult:
        """
        Run a single benchmark test.

        Parameters:
        ----------
        algorithm : str
            Algorithm to test
        mode : str
            Execution mode ('cpu' or 'gpu')
        image_size : tuple
            (width, height)
        batch_size : int
            Number of images in batch

        Returns:
        -------
        BenchmarkResult
            Benchmark results
        """
        width, height = image_size
        size_str = f"{width}x{height}"

        print(f"  Testing: {algorithm} | {mode.upper()} | {size_str} | batch={batch_size}")

        # Generate synthetic images
        source = self.generate_synthetic_image(width, height, "gradient")
        target = self.generate_synthetic_image(width, height, "noise")

        # Create config
        config = TransferConfig(
            algorithm=TransferAlgorithm(algorithm),
            blend_factor=1.0
        )

        # Warm-up run
        _ = self.orchestrator.transfer(source, target, config, enable_gpu=(mode == 'gpu'))

        # Timed runs
        execution_times = []
        for _ in range(self.config.n_iterations):
            start_time = time.perf_counter()

            if batch_size == 1:
                _ = self.orchestrator.transfer(
                    source, target, config,
                    enable_gpu=(mode == 'gpu'),
                    profile_performance=False
                )
            else:
                # Batch processing
                for _ in range(batch_size):
                    _ = self.orchestrator.transfer(
                        source, target, config,
                        enable_gpu=(mode == 'gpu'),
                        profile_performance=False
                    )

            elapsed = (time.perf_counter() - start_time) * 1000  # ms
            execution_times.append(elapsed)

        # Calculate metrics
        avg_time = np.mean(execution_times)
        std_time = np.std(execution_times)
        throughput = (batch_size * 1000.0) / avg_time if avg_time > 0 else 0.0

        # Memory metrics
        peak_memory = self.orchestrator.optimizer_engine.memory_tracker.get_peak_mb()

        return BenchmarkResult(
            algorithm=algorithm,
            mode=mode,
            image_size=size_str,
            batch_size=batch_size,
            avg_execution_time_ms=avg_time,
            std_execution_time_ms=std_time,
            throughput_images_per_sec=throughput,
            peak_memory_mb=peak_memory,
            peak_vram_mb=0.0  # GPU memory tracking would go here
        )

    def run_all_benchmarks(self) -> None:
        """Run all benchmark combinations."""
        total_tests = (
            len(self.config.algorithms) *
            len(self.config.modes) *
            len(self.config.image_sizes) *
            len(self.config.batch_sizes)
        )

        print(f"\n{'='*70}")
        print(f"Color Transfer Framework - Performance Benchmarking Suite")
        print(f"{'='*70}")
        print(f"Total tests to run: {total_tests}")
        print(f"Iterations per test: {self.config.n_iterations}")
        print(f"Output directory: {self.config.output_dir}")
        print(f"{'='*70}\n")

        test_count = 0

        for algorithm in self.config.algorithms:
            for mode in self.config.modes:
                # Skip GPU if not available
                if mode == 'gpu':
                    try:
                        import torch
                        if not torch.cuda.is_available():
                            print(f"  Skipping GPU tests (CUDA not available)")
                            continue
                    except ImportError:
                        print(f"  Skipping GPU tests (PyTorch not installed)")
                        continue

                for image_size in self.config.image_sizes:
                    for batch_size in self.config.batch_sizes:
                        test_count += 1
                        print(f"\n[Test {test_count}/{total_tests}]")

                        try:
                            result = self.run_single_benchmark(
                                algorithm, mode, image_size, batch_size
                            )
                            self.results.append(result)

                            print(f"  ✓ Avg time: {result.avg_execution_time_ms:.2f} ms")
                            print(f"  ✓ Throughput: {result.throughput_images_per_sec:.2f} img/s")

                        except Exception as e:
                            print(f"  ✗ Error: {str(e)}")

        print(f"\n{'='*70}")
        print(f"Benchmarking complete! {len(self.results)} tests successful.")
        print(f"{'='*70}\n")

    def save_csv_results(self) -> Path:
        """
        Save raw results to CSV.

        Returns:
        -------
        Path
            Path to CSV file
        """
        csv_path = self.config.output_dir / "benchmark_results.csv"

        with open(csv_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'algorithm', 'mode', 'image_size', 'batch_size',
                'avg_execution_time_ms', 'std_execution_time_ms',
                'throughput_images_per_sec', 'peak_memory_mb', 'peak_vram_mb'
            ])
            writer.writeheader()
            for result in self.results:
                writer.writerow(asdict(result))

        print(f"✓ Raw results saved to: {csv_path}")
        return csv_path

    def generate_markdown_report(self) -> Path:
        """
        Generate human-readable markdown report.

        Returns:
        -------
        Path
            Path to markdown file
        """
        md_path = self.config.output_dir / "BENCHMARKS.md"

        with open(md_path, 'w') as f:
            # Header
            f.write("# Color Transfer Framework - Performance Benchmarks\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**Total Tests:** {len(self.results)}\n\n")
            f.write("---\n\n")

            # Summary by algorithm
            f.write("## Performance by Algorithm\n\n")
            f.write("| Algorithm | Avg Time (ms) | Throughput (img/s) | Peak Memory (MB) |\n")
            f.write("|-----------|---------------|--------------------|-----------------|\n")

            by_algorithm = {}
            for result in self.results:
                if result.algorithm not in by_algorithm:
                    by_algorithm[result.algorithm] = []
                by_algorithm[result.algorithm].append(result)

            for algo, results in sorted(by_algorithm.items()):
                avg_time = np.mean([r.avg_execution_time_ms for r in results])
                avg_throughput = np.mean([r.throughput_images_per_sec for r in results])
                max_memory = max([r.peak_memory_mb for r in results])

                f.write(f"| {algo} | {avg_time:.2f} | {avg_throughput:.2f} | {max_memory:.2f} |\n")

            f.write("\n---\n\n")

            # Detailed results by image size
            f.write("## Performance by Image Size\n\n")

            by_size = {}
            for result in self.results:
                if result.image_size not in by_size:
                    by_size[result.image_size] = []
                by_size[result.image_size].append(result)

            for size, results in sorted(by_size.items()):
                f.write(f"### {size}\n\n")
                f.write("| Algorithm | Mode | Batch | Avg Time (ms) | Throughput (img/s) |\n")
                f.write("|-----------|------|-------|---------------|-------------------|\n")

                for result in sorted(results, key=lambda r: (r.algorithm, r.mode, r.batch_size)):
                    f.write(f"| {result.algorithm} | {result.mode.upper()} | {result.batch_size} | "
                           f"{result.avg_execution_time_ms:.2f} | {result.throughput_images_per_sec:.2f} |\n")

                f.write("\n")

            # Best performers
            f.write("---\n\n")
            f.write("## Best Performers\n\n")

            fastest = min(self.results, key=lambda r: r.avg_execution_time_ms)
            highest_throughput = max(self.results, key=lambda r: r.throughput_images_per_sec)
            lowest_memory = min(self.results, key=lambda r: r.peak_memory_mb)

            f.write(f"**Fastest:** {fastest.algorithm} ({fastest.mode.upper()}, {fastest.image_size}, "
                   f"batch={fastest.batch_size}) - {fastest.avg_execution_time_ms:.2f} ms\n\n")
            f.write(f"**Highest Throughput:** {highest_throughput.algorithm} "
                   f"({highest_throughput.mode.upper()}, {highest_throughput.image_size}, "
                   f"batch={highest_throughput.batch_size}) - "
                   f"{highest_throughput.throughput_images_per_sec:.2f} img/s\n\n")
            f.write(f"**Lowest Memory:** {lowest_memory.algorithm} ({lowest_memory.mode.upper()}, "
                   f"{lowest_memory.image_size}, batch={lowest_memory.batch_size}) - "
                   f"{lowest_memory.peak_memory_mb:.2f} MB\n\n")

        print(f"✓ Markdown report saved to: {md_path}")
        return md_path


def main():
    """CLI entry point for benchmarking suite."""
    parser = argparse.ArgumentParser(
        description="Run comprehensive performance benchmarks for Color Transfer Framework"
    )

    parser.add_argument(
        '--algorithms', '-a',
        nargs='+',
        default=['reinhard_lab', 'reinhard_lch', 'rgb_direct', 'histogram_match'],
        help='Algorithms to benchmark'
    )

    parser.add_argument(
        '--modes', '-m',
        nargs='+',
        default=['cpu'],
        choices=['cpu', 'gpu'],
        help='Execution modes to benchmark'
    )

    parser.add_argument(
        '--sizes', '-s',
        nargs='+',
        default=['512x512', '1080p', '4k'],
        help='Image sizes to benchmark (e.g., 512x512, 1080p, 4k)'
    )

    parser.add_argument(
        '--batch-sizes', '-b',
        nargs='+',
        type=int,
        default=[1, 10],
        help='Batch sizes to benchmark'
    )

    parser.add_argument(
        '--iterations', '-i',
        type=int,
        default=5,
        help='Iterations per test for averaging'
    )

    parser.add_argument(
        '--output', '-o',
        type=Path,
        default=Path('./benchmarks'),
        help='Output directory for results'
    )

    args = parser.parse_args()

    # Convert size strings to tuples
    image_sizes = []
    for size_str in args.sizes:
        if size_str in PerformanceBenchmarkingSuite.SIZE_PRESETS:
            image_sizes.append(PerformanceBenchmarkingSuite.SIZE_PRESETS[size_str])
        elif 'x' in size_str:
            width, height = map(int, size_str.split('x'))
            image_sizes.append((width, height))
        else:
            print(f"Warning: Unknown size format '{size_str}', skipping")

    # Create config
    config = BenchmarkConfig(
        algorithms=args.algorithms,
        modes=args.modes,
        image_sizes=image_sizes,
        batch_sizes=args.batch_sizes,
        output_dir=args.output,
        n_iterations=args.iterations
    )

    # Run benchmarks
    suite = PerformanceBenchmarkingSuite(config)
    suite.run_all_benchmarks()

    # Save results
    suite.save_csv_results()
    suite.generate_markdown_report()

    print("\n✓ Benchmarking complete!")


if __name__ == "__main__":
    main()
