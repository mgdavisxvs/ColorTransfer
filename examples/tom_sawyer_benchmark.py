#!/usr/bin/env python3
"""
Tom Sawyer Method - Benchmark Script
=====================================

Comprehensive benchmarking script for evaluating Tom Sawyer method
performance and quality improvements.

Usage:
    python examples/tom_sawyer_benchmark.py \
        --source source.jpg \
        --target target.jpg \
        --runs 5 \
        --output-dir results/benchmarks

Metrics:
    - Processing time (standard vs Tom Sawyer)
    - Memory usage
    - Quality metrics (MSE, PSNR, SSIM)
    - Consensus confidence
    - Outlier detection rate
"""

import argparse
import sys
import time
import json
from pathlib import Path
from typing import List, Dict
import cv2
import numpy as np
from tabulate import tabulate

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from color_transfer_framework.interface_layer.orchestrator import TransferOrchestrator
from color_transfer_framework.transfer_engine import TransferConfig, TransferAlgorithm


def calculate_mse(img1: np.ndarray, img2: np.ndarray) -> float:
    """Calculate Mean Squared Error between two images."""
    return float(np.mean((img1.astype(float) - img2.astype(float)) ** 2))


def calculate_psnr(img1: np.ndarray, img2: np.ndarray) -> float:
    """Calculate Peak Signal-to-Noise Ratio."""
    mse = calculate_mse(img1, img2)
    if mse == 0:
        return float('inf')
    max_pixel = 255.0
    return 20 * np.log10(max_pixel / np.sqrt(mse))


def calculate_ssim(img1: np.ndarray, img2: np.ndarray) -> float:
    """Calculate Structural Similarity Index (simplified version)."""
    # Convert to grayscale
    gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

    # Calculate means
    mu1 = gray1.mean()
    mu2 = gray2.mean()

    # Calculate variances and covariance
    sigma1_sq = ((gray1 - mu1) ** 2).mean()
    sigma2_sq = ((gray2 - mu2) ** 2).mean()
    sigma12 = ((gray1 - mu1) * (gray2 - mu2)).mean()

    # SSIM constants
    C1 = (0.01 * 255) ** 2
    C2 = (0.03 * 255) ** 2

    # Calculate SSIM
    numerator = (2 * mu1 * mu2 + C1) * (2 * sigma12 + C2)
    denominator = (mu1 ** 2 + mu2 ** 2 + C1) * (sigma1_sq + sigma2_sq + C2)

    ssim = numerator / denominator
    return float(ssim)


