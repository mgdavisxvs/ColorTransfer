#!/usr/bin/env python3
"""
Test Wider Variation Range (Phase 18.2)
========================================

Compares PSNR quality between old (0.85-1.15) and new (0.7-1.3)
variation ranges to validate expected +0.3-0.5 dB improvement.
"""

import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from color_transfer_framework.interface_layer.orchestrator import TransferOrchestrator
from color_transfer_framework.transfer_engine import TransferConfig, TransferAlgorithm


def calculate_psnr(img1: np.ndarray, img2: np.ndarray) -> float:
    """Calculate Peak Signal-to-Noise Ratio."""
    mse = float(np.mean((img1.astype(float) - img2.astype(float)) ** 2))
    if mse == 0:
        return float('inf')
    max_pixel = 255.0
    return 20 * np.log10(max_pixel / np.sqrt(mse))


def test_variation_range_comparison():
    """Compare old vs new variation ranges."""
    print("=" * 70)
    print("VARIATION RANGE COMPARISON TEST (Phase 18.2)")
    print("=" * 70)

    orchestrator = TransferOrchestrator()
    config = TransferConfig(algorithm=TransferAlgorithm.REINHARD_LAB)

    # Test different image sizes
    test_cases = [
        (512, 512, "Small: 512x512"),
        (1024, 1024, "Large: 1024x1024"),
    ]

    print(f"\nComparing variation ranges:")
    print(f"  OLD: (0.85, 1.15) - Narrow range")
    print(f"  NEW: (0.7, 1.3)   - Wider range")
    print(f"\nExpected improvement: +0.3 to +0.5 dB PSNR\n")

    all_improvements = []

    for width, height, description in test_cases:
        print(f"\n{'-' * 70}")
        print(f"Testing: {description} ({width * height:,} pixels)")
        print(f"{'-' * 70}\n")

        # Create test images
        source = np.random.randint(0, 256, (height, width, 3), dtype=np.uint8)
        target = np.random.randint(0, 256, (height, width, 3), dtype=np.uint8)

        # Get reference (standard processing)
        print("Running standard processing (reference)...", end=" ", flush=True)
        std_result = orchestrator.transfer(source, target, config=config)
        std_image = std_result.result_image
        std_time = std_result.metrics.execution_time_ms
        print(f"✓ {std_time:.2f} ms")

        # OLD variation range (0.85, 1.15)
        print("Running Tom Sawyer with OLD range (0.85-1.15)...", end=" ", flush=True)
        old_result = orchestrator.transfer_tom_sawyer(
            source, target,
            config=config,
            num_workers=None,  # Auto-select
            variation_range=(0.85, 1.15),
            enable_parallel=True
        )
        old_image = old_result.result_image
        old_time = old_result.metrics.execution_time_ms
        old_workers = old_result.tom_sawyer_metrics.num_workers
        old_confidence = old_result.tom_sawyer_metrics.consensus_confidence
        print(f"✓ {old_time:.2f} ms ({old_workers} workers)")

        # NEW variation range (0.7, 1.3)
        print("Running Tom Sawyer with NEW range (0.7-1.3)...", end=" ", flush=True)
        new_result = orchestrator.transfer_tom_sawyer(
            source, target,
            config=config,
            num_workers=None,  # Auto-select
            variation_range=(0.7, 1.3),
            enable_parallel=True
        )
        new_image = new_result.result_image
        new_time = new_result.metrics.execution_time_ms
        new_workers = new_result.tom_sawyer_metrics.num_workers
        new_confidence = new_result.tom_sawyer_metrics.consensus_confidence
        print(f"✓ {new_time:.2f} ms ({new_workers} workers)")

        # Calculate PSNR (higher is better - closer to reference)
        old_psnr = calculate_psnr(std_image, old_image)
        new_psnr = calculate_psnr(std_image, new_image)
        psnr_improvement = new_psnr - old_psnr

        # Calculate overhead
        old_overhead = (old_time / std_time - 1) * 100
        new_overhead = (new_time / std_time - 1) * 100
        overhead_change = new_overhead - old_overhead

        all_improvements.append(psnr_improvement)

        # Print results
        print(f"\n{'Metric':<30} {'OLD (0.85-1.15)':<20} {'NEW (0.7-1.3)':<20} {'Change':<15}")
        print(f"{'-' * 85}")
        print(f"{'PSNR vs Standard (dB)':<30} {old_psnr:>18.2f}   {new_psnr:>18.2f}   {psnr_improvement:>+13.2f}")
        print(f"{'Consensus Confidence (%)':<30} {old_confidence:>18.2f}   {new_confidence:>18.2f}   {(new_confidence - old_confidence):>+13.2f}")
        print(f"{'Time Overhead (%)':<30} {old_overhead:>18.1f}   {new_overhead:>18.1f}   {overhead_change:>+13.1f}")

        # Interpretation
        if psnr_improvement >= 0.3:
            status = "✅ TARGET MET"
        elif psnr_improvement >= 0:
            status = "⚠️  SLIGHT IMPROVEMENT"
        else:
            status = "❌ REGRESSION"

        print(f"\nPSNR Improvement: {psnr_improvement:+.2f} dB - {status}")

    # Overall summary
    print(f"\n{'=' * 70}")
    print("SUMMARY")
    print(f"{'=' * 70}\n")

    mean_improvement = np.mean(all_improvements)
    std_improvement = np.std(all_improvements)

    print(f"Mean PSNR Improvement: {mean_improvement:+.2f} dB")
    print(f"Std Dev:               {std_improvement:.2f} dB")
    print(f"Target Range:          +0.3 to +0.5 dB")

    if mean_improvement >= 0.3:
        print(f"\n✅ SUCCESS: Wider variation range achieves target improvement")
        print(f"   Recommendation: PROCEED with Phase 18.2 implementation")
    elif mean_improvement >= 0:
        print(f"\n⚠️  MARGINAL: Improvement below target but positive")
        print(f"   Recommendation: Consider additional tuning or accept marginal gain")
    else:
        print(f"\n❌ REGRESSION: Wider variation range reduces quality")
        print(f"   Recommendation: Investigate or revert to narrow range")

    print(f"\n{'=' * 70}")
    print("TEST COMPLETE")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    test_variation_range_comparison()
