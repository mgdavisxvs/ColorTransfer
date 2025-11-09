#!/usr/bin/env python3
"""
Run All Benchmarks
==================

Executes comprehensive benchmarks on all test image pairs and
generates a consolidated report.
"""

import subprocess
import json
from pathlib import Path
from typing import List, Dict
import numpy as np


def load_benchmark_pairs(pairs_file: Path) -> List[tuple]:
    """Load benchmark pairs from configuration file."""
    pairs = []
    with open(pairs_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            source, target = line.split(',')
            pairs.append((source.strip(), target.strip()))
    return pairs


def run_single_benchmark(source: str, target: str, algorithm: str, runs: int = 3) -> Dict:
    """Run benchmark on a single image pair."""
    source_name = Path(source).stem
    target_name = Path(target).stem
    output_dir = f"benchmark_results/{source_name}_to_{target_name}"

    # Run benchmark
    cmd = [
        "python", "examples/tom_sawyer_benchmark.py",
        "--source", f"test_images/{source}",
        "--target", f"test_images/{target}",
        "--algorithm", algorithm,
        "--runs", str(runs),
        "--output-dir", output_dir
    ]

    print(f"\n{'=' * 70}")
    print(f"Running: {source_name} → {target_name}")
    print(f"{'=' * 70}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        # Load results
        json_file = Path(output_dir) / f"benchmark_{algorithm}.json"
        if json_file.exists():
            with open(json_file, 'r') as f:
                data = json.load(f)

            overhead = data.get('overhead', {}).get('time_pct', 'N/A')
            confidence = data.get('tom_sawyer', {}).get('confidence_avg', 'N/A')
            psnr = data.get('quality', {}).get('psnr', 'N/A')

            print(f"✓ Time overhead: {overhead:.1f}%" if overhead != 'N/A' else f"✓ Time overhead: {overhead}")
            print(f"✓ Consensus confidence: {confidence * 100:.2f}%" if confidence != 'N/A' else f"✓ Consensus confidence: {confidence}")
            print(f"✓ PSNR: {psnr:.2f} dB" if psnr != 'N/A' else f"✓ PSNR: {psnr}")

            return {
                'source': source,
                'target': target,
                'output_dir': output_dir,
                'success': True,
                'data': data
            }
        else:
            print(f"✗ Results file not found")
            return {
                'source': source,
                'target': target,
                'success': False,
                'error': 'Results file not found'
            }

    except subprocess.TimeoutExpired:
        print(f"✗ Timeout")
        return {
            'source': source,
            'target': target,
            'success': False,
            'error': 'Timeout'
        }
    except Exception as e:
        print(f"✗ Error: {e}")
        return {
            'source': source,
            'target': target,
            'success': False,
            'error': str(e)
        }


def generate_consolidated_report(results: List[Dict], output_file: Path):
    """Generate consolidated report from all benchmark results."""
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]

    # Calculate aggregate statistics
    time_overheads = []
    memory_overheads = []
    confidences = []
    psnrs = []
    ssims = []

    for result in successful:
        data = result.get('data', {})

        # Extract metrics
        overhead_data = data.get('overhead', {})
        time_overhead = overhead_data.get('time_pct')
        if time_overhead is not None:
            time_overheads.append(float(time_overhead))

        memory_overhead = overhead_data.get('memory_pct')
        if memory_overhead is not None:
            memory_overheads.append(float(memory_overhead))

        ts_data = data.get('tom_sawyer', {})
        conf = ts_data.get('confidence_avg')
        if conf is not None:
            confidences.append(float(conf) * 100)  # Convert to percentage

        quality = data.get('quality', {})
        psnr = quality.get('psnr')
        if psnr is not None:
            psnrs.append(float(psnr))

        ssim = quality.get('ssim')
        if ssim is not None:
            ssims.append(float(ssim))

    # Generate report
    report = {
        'summary': {
            'total_benchmarks': len(results),
            'successful': len(successful),
            'failed': len(failed),
        },
        'aggregate_statistics': {
            'time_overhead': {
                'mean': np.mean(time_overheads) if time_overheads else None,
                'std': np.std(time_overheads) if time_overheads else None,
                'min': np.min(time_overheads) if time_overheads else None,
                'max': np.max(time_overheads) if time_overheads else None,
            },
            'consensus_confidence': {
                'mean': np.mean(confidences) if confidences else None,
                'std': np.std(confidences) if confidences else None,
                'min': np.min(confidences) if confidences else None,
                'max': np.max(confidences) if confidences else None,
            },
            'psnr': {
                'mean': np.mean(psnrs) if psnrs else None,
                'std': np.std(psnrs) if psnrs else None,
                'min': np.min(psnrs) if psnrs else None,
                'max': np.max(psnrs) if psnrs else None,
            },
            'ssim': {
                'mean': np.mean(ssims) if ssims else None,
                'std': np.std(ssims) if ssims else None,
                'min': np.min(ssims) if ssims else None,
                'max': np.max(ssims) if ssims else None,
            },
        },
        'individual_results': results
    }

    # Save JSON report
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)

    # Print summary
    print("\n" + "=" * 70)
    print("CONSOLIDATED BENCHMARK REPORT")
    print("=" * 70)
    print(f"\nTotal benchmarks: {len(results)}")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")

    if time_overheads:
        print(f"\nTime Overhead:")
        print(f"  Mean: {np.mean(time_overheads):.1f}%")
        print(f"  Std Dev: {np.std(time_overheads):.1f}%")
        print(f"  Range: {np.min(time_overheads):.1f}% to {np.max(time_overheads):.1f}%")

    if confidences:
        print(f"\nConsensus Confidence:")
        print(f"  Mean: {np.mean(confidences):.2f}%")
        print(f"  Std Dev: {np.std(confidences):.2f}%")
        print(f"  Range: {np.min(confidences):.2f}% to {np.max(confidences):.2f}%")

    if psnrs:
        print(f"\nPSNR (Standard vs Tom Sawyer):")
        print(f"  Mean: {np.mean(psnrs):.2f} dB")
        print(f"  Std Dev: {np.std(psnrs):.2f} dB")
        print(f"  Range: {np.min(psnrs):.2f} dB to {np.max(psnrs):.2f} dB")

    if ssims:
        print(f"\nSSIM (Standard vs Tom Sawyer):")
        print(f"  Mean: {np.mean(ssims):.4f}")
        print(f"  Std Dev: {np.std(ssims):.4f}")
        print(f"  Range: {np.min(ssims):.4f} to {np.max(ssims):.4f}")

    print(f"\n✓ Report saved: {output_file}")


def main():
    """Main entry point."""
    # Load benchmark pairs
    pairs_file = Path("test_images/benchmark_pairs.txt")
    pairs = load_benchmark_pairs(pairs_file)

    print("=" * 70)
    print("TOM SAWYER METHOD - COMPREHENSIVE BENCHMARK SUITE")
    print("=" * 70)
    print(f"\nFound {len(pairs)} image pairs to benchmark")

    # Run all benchmarks
    results = []
    for source, target in pairs:
        result = run_single_benchmark(source, target, algorithm="reinhard_lab", runs=3)
        results.append(result)

    # Generate consolidated report
    output_file = Path("benchmark_results/consolidated_report.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    generate_consolidated_report(results, output_file)


if __name__ == "__main__":
    main()