def run_benchmark(
    source: np.ndarray,
    target: np.ndarray,
    algorithm: str,
    num_runs: int = 5
) -> Dict:
    """
    Run comprehensive benchmark comparing standard vs Tom Sawyer.

    Args:
        source: Source image
        target: Target image
        algorithm: Algorithm name
        num_runs: Number of runs for averaging

    Returns:
        Dictionary with benchmark results
    """
    orchestrator = TransferOrchestrator()
    config = TransferConfig(
        algorithm=TransferAlgorithm(algorithm),
        blend_factor=1.0
    )

    print(f"\nRunning benchmark: {algorithm}")
    print(f"  Image size: {target.shape[1]}x{target.shape[0]}")
    print(f"  Number of runs: {num_runs}")
    print("  " + "=" * 60)

    # Standard processing
    print("\n  Standard Processing:")
    standard_times = []
    standard_memories = []
    standard_result = None

    for i in range(num_runs):
        print(f"    Run {i + 1}/{num_runs}... ", end="", flush=True)
        result = orchestrator.transfer(source, target, config, profile_performance=True)
        standard_times.append(result.metrics.execution_time_ms)
        standard_memories.append(result.metrics.memory_used_mb)
        if i == 0:
            standard_result = result.result_image
        print(f"✓ {result.metrics.execution_time_ms:.2f}ms")

    # Tom Sawyer processing
    print("\n  Tom Sawyer Processing:")
    tom_sawyer_times = []
    tom_sawyer_memories = []
    tom_sawyer_confidences = []
    tom_sawyer_outliers = []
    tom_sawyer_result = None

    for i in range(num_runs):
        print(f"    Run {i + 1}/{num_runs}... ", end="", flush=True)
        result = orchestrator.transfer_tom_sawyer(
            source, target, config,
            num_workers=10,
            variation_range=(0.85, 1.15),
            enable_parallel=True
        )
        tom_sawyer_times.append(result.metrics.execution_time_ms)
        tom_sawyer_memories.append(result.metrics.memory_used_mb)
        tom_sawyer_confidences.append(result.tom_sawyer_metrics.consensus_confidence)
        tom_sawyer_outliers.append(result.tom_sawyer_metrics.num_outliers)
        if i == 0:
            tom_sawyer_result = result.result_image
        print(
            f"✓ {result.metrics.execution_time_ms:.2f}ms "
            f"(confidence: {result.tom_sawyer_metrics.consensus_confidence:.1%})"
        )

    # Calculate statistics
    std_time_avg = np.mean(standard_times)
    std_time_std = np.std(standard_times)
    ts_time_avg = np.mean(tom_sawyer_times)
    ts_time_std = np.std(tom_sawyer_times)

    time_overhead = (ts_time_avg / std_time_avg - 1.0) * 100

    std_mem_avg = np.mean(standard_memories)
    ts_mem_avg = np.mean(tom_sawyer_memories)
    mem_overhead = (ts_mem_avg / std_mem_avg - 1.0) * 100

    # Quality metrics (standard vs Tom Sawyer)
    mse = calculate_mse(standard_result, tom_sawyer_result)
    psnr = calculate_psnr(standard_result, tom_sawyer_result)
    ssim = calculate_ssim(standard_result, tom_sawyer_result)
    similarity = (1.0 - mse / 65025.0) * 100  # Normalize by max MSE

    # Compile results
    results = {
        "algorithm": algorithm,
        "image_size": f"{target.shape[1]}x{target.shape[0]}",
        "num_runs": num_runs,
        "standard": {
            "time_avg_ms": float(std_time_avg),
            "time_std_ms": float(std_time_std),
            "memory_avg_mb": float(std_mem_avg),
        },
        "tom_sawyer": {
            "time_avg_ms": float(ts_time_avg),
            "time_std_ms": float(ts_time_std),
            "memory_avg_mb": float(ts_mem_avg),
            "confidence_avg": float(np.mean(tom_sawyer_confidences)),
            "outliers_avg": float(np.mean(tom_sawyer_outliers)),
        },
        "overhead": {
            "time_pct": float(time_overhead),
            "memory_pct": float(mem_overhead),
        },
        "quality": {
            "mse": float(mse),
            "psnr": float(psnr),
            "ssim": float(ssim),
            "similarity_pct": float(similarity),
        },
    }

    return results, standard_result, tom_sawyer_result


def print_results(results: Dict):
    """Print benchmark results in formatted table."""
    print("\n" + "=" * 80)
    print("BENCHMARK RESULTS")
    print("=" * 80)

    # Performance comparison
    perf_table = [
        ["Metric", "Standard", "Tom Sawyer", "Overhead"],
        [
            "Processing Time",
            f"{results['standard']['time_avg_ms']:.2f} ± {results['standard']['time_std_ms']:.2f} ms",
            f"{results['tom_sawyer']['time_avg_ms']:.2f} ± {results['tom_sawyer']['time_std_ms']:.2f} ms",
            f"{results['overhead']['time_pct']:+.1f}%",
        ],
        [
            "Memory Usage",
            f"{results['standard']['memory_avg_mb']:.2f} MB",
            f"{results['tom_sawyer']['memory_avg_mb']:.2f} MB",
            f"{results['overhead']['memory_pct']:+.1f}%",
        ],
    ]

    print("\nPerformance Comparison:")
    print(tabulate(perf_table, headers="firstrow", tablefmt="grid"))

    # Tom Sawyer specific metrics
    ts_table = [
        ["Metric", "Value"],
        ["Consensus Confidence", f"{results['tom_sawyer']['confidence_avg']:.2%}"],
        ["Outliers Detected (avg)", f"{results['tom_sawyer']['outliers_avg']:.1f}"],
    ]

    print("\nTom Sawyer Metrics:")
    print(tabulate(ts_table, headers="firstrow", tablefmt="grid"))

    # Quality metrics
    quality_table = [
        ["Metric", "Value", "Description"],
        ["MSE", f"{results['quality']['mse']:.2f}", "Lower is better"],
        ["PSNR", f"{results['quality']['psnr']:.2f} dB", "Higher is better (>30dB is good)"],
        ["SSIM", f"{results['quality']['ssim']:.4f}", "Closer to 1.0 is better"],
        ["Similarity", f"{results['quality']['similarity_pct']:.1f}%", "Closer to 100% is better"],
    ]

    print("\nQuality Metrics (Standard vs Tom Sawyer):")
    print(tabulate(quality_table, headers="firstrow", tablefmt="grid"))


