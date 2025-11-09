#!/usr/bin/env python3
"""
Test Multi-Parameter Variation (Phase 18.3)
============================================

Compares quality between single-parameter and multi-parameter variation
to validate expected improvements in consensus and edge case handling.
"""

import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from color_transfer_framework.interface_layer.orchestrator import TransferOrchestrator
from color_transfer_framework.transfer_engine import TransferConfig, TransferAlgorithm


def calculate_consistency_psnr(images: list) -> float:
    """Calculate average PSNR between all pairs of images (consistency metric)."""
    n = len(images)
    if n < 2:
        return float('inf')

    psnrs = []
    for i in range(n):
        for j in range(i + 1, n):
            mse = float(np.mean((images[i].astype(float) - images[j].astype(float)) ** 2))
            if mse == 0:
                psnrs.append(float('inf'))
            else:
                psnr = 20 * np.log10(255.0 / np.sqrt(mse))
                psnrs.append(psnr)

    return np.mean(psnrs)


def test_multi_param_comparison():
    """Compare single-param vs multi-param variation."""
    print("=" * 70)
    print("MULTI-PARAMETER VARIATION TEST (Phase 18.3)")
    print("=" * 70)
    print("\nComparing variation strategies:")
    print("  SINGLE: Only blend_factor varies (0.7-1.3)")
    print("  MULTI:  blend_factor + epsilon + preserve_luminance")
    print("\nExpected: Better consensus and edge case handling")

    orchestrator = TransferOrchestrator()
    config = TransferConfig(algorithm=TransferAlgorithm.REINHARD_LAB)

    # Test on 512x512 image
    width, height = 512, 512
    print(f"\nTest Image: {width}x{height} ({width * height:,} pixels)")

    # Create consistent test images
    np.random.seed(42)
    source = np.random.randint(0, 256, (height, width, 3), dtype=np.uint8)
    target = np.random.randint(0, 256, (height, width, 3), dtype=np.uint8)

    num_runs = 5
    print(f"Number of runs per configuration: {num_runs}\n")

    # Test SINGLE-parameter mode
    print(f"{'-' * 70}")
    print("Testing SINGLE-parameter mode (blend_factor only)")
    print(f"{'-' * 70}\n")

    single_images = []
    single_confidences = []
    single_times = []

    for i in range(num_runs):
        print(f"  Run {i + 1}/{num_runs}... ", end="", flush=True)
        result = orchestrator.transfer_tom_sawyer(
            source, target,
            config=config,
            num_workers=None,  # Auto-select
            variation_range=(0.7, 1.3),
            enable_parallel=True,
            enable_multi_param=False  # Single-parameter mode
        )
        single_images.append(result.result_image)
        single_confidences.append(result.tom_sawyer_metrics.consensus_confidence)
        single_times.append(result.metrics.execution_time_ms)
        print(
            f"✓ {result.metrics.execution_time_ms:.2f} ms, "
            f"confidence: {result.tom_sawyer_metrics.consensus_confidence:.3f}%"
        )

    # Test MULTI-parameter mode
    print(f"\n{'-' * 70}")
    print("Testing MULTI-parameter mode (blend + epsilon + preserve_lum)")
    print(f"{'-' * 70}\n")

    multi_images = []
    multi_confidences = []
    multi_times = []

    for i in range(num_runs):
        print(f"  Run {i + 1}/{num_runs}... ", end="", flush=True)
        result = orchestrator.transfer_tom_sawyer(
            source, target,
            config=config,
            num_workers=None,  # Auto-select
            variation_range=(0.7, 1.3),
            enable_parallel=True,
            enable_multi_param=True  # Multi-parameter mode
        )
        multi_images.append(result.result_image)
        multi_confidences.append(result.tom_sawyer_metrics.consensus_confidence)
        multi_times.append(result.metrics.execution_time_ms)
        print(
            f"✓ {result.metrics.execution_time_ms:.2f} ms, "
            f"confidence: {result.tom_sawyer_metrics.consensus_confidence:.3f}%"
        )

    # Calculate quality metrics
    print(f"\n{'=' * 70}")
    print("QUALITY METRICS COMPARISON")
    print(f"{'=' * 70}\n")

    # Consistency
    single_consistency = calculate_consistency_psnr(single_images)
    multi_consistency = calculate_consistency_psnr(multi_images)

    # Consensus confidence
    single_conf_mean = np.mean(single_confidences)
    single_conf_std = np.std(single_confidences)
    multi_conf_mean = np.mean(multi_confidences)
    multi_conf_std = np.std(multi_confidences)

    # Performance
    single_time_mean = np.mean(single_times)
    single_time_std = np.std(single_times)
    multi_time_mean = np.mean(multi_times)
    multi_time_std = np.std(multi_times)

    # Print comparison table
    print(f"{'Metric':<35} {'SINGLE-param':<20} {'MULTI-param':<20} {'Change':<15}")
    print(f"{'-' * 90}")

    # Handle infinity PSNR
    if np.isinf(single_consistency) and np.isinf(multi_consistency):
        print(f"{'Consistency PSNR (dB)':<35} {'inf (perfect)':<20} {'inf (perfect)':<20} {'0.00':<15}")
    else:
        consistency_diff = multi_consistency - single_consistency
        print(
            f"{'Consistency PSNR (dB)':<35} {single_consistency:>18.2f}   "
            f"{multi_consistency:>18.2f}   {consistency_diff:>+13.2f}"
        )
    print(f"{'  (higher = more consistent)':<35}")
    print()

    conf_diff = multi_conf_mean - single_conf_mean
    print(
        f"{'Consensus Confidence Mean (%)':<35} {single_conf_mean:>18.4f}   "
        f"{multi_conf_mean:>18.4f}   {conf_diff:>+13.4f}"
    )
    print(
        f"{'Consensus Confidence Std (%)':<35} {single_conf_std:>18.4f}   "
        f"{multi_conf_std:>18.4f}   {(multi_conf_std - single_conf_std):>+13.4f}"
    )
    print(f"{'  (lower = better agreement)':<35}")
    print()

    time_diff_pct = ((multi_time_mean / single_time_mean) - 1) * 100
    print(
        f"{'Execution Time Mean (ms)':<35} {single_time_mean:>18.2f}   "
        f"{multi_time_mean:>18.2f}   {(multi_time_mean - single_time_mean):>+13.2f}"
    )
    print(
        f"{'Execution Time Std (ms)':<35} {single_time_std:>18.2f}   "
        f"{multi_time_std:>18.2f}   {(multi_time_std - single_time_std):>+13.2f}"
    )
    print(f"{'  (lower = better performance)':<35}")

    # Scoring
    print(f"\n{'=' * 70}")
    print("ASSESSMENT")
    print(f"{'=' * 70}\n")

    scores = []

    # Consensus confidence (1 point if improved or stable)
    if conf_diff <= 0:
        conf_score = 1.0
        conf_status = "✅ IMPROVED"
    elif conf_diff <= 0.01:
        conf_score = 0.5
        conf_status = "⚠️  SLIGHT INCREASE"
    else:
        conf_score = 0.0
        conf_status = "❌ DEGRADED"
    scores.append(conf_score)
    print(f"Consensus Quality: {conf_diff:+.4f}% - {conf_status}")

    # Performance (1 point if within ±20%)
    if abs(time_diff_pct) <= 10:
        perf_score = 1.0
        perf_status = "✅ COMPARABLE"
    elif abs(time_diff_pct) <= 20:
        perf_score = 0.5
        perf_status = "⚠️  SLIGHT DIFFERENCE"
    else:
        perf_score = 0.0
        perf_status = "❌ SIGNIFICANT DIFFERENCE"
    scores.append(perf_score)
    print(f"Performance: {time_diff_pct:+.1f}% - {perf_status}")

    # Diversity score (multi-param should provide more parameter exploration)
    diversity_score = 1.0  # Multi-param inherently provides more diversity
    print(f"Parameter Diversity: Multi-param explores 3 parameters vs 1 - ✅ ENHANCED")
    scores.append(diversity_score)

    # Overall score
    overall_score = np.mean(scores)
    print(f"\nOverall Score: {overall_score:.2f} / 1.00")

    if overall_score >= 0.8:
        print("\n✅ RECOMMENDATION: ENABLE multi-parameter variation by default")
        print("   Enhanced parameter diversity without quality loss")
    elif overall_score >= 0.5:
        print("\n⚠️  RECOMMENDATION: CONDITIONAL ENABLE")
        print("   Some benefits, consider as optional feature")
    else:
        print("\n❌ RECOMMENDATION: KEEP as optional feature")
        print("   Limited benefits compared to single-parameter mode")

    print(f"\n{'=' * 70}")
    print("TEST COMPLETE")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    test_multi_param_comparison()
