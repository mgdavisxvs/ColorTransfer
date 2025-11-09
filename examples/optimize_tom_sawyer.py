#!/usr/bin/env python3
"""
Optimize Tom Sawyer Configuration
==================================

Find the optimal number of workers and parallel workers to minimize overhead
while maintaining quality.
"""

import sys
from pathlib import Path
import numpy as np
import time

sys.path.insert(0, str(Path(__file__).parent.parent))

from color_transfer_framework.interface_layer.orchestrator import TransferOrchestrator
from color_transfer_framework.transfer_engine import TransferConfig, TransferAlgorithm


def test_configuration(source, target, num_workers, variation_range=(0.85, 1.15)):
    """Test a specific Tom Sawyer configuration."""
    orchestrator = TransferOrchestrator()
    config = TransferConfig(algorithm=TransferAlgorithm.REINHARD_LAB)

    # Standard processing
    std_start = time.perf_counter()
    std_result = orchestrator.transfer(source, target, config=config)
    std_time = (time.perf_counter() - std_start) * 1000

    # Tom Sawyer processing (max_parallel_workers=4 is hard-coded in orchestrator)
    ts_start = time.perf_counter()
    ts_result = orchestrator.transfer_tom_sawyer(
        source, target,
        config=config,
        num_workers=num_workers,
        variation_range=variation_range,
        enable_parallel=True
    )
    ts_time = (time.perf_counter() - ts_start) * 1000

    overhead = (ts_time / std_time - 1) * 100
    confidence = ts_result.tom_sawyer_metrics.consensus_confidence

    return {
        'num_workers': num_workers,
        'variation_range': variation_range,
        'std_time': std_time,
        'ts_time': ts_time,
        'overhead': overhead,
        'confidence': confidence,
        'speedup_vs_sequential': num_workers / (ts_time / std_time)
    }


def main():
    """Run optimization tests."""
    print("=" * 70)
    print("TOM SAWYER OPTIMIZATION")
    print("=" * 70)

    # Create test images
    print("\nCreating test images (512x512)...")
    source = np.random.randint(0, 256, (512, 512, 3), dtype=np.uint8)
    target = np.random.randint(0, 256, (512, 512, 3), dtype=np.uint8)

    # Warm-up
    print("Warm-up run...")
    orchestrator = TransferOrchestrator()
    config = TransferConfig(algorithm=TransferAlgorithm.REINHARD_LAB)
    _ = orchestrator.transfer(source, target, config=config)

    configurations = [
        # (num_workers, variation_range)
        (4, (0.85, 1.15)),   # Minimal workers for 4 parallel (1:1 ratio)
        (5, (0.85, 1.15)),   # Fewer workers, tight range
        (6, (0.85, 1.15)),   # Optimal for 4 parallel?
        (8, (0.85, 1.15)),   # Standard  (2:1 ratio)
        (10, (0.85, 1.15)),  # Current default (2.5:1 ratio)
        (12, (0.85, 1.15)),  # More workers (3:1 ratio)
        (6, (0.7, 1.3)),     # Wider range, fewer workers
        (8, (0.7, 1.3)),     # Wider range, standard workers
    ]

    print(f"\n{'=' * 70}")
    print("TESTING CONFIGURATIONS")
    print(f"(max_parallel_workers=4 fixed in orchestrator)")
    print(f"{'=' * 70}\n")

    results = []
    for num_workers, var_range in configurations:
        print(f"Testing: workers={num_workers}, range={var_range}")

        result = test_configuration(source, target, num_workers, var_range)
        results.append(result)

        print(f"  Standard: {result['std_time']:.2f} ms")
        print(f"  Tom Sawyer: {result['ts_time']:.2f} ms")
        print(f"  Overhead: {result['overhead']:+.1f}%")
        print(f"  Confidence: {result['confidence']:.2f}%")
        print()

    # Find best configuration
    print(f"{'=' * 70}")
    print("RESULTS SUMMARY")
    print(f"{'=' * 70}\n")

    # Sort by overhead
    results_sorted = sorted(results, key=lambda x: x['overhead'])

    print(f"{'Workers':<10} {'Var Range':<15} {'Overhead':<15} {'Confidence':<12}")
    print(f"{'-' * 70}")

    for r in results_sorted:
        var_str = f"{r['variation_range'][0]:.2f}-{r['variation_range'][1]:.2f}"
        overhead_str = f"{r['overhead']:+.1f}%"
        print(f"{r['num_workers']:<10} {var_str:<15} {overhead_str:<15} {r['confidence']:.2f}%")

    best = results_sorted[0]
    print(f"\n{'=' * 70}")
    print("BEST CONFIGURATION")
    print(f"{'=' * 70}\n")

    print(f"Workers: {best['num_workers']}")
    print(f"Variation Range: {best['variation_range']}")
    print(f"Overhead: {best['overhead']:+.1f}%")
    print(f"Confidence: {best['confidence']:.2f}%")

    if best['overhead'] < 100:
        print(f"\n✅ EXCELLENT: Overhead < 100%")
        print(f"   Recommendation: PROCEED WITH PHASE 18")
    elif best['overhead'] < 200:
        print(f"\n⚠️  ACCEPTABLE: Overhead < 200%")
        print(f"   Recommendation: Proceed with Phase 18, monitor performance")
    else:
        print(f"\n❌ HIGH: Overhead > 200%")
        print(f"   Current implementation provides quality but at cost")
        print(f"   Recommendation: Document as optional 'quality mode'")


if __name__ == "__main__":
    main()