def main():
    """Main benchmark function."""
    parser = argparse.ArgumentParser(
        description="Tom Sawyer Method Benchmark",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--source", type=str, required=True, help="Path to source image")
    parser.add_argument("--target", type=str, required=True, help="Path to target image")
    parser.add_argument(
        "--algorithm",
        type=str,
        default="reinhard_lab",
        choices=["reinhard_lab", "reinhard_lch", "rgb_direct", "histogram_match"],
        help="Transfer algorithm",
    )
    parser.add_argument(
        "--runs", type=int, default=5, help="Number of runs for averaging (default: 5)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="results/benchmarks",
        help="Output directory for results",
    )

    args = parser.parse_args()

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("TOM SAWYER METHOD - BENCHMARK")
    print("=" * 80)
    print(f"\nConfiguration:")
    print(f"  Source: {args.source}")
    print(f"  Target: {args.target}")
    print(f"  Algorithm: {args.algorithm}")
    print(f"  Runs: {args.runs}")
    print(f"  Output: {output_dir}")

    # Load images
    print("\nLoading images...")
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

    # Run benchmark
    results, std_result, ts_result = run_benchmark(
        source, target, args.algorithm, args.runs
    )

    # Print results
    print_results(results)

    # Save results
    json_path = output_dir / f"benchmark_{args.algorithm}.json"
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n✓ Results saved: {json_path}")

    # Save images
    std_output = output_dir / f"standard_{args.algorithm}.png"
    ts_output = output_dir / f"tom_sawyer_{args.algorithm}.png"

    cv2.imwrite(str(std_output), std_result)
    cv2.imwrite(str(ts_output), ts_result)

    print(f"✓ Standard result saved: {std_output}")
    print(f"✓ Tom Sawyer result saved: {ts_output}")

    # Create side-by-side comparison
    h, w = target.shape[:2]
    comparison = np.zeros((h, w * 3, 3), dtype=np.uint8)
    comparison[:, :w] = target
    comparison[:, w : 2 * w] = std_result
    comparison[:, 2 * w : 3 * w] = ts_result

    # Add labels
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(comparison, "Target", (10, 30), font, 1.0, (255, 255, 255), 2)
    cv2.putText(comparison, "Standard", (w + 10, 30), font, 1.0, (255, 255, 255), 2)
    cv2.putText(comparison, "Tom Sawyer", (2 * w + 10, 30), font, 1.0, (255, 255, 255), 2)

    comp_output = output_dir / f"comparison_{args.algorithm}.png"
    cv2.imwrite(str(comp_output), comparison)
    print(f"✓ Comparison saved: {comp_output}")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"\nTime overhead: {results['overhead']['time_pct']:+.1f}%")
    print(f"Memory overhead: {results['overhead']['memory_pct']:+.1f}%")
    print(f"Consensus confidence: {results['tom_sawyer']['confidence_avg']:.1%}")
    print(f"Results similarity: {results['quality']['similarity_pct']:.1f}%")

    if results['quality']['psnr'] > 40:
        print("\n✅ Excellent similarity (PSNR > 40dB)")
    elif results['quality']['psnr'] > 30:
        print("\n✅ Good similarity (PSNR > 30dB)")
    else:
        print("\n⚠️  Moderate similarity (PSNR < 30dB)")

    return 0


if __name__ == "__main__":
    try:
        # Try to import tabulate
        from tabulate import tabulate
    except ImportError:
        print("Warning: tabulate module not found. Install with: pip install tabulate")
        print("Tables will be displayed in simple format.\n")

        # Fallback simple table function
        def tabulate(data, headers=None, tablefmt=None):
            return "\n".join(["\t".join(map(str, row)) for row in data])

    sys.exit(main())
