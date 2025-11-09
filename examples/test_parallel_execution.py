#!/usr/bin/env python3
"""
Test Parallel Execution
========================

Diagnose parallel vs sequential execution performance to verify
ThreadPoolExecutor is providing true parallelism.
"""

import time
import numpy as np
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from color_transfer_framework.transfer_engine import TransferEngine, TransferConfig, TransferAlgorithm


def single_transfer(source, target, config):
    """Execute single transfer (for timing)."""
    engine = TransferEngine()
    return engine.transfer(source, target, config)


def time_sequential(source, target, config, num_runs=10):
    """Time sequential execution."""
    start = time.perf_counter()
    results = []
    for i in range(num_runs):
        result = single_transfer(source, target, config)
        results.append(result)
    end = time.perf_counter()
    return (end - start) * 1000, results


def time_parallel_threads(source, target, config, num_runs=10, max_workers=4):
    """Time parallel execution with ThreadPoolExecutor."""
    start = time.perf_counter()
    results = [None] * num_runs

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for i in range(num_runs):
            future = executor.submit(single_transfer, source, target, config)
            futures.append((i, future))

        for i, future in futures:
            results[i] = future.result()

    end = time.perf_counter()
    return (end - start) * 1000, results


def main():
    """Run parallel execution diagnostic."""
    print("=" * 70)
    print("PARALLEL EXECUTION DIAGNOSTIC")
    print("=" * 70)

    # Create test images
    print("\nCreating test images (256x256)...")
    source = np.random.randint(0, 256, (256, 256, 3), dtype=np.uint8)
    target = np.random.randint(0, 256, (256, 256, 3), dtype=np.uint8)

    config = TransferConfig(algorithm=TransferAlgorithm.REINHARD_LAB)

    num_runs = 10

    # Warm-up
    print("Warm-up run...")
    _ = single_transfer(source, target, config)

    print(f"\n{'=' * 70}")
    print(f"RUNNING {num_runs} TRANSFERS")
    print(f"{'=' * 70}\n")

    # Test 1: Sequential
    print("Test 1: Sequential Execution")
    seq_time, seq_results = time_sequential(source, target, config, num_runs)
    per_transfer_seq = seq_time / num_runs
    print(f"  Total time: {seq_time:.2f} ms")
    print(f"  Per transfer: {per_transfer_seq:.2f} ms")

    # Test 2: Parallel with 2 workers
    print("\nTest 2: Parallel (ThreadPoolExecutor, 2 workers)")
    par2_time, par2_results = time_parallel_threads(source, target, config, num_runs, max_workers=2)
    speedup2 = seq_time / par2_time
    efficiency2 = speedup2 / 2 * 100
    print(f"  Total time: {par2_time:.2f} ms")
    print(f"  Speedup: {speedup2:.2f}x")
    print(f"  Efficiency: {efficiency2:.1f}% (ideal: 100%)")

    # Test 3: Parallel with 4 workers
    print("\nTest 3: Parallel (ThreadPoolExecutor, 4 workers)")
    par4_time, par4_results = time_parallel_threads(source, target, config, num_runs, max_workers=4)
    speedup4 = seq_time / par4_time
    efficiency4 = speedup4 / 4 * 100
    print(f"  Total time: {par4_time:.2f} ms")
    print(f"  Speedup: {speedup4:.2f}x")
    print(f"  Efficiency: {efficiency4:.1f}% (ideal: 100%)")

    # Test 4: Parallel with 8 workers
    print("\nTest 4: Parallel (ThreadPoolExecutor, 8 workers)")
    par8_time, par8_results = time_parallel_threads(source, target, config, num_runs, max_workers=8)
    speedup8 = seq_time / par8_time
    efficiency8 = speedup8 / 8 * 100
    print(f"  Total time: {par8_time:.2f} ms")
    print(f"  Speedup: {speedup8:.2f}x")
    print(f"  Efficiency: {efficiency8:.1f}% (ideal: 100%)")

    print(f"\n{'=' * 70}")
    print("SUMMARY")
    print(f"{'=' * 70}\n")

    print(f"Sequential: {seq_time:.2f} ms ({per_transfer_seq:.2f} ms/transfer)")
    print(f"Parallel (2 workers): {par2_time:.2f} ms ({speedup2:.2f}x speedup, {efficiency2:.1f}% efficiency)")
    print(f"Parallel (4 workers): {par4_time:.2f} ms ({speedup4:.2f}x speedup, {efficiency4:.1f}% efficiency)")
    print(f"Parallel (8 workers): {par8_time:.2f} ms ({speedup8:.2f}x speedup, {efficiency8:.1f}% efficiency)")

    print(f"\n{'=' * 70}")
    print("ANALYSIS")
    print(f"{'=' * 70}\n")

    if speedup4 > 2.0:
        print("✅ GOOD: ThreadPoolExecutor achieving >2x speedup with 4 workers")
        print("   OpenCV/NumPy are releasing GIL effectively")
    elif speedup4 > 1.5:
        print("⚠️  MODERATE: ThreadPoolExecutor achieving >1.5x speedup with 4 workers")
        print("   Some parallelism but not ideal - GIL may be limiting")
    else:
        print("❌ POOR: ThreadPoolExecutor achieving <1.5x speedup with 4 workers")
        print("   GIL is severely limiting parallelism")
        print("   Recommendation: Consider ProcessPoolExecutor")

    # Theoretical analysis for Tom Sawyer
    print(f"\n{'=' * 70}")
    print("TOM SAWYER METHOD PROJECTION")
    print(f"{'=' * 70}\n")

    standard_time = per_transfer_seq
    tom_sawyer_seq = num_runs * per_transfer_seq
    tom_sawyer_par4 = par4_time  # 10 workers with 4 parallel

    overhead_seq = (tom_sawyer_seq / standard_time - 1) * 100
    overhead_par = (tom_sawyer_par4 / standard_time - 1) * 100

    print(f"Standard processing: {standard_time:.2f} ms")
    print(f"Tom Sawyer (sequential): {tom_sawyer_seq:.2f} ms (overhead: +{overhead_seq:.1f}%)")
    print(f"Tom Sawyer (parallel, 4 workers): {tom_sawyer_par4:.2f} ms (overhead: +{overhead_par:.1f}%)")
    print(f"\nReduction in overhead: {overhead_seq - overhead_par:.1f} percentage points")

    if overhead_par < 100:
        print(f"\n✅ EXCELLENT: Projected overhead < 100%")
        print(f"   Recommendation: PROCEED WITH PHASE 18")
    elif overhead_par < 200:
        print(f"\n⚠️  ACCEPTABLE: Projected overhead < 200%")
        print(f"   Recommendation: Proceed with caution")
    else:
        print(f"\n❌ HIGH: Projected overhead > 200%")
        print(f"   Recommendation: Re-evaluate cost/benefit")


if __name__ == "__main__":
    main()
