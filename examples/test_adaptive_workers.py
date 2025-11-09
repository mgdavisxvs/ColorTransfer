#!/usr/bin/env python3
"""
Test Adaptive Worker Selection
===============================

Validates that the adaptive worker selection (Phase 18.1) correctly
auto-selects optimal worker counts based on image size.
"""

import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from color_transfer_framework.interface_layer.orchestrator import TransferOrchestrator
from color_transfer_framework.transfer_engine import TransferConfig, TransferAlgorithm


def test_adaptive_workers():
    """Test adaptive worker selection across different image sizes."""
    print("=" * 70)
    print("ADAPTIVE WORKER SELECTION TEST (Phase 18.1)")
    print("=" * 70)

    orchestrator = TransferOrchestrator()
    config = TransferConfig(algorithm=TransferAlgorithm.REINHARD_LAB)

    # Test different image sizes
    test_cases = [
        (256, 256, 4, "Small: 256x256 (65k pixels)"),
        (512, 512, 4, "Small: 512x512 (262k pixels)"),
        (600, 600, 6, "Medium: 600x600 (360k pixels)"),
        (900, 900, 6, "Medium: 900x900 (810k pixels)"),
        (1024, 1024, 8, "Large: 1024x1024 (1M pixels)"),  # >= 1M threshold
        (1200, 1200, 8, "Large: 1200x1200 (1.4M pixels)"),
        (2048, 2048, 8, "Large: 2048x2048 (4.2M pixels)"),
    ]

    print(f"\n{'Image Size':<25} {'Pixels':<15} {'Expected':<10} {'Actual':<10} {'Status':<10}\n{'-' * 70}")

    all_passed = True

    for width, height, expected_workers, description in test_cases:
        # Create test images
        source = np.random.randint(0, 256, (height, width, 3), dtype=np.uint8)
        target = np.random.randint(0, 256, (height, width, 3), dtype=np.uint8)

        # Run with auto-selection (num_workers=None)
        result = orchestrator.transfer_tom_sawyer(
            source, target,
            config=config,
            num_workers=None,  # Auto-select
            enable_parallel=True
        )

        actual_workers = result.tom_sawyer_metrics.num_workers
        pixels = width * height
        status = "✅ PASS" if actual_workers == expected_workers else "❌ FAIL"

        if actual_workers != expected_workers:
            all_passed = False

        print(f"{description:<25} {pixels:>12,} px   {expected_workers:<10} {actual_workers:<10} {status}")

    print(f"\n{'=' * 70}")
    if all_passed:
        print("✅ ALL TESTS PASSED - Adaptive worker selection working correctly")
    else:
        print("❌ SOME TESTS FAILED - Review adaptive worker logic")

    # Performance test with adaptive workers
    print(f"\n{'=' * 70}")
    print("PERFORMANCE COMPARISON (512x512 image)")
    print(f"{'=' * 70}\n")

    source_512 = np.random.randint(0, 256, (512, 512, 3), dtype=np.uint8)
    target_512 = np.random.randint(0, 256, (512, 512, 3), dtype=np.uint8)

    # Standard
    std_result = orchestrator.transfer(source_512, target_512, config=config)
    std_time = std_result.metrics.execution_time_ms

    # Tom Sawyer (auto-select)
    ts_result = orchestrator.transfer_tom_sawyer(
        source_512, target_512,
        config=config,
        num_workers=None  # Auto-select (should choose 4)
    )
    ts_time = ts_result.metrics.execution_time_ms
    ts_workers = ts_result.tom_sawyer_metrics.num_workers
    overhead = (ts_time / std_time - 1) * 100

    print(f"Standard processing:     {std_time:.2f} ms")
    print(f"Tom Sawyer (auto={ts_workers} workers): {ts_time:.2f} ms")
    print(f"Overhead:                {overhead:+.1f}%")
    print(f"Consensus confidence:    {ts_result.tom_sawyer_metrics.consensus_confidence:.2f}%")

    if overhead < 50:
        print(f"\n✅ EXCELLENT: Overhead < 50% (production-ready)")
    elif overhead < 100:
        print(f"\n✅ GOOD: Overhead < 100% (acceptable)")
    else:
        print(f"\n⚠️  HIGH: Overhead > 100% (needs investigation)")

    print(f"\n{'=' * 70}")
    print("TEST COMPLETE")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    test_adaptive_workers()
