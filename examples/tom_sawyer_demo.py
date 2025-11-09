#!/usr/bin/env python3
"""
Tom Sawyer Method - Demonstration Script
=========================================

This script demonstrates the Tom Sawyer parallel processing method
and compares it to standard color transfer processing.

Usage:
    python examples/tom_sawyer_demo.py --source source.jpg --target target.jpg

Requirements:
    - OpenCV (cv2)
    - NumPy
    - Color Transfer Framework

Example:
    # Compare standard vs Tom Sawyer processing
    python examples/tom_sawyer_demo.py \
        --source examples/source.jpg \
        --target examples/target.jpg \
        --output-dir results/tom_sawyer_demo
"""

import argparse
import sys
import time
from pathlib import Path
import cv2
import numpy as np

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from color_transfer_framework.interface_layer.orchestrator import TransferOrchestrator
from color_transfer_framework.transfer_engine import TransferConfig, TransferAlgorithm


def print_section(title: str):
    """Print section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}\n")


def compare_results(
    standard_result: dict,
    tom_sawyer_result: dict,
    source: np.ndarray,
    target: np.ndarray,
):
    """
    Compare standard vs Tom Sawyer results.

    Args:
        standard_result: Standard processing orchestration result
        tom_sawyer_result: Tom Sawyer processing orchestration result
        source: Source image
        target: Target image
    """
    print_section("Performance Comparison")

    # Time comparison
    std_time = standard_result.metrics.execution_time_ms
    ts_time = tom_sawyer_result.metrics.execution_time_ms
    time_overhead = (ts_time / std_time - 1.0) * 100

    print(f"Standard Processing:")
    print(f"  Time: {std_time:.2f}ms")
    print(f"  Memory: {standard_result.metrics.memory_used_mb:.2f}MB")
    print(f"  Throughput: {standard_result.metrics.throughput_images_per_sec:.2f} img/s")

    print(f"\nTom Sawyer Processing:")
    print(f"  Time: {ts_time:.2f}ms")
    print(f"  Memory: {tom_sawyer_result.metrics.memory_used_mb:.2f}MB")
    print(f"  Throughput: {tom_sawyer_result.metrics.throughput_images_per_sec:.2f} img/s")

    print(f"\nOverhead:")
    print(f"  Time: {time_overhead:+.1f}%")
    print(f"  Memory: {(tom_sawyer_result.metrics.memory_used_mb / standard_result.metrics.memory_used_mb - 1.0) * 100:+.1f}%")

    # Tom Sawyer specific metrics
    if tom_sawyer_result.tom_sawyer_metrics:
        ts_metrics = tom_sawyer_result.tom_sawyer_metrics
        print(f"\nTom Sawyer Details:")
        print(f"  Workers: {ts_metrics.num_workers}")
        print(f"  Per-worker time: {ts_metrics.per_worker_time_ms:.2f}ms")
        print(f"  Aggregation time: {ts_metrics.aggregation_time_ms:.2f}ms")
        print(f"  Outliers rejected: {ts_metrics.num_outliers}")
        print(f"  Consensus confidence: {ts_metrics.consensus_confidence:.2%}")
        if ts_metrics.speedup_vs_sequential:
            print(f"  Speedup vs sequential: {ts_metrics.speedup_vs_sequential:.2f}x")

    # Quality comparison (simple MSE)
    std_result = standard_result.result_image
    ts_result = tom_sawyer_result.result_image

    mse = np.mean((std_result.astype(float) - ts_result.astype(float)) ** 2)
    psnr = 20 * np.log10(255.0 / np.sqrt(mse)) if mse > 0 else float('inf')

    print(f"\nQuality Metrics:")
    print(f"  MSE (std vs Tom Sawyer): {mse:.2f}")
    print(f"  PSNR: {psnr:.2f} dB")
    print(f"  Similarity: {(1.0 - mse / 65025.0) * 100:.1f}%")  # Normalize by max MSE


def main():
    """Main demonstration function."""
    parser = argparse.ArgumentParser(
        description="Tom Sawyer Method Demonstration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "--source",
        type=str,
        required=True,
        help="Path to source image (color donor)"
    )
    parser.add_argument(
        "--target",
        type=str,
        required=True,
        help="Path to target image (to be transformed)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="results/tom_sawyer_demo",
        help="Output directory for results (default: results/tom_sawyer_demo)"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=10,
        help="Number of Tom Sawyer workers (default: 10)"
    )
    parser.add_argument(
        "--algorithm",
        type=str,
        default="reinhard_lab",
        choices=["reinhard_lab", "reinhard_lch", "rgb_direct", "histogram_match"],
        help="Transfer algorithm (default: reinhard_lab)"
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Enable parallel worker execution"
    )

    args = parser.parse_args()

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print_section("Tom Sawyer Method - Demonstration")
    print(f"Source: {args.source}")
    print(f"Target: {args.target}")
    print(f"Output: {output_dir}")
    print(f"Workers: {args.workers}")
    print(f"Algorithm: {args.algorithm}")
    print(f"Parallel: {'Yes' if args.parallel else 'No'}")

    # Load images
    print_section("Loading Images")
    source = cv2.imread(args.source)
    target = cv2.imread(args.target)

    if source is None:
        print(f"Error: Failed to load source image: {args.source}")
        return 1

    if target is None:
        print(f"Error: Failed to load target image: {args.target}")
        return 1

    print(f"✓ Source loaded: {source.shape[1]}x{source.shape[0]} pixels")
    print(f"✓ Target loaded: {target.shape[1]}x{target.shape[0]} pixels")

    # Create configuration
    config = TransferConfig(
        algorithm=TransferAlgorithm(args.algorithm),
        blend_factor=1.0,
        clip_output=True
    )

    # Initialize orchestrator
    orchestrator = TransferOrchestrator()

    # Run standard processing
    print_section("Running Standard Processing")
    print("Processing with standard method...")

    start = time.time()
    standard_result = orchestrator.transfer(
        source, target, config,
        profile_performance=True
    )
    standard_time = time.time() - start

    print(f"✓ Standard processing complete ({standard_time:.3f}s)")

    # Save standard result
    std_output = output_dir / "standard_result.png"
    cv2.imwrite(str(std_output), standard_result.result_image)
    print(f"✓ Saved: {std_output}")

    # Run Tom Sawyer processing
    print_section("Running Tom Sawyer Processing")
    print(f"Processing with Tom Sawyer method ({args.workers} workers)...")

    start = time.time()
    tom_sawyer_result = orchestrator.transfer_tom_sawyer(
        source, target, config,
        num_workers=args.workers,
        variation_range=(0.85, 1.15),
        enable_parallel=args.parallel
    )
    tom_sawyer_time = time.time() - start

    print(f"✓ Tom Sawyer processing complete ({tom_sawyer_time:.3f}s)")

    # Save Tom Sawyer result
    ts_output = output_dir / "tom_sawyer_result.png"
    cv2.imwrite(str(ts_output), tom_sawyer_result.result_image)
    print(f"✓ Saved: {ts_output}")

    # Create comparison visualization
    print_section("Creating Comparison Visualization")

    # Stack images side by side
    h, w = target.shape[:2]
    comparison = np.zeros((h, w * 4, 3), dtype=np.uint8)
    comparison[:, :w] = source
    comparison[:, w:2*w] = target
    comparison[:, 2*w:3*w] = standard_result.result_image
    comparison[:, 3*w:4*w] = tom_sawyer_result.result_image

    # Add labels
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(comparison, "Source", (10, 30), font, 1.0, (255, 255, 255), 2)
    cv2.putText(comparison, "Target", (w + 10, 30), font, 1.0, (255, 255, 255), 2)
    cv2.putText(comparison, "Standard", (2*w + 10, 30), font, 1.0, (255, 255, 255), 2)
    cv2.putText(comparison, "Tom Sawyer", (3*w + 10, 30), font, 1.0, (255, 255, 255), 2)

    comp_output = output_dir / "comparison.png"
    cv2.imwrite(str(comp_output), comparison)
    print(f"✓ Comparison saved: {comp_output}")

    # Compare results
    compare_results(standard_result, tom_sawyer_result, source, target)

    # Summary
    print_section("Summary")
    print("✓ Demonstration complete!")
    print(f"\nResults saved to: {output_dir}/")
    print(f"  - standard_result.png")
    print(f"  - tom_sawyer_result.png")
    print(f"  - comparison.png")

    print(f"\nKey Findings:")
    time_overhead = (tom_sawyer_result.metrics.execution_time_ms / standard_result.metrics.execution_time_ms - 1.0) * 100
    print(f"  • Time overhead: {time_overhead:+.1f}%")

    if tom_sawyer_result.tom_sawyer_metrics:
        ts_m = tom_sawyer_result.tom_sawyer_metrics
        print(f"  • Consensus confidence: {ts_m.consensus_confidence:.1%}")
        print(f"  • Workers used: {ts_m.num_workers - ts_m.num_outliers}/{ts_m.num_workers}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
