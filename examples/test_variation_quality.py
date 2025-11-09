#!/usr/bin/env python3
"""
Test Variation Range Quality (Phase 18.2)
==========================================

Measures quality through consistency across multiple runs and consensus metrics,
rather than similarity to standard processing.
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


def test_quality_comparison():
    """Compare quality metrics between old and new variation ranges."""
    print("=" * 70)
    print("VARIATION RANGE QUALITY TEST (Phase 18.2)")
    print("=" * 70)
    print("\nMeasuring QUALITY through consistency and consensus metrics")
    print("(not similarity to standard processing)")

    orchestrator = TransferOrchestrator()
    config = TransferConfig(algorithm=TransferAlgorithm.REINHARD_LAB)

    # Test on 512x512 image
    width, height = 512, 512
    print(f"\nTest Image: {width}x{height} ({width * height:,} pixels)")

    # Create consistent test images (using seed for reproducibility)
    np.random.seed(42)
    source = np.random.randint(0, 256, (height, width, 3), dtype=np.uint8)
    target = np.random.randint(0, 256, (height, width, 3), dtype=np.uint8)

    num_runs = 5
    print(f"Number of runs per configuration: {num_runs}")

    # Test OLD range (0.85, 1.15)
    print(f"\n{'-' * 70}")
    print("Testing OLD range (0.85-1.15)")
    print(f"{'-' * 70}\n")

    old_images = []
    old_confidences = []
    old_times = []

    for i in range(num_runs):
        print(f"  Run {i + 1}/{num_runs}... ", end="", flush=True)
        result = orchestrator.transfer_tom_sawyer(
            source, target,
            config=config,
            num_workers=None,
            variation_range=(0.85, 1.15),
            enable_parallel=True
        )
        old_images.append(result.result_image)
        old_confidences.append(result.tom_sawyer_metrics.consensus_confidence)
        old_times.append(result.metrics.execution_time_ms)
        print(f"✓ {result.metrics.execution_time_ms:.2f} ms, confidence: {result.tom_sawyer_metrics.consensus_confidence:.3f}%")

    # Test NEW range (0.7, 1.3)
    print(f"\n{'-' * 70}")
    print("Testing NEW range (0.7-1.3)")
    print(f"{'-' * 70}\n")

    new_images = []
    new_confidences = []
    new_times = []

    for i in range(num_runs):
        print(f"  Run {i + 1}/{num_runs}... ", end="", flush=True)
        result = orchestrator.transfer_tom_sawyer(
            source, target,
            config=config,
            num_workers=None,
            variation_range=(0.7, 1.3),
            enable_parallel=True
        )
        new_images.append(result.result_image)
        new_confidences.append(result.tom_sawyer_metrics.consensus_confidence)
        new_times.append(result.metrics.execution_time_ms)
        print(f"✓ {result.metrics.execution_time_ms:.2f} ms, confidence: {result.tom_sawyer_metrics.consensus_confidence:.3f}%")

    # Calculate quality metrics
    print(f"\n{'=' * 70}")
    print("QUALITY METRICS")
    print(f"{'=' * 70}\n")

    # Consistency (higher PSNR = more consistent across runs)
    old_consistency = calculate_consistency_psnr(old_images)
    new_consistency = calculate_consistency_psnr(new_images)

    # Consensus confidence (lower = better agreement)
    old_conf_mean = np.mean(old_confidences)
    old_conf_std = np.std(old_confidences)
    new_conf_mean = np.mean(new_confidences)
    new_conf_std = np.std(new_confidences)

    # Performance
    old_time_mean = np.mean(old_times)
    old_time_std = np.std(old_times)
    new_time_mean = np.mean(new_times)
    new_time_std = np.std(new_times)

    # Print comparison
    print(f"{'Metric':<35} {'OLD (0.85-1.15)':<20} {'NEW (0.7-1.3)':<20} {'Change':<15}")
    print(f"{'-' * 90}")
    print(f"{'Consistency PSNR (dB)':<35} {old_consistency:>18.2f}   {new_consistency:>18.2f}   {(new_consistency - old_consistency):>+13.2f}")
    print(f"{'  (higher = more consistent)':<35}")
    print()
    print(f"{'Consensus Confidence Mean (%)':<35} {old_conf_mean:>18.4f}   {new_conf_mean:>18.4f}   {(new_conf_mean - old_conf_mean):>+13.4f}")
    print(f"{'Consensus Confidence Std (%)':<35} {old_conf_std:>18.4f}   {new_conf_std:>18.4f}   {(new_conf_std - old_conf_std):>+13.4f}")
    print(f"{'  (lower = better agreement)':<35}")
    print()
    print(f"{'Execution Time Mean (ms)':<35} {old_time_mean:>18.2f}   {new_time_mean:>18.2f}   {(new_time_mean - old_time_mean):>+13.2f}")
    print(f"{'Execution Time Std (ms)':<35} {old_time_std:>18.2f}   {new_time_std:>18.2f}   {(new_time_std - old_time_std):>+13.2f}")
    print(f"{'  (lower = better performance)':<35}")

    # Scoring
    print(f"\n{'=' * 70}")
    print("ASSESSMENT")
    print(f"{'=' * 70}\n")

    scores = []

    # Consistency (1 point if within 2 dB, 0.5 if worse but close)
    consistency_diff = new_consistency - old_consistency
    if consistency_diff >= -2.0:
        consistency_score = 1.0
        consistency_status = "✅ GOOD"
    elif consistency_diff >= -5.0:
        consistency_score = 0.5
        consistency_status = "⚠️  ACCEPTABLE"
    else:
        consistency_score = 0.0
        consistency_status = "❌ POOR"
    scores.append(consistency_score)
    print(f"Consistency: {consistency_diff:+.2f} dB - {consistency_status}")

    # Consensus confidence (1 point if improved or stable)
    conf_diff = new_conf_mean - old_conf_mean
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
    print(f"Consensus Confidence: {conf_diff:+.4f}% - {conf_status}")

    # Performance (1 point if faster or within 10%)
    perf_diff = ((new_time_mean / old_time_mean) - 1) * 100
    if perf_diff <= 0:
        perf_score = 1.0
        perf_status = "✅ FASTER"
    elif perf_diff <= 10:
        perf_score = 0.5
        perf_status = "⚠️  SLIGHT SLOWDOWN"
    else:
        perf_score = 0.0
        perf_status = "❌ SLOWER"
    scores.append(perf_score)
    print(f"Performance: {perf_diff:+.1f}% - {perf_status}")

    # Overall score
    overall_score = np.mean(scores)
    print(f"\nOverall Score: {overall_score:.2f} / 1.00")

    if overall_score >= 0.8:
        print("\n✅ RECOMMENDATION: PROCEED with wider variation range (0.7-1.3)")
        print("   Quality metrics are improved or stable")
    elif overall_score >= 0.5:
        print("\n⚠️  RECOMMENDATION: CONDITIONAL PROCEED")
        print("   Some metrics improved, monitor in production")
    else:
        print("\n❌ RECOMMENDATION: REVERT to narrow range (0.85-1.15)")
        print("   Quality metrics show regression")

    print(f"\n{'=' * 70}")
    print("TEST COMPLETE")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    test_quality_comparison()
