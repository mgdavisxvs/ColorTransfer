#!/usr/bin/env python3
"""
Comprehensive Performance Profiling Script
===========================================

Torvalds Principle: "Talk is cheap. Show me the data."

This script profiles the ColorTransfer framework to identify real bottlenecks:
1. Function-level timing (cProfile)
2. Memory usage (tracemalloc)
3. Per-operation breakdown
4. Comparative analysis (standard vs Tom Sawyer)

Usage:
    python scripts/profile_bottlenecks.py
    python scripts/profile_bottlenecks.py --flamegraph
    python scripts/profile_bottlenecks.py --detailed
"""

import os
import sys
import time
import cProfile
import pstats
import io
import argparse
import json
import tracemalloc
from pathlib import Path
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass, asdict

import numpy as np
import cv2

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from color_transfer_framework.interface_layer.orchestrator import TransferOrchestrator
from color_transfer_framework.transfer_engine import TransferConfig, TransferAlgorithm


@dataclass
class ProfileResult:
    """Single profile measurement."""
    operation: str
    total_time_ms: float
    calls: int
    time_per_call_ms: float
    memory_mb: float
    peak_memory_mb: float


@dataclass
class BottleneckReport:
    """Complete bottleneck analysis."""
    timestamp: str
    image_size: Tuple[int, int]
    profiles: List[ProfileResult]
    hotspots: List[Dict[str, Any]]
    total_time_ms: float
    total_memory_mb: float
    recommendations: List[str]


class PerformanceProfiler:
    """
    Comprehensive performance profiler.

    Torvalds Requirements:
        - Fast execution (< 30 seconds for full profile)
        - Actionable results (specific bottlenecks)
        - Reproducible measurements
        - No external dependencies beyond stdlib
    """

    def __init__(self, output_dir: str = "profiling_results"):
        """Initialize profiler."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        self.orchestrator = TransferOrchestrator()
        self.config = TransferConfig(
            algorithm=TransferAlgorithm.REINHARD_LAB,
            blend_factor=1.0
        )

    def create_test_images(self, size: Tuple[int, int] = (512, 512)) -> Tuple[np.ndarray, np.ndarray]:
        """
        Create test images for profiling.

        Args:
            size: Image dimensions (height, width)

        Returns:
            Tuple of (source, target) images
        """
        height, width = size

        # Source: Gradient
        source = np.zeros((height, width, 3), dtype=np.uint8)
        for i in range(height):
            source[i, :] = [int(255 * i / height), 128, 255 - int(255 * i / height)]

        # Target: Random
        np.random.seed(42)
        target = np.random.randint(0, 256, (height, width, 3), dtype=np.uint8)

        return source, target

    def profile_function(
        self,
        func: callable,
        *args,
        operation_name: str = "operation",
        **kwargs
    ) -> ProfileResult:
        """
        Profile a single function with timing and memory.

        Args:
            func: Function to profile
            operation_name: Name for reporting
            *args, **kwargs: Arguments to func

        Returns:
            ProfileResult with timing and memory data
        """
        # Start memory tracking
        tracemalloc.start()

        # Time the function
        profiler = cProfile.Profile()
        profiler.enable()

        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()

        profiler.disable()

        # Get memory stats
        current_mem, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Extract stats
        stats = pstats.Stats(profiler)
        total_calls = stats.total_calls

        elapsed_ms = (end_time - start_time) * 1000

        return ProfileResult(
            operation=operation_name,
            total_time_ms=elapsed_ms,
            calls=total_calls,
            time_per_call_ms=elapsed_ms / max(1, total_calls),
            memory_mb=current_mem / 1024 / 1024,
            peak_memory_mb=peak_mem / 1024 / 1024
        )

    def extract_hotspots(self, profiler: cProfile.Profile, n: int = 10) -> List[Dict[str, Any]]:
        """
        Extract top N hotspots from profiler.

        Args:
            profiler: cProfile.Profile object
            n: Number of hotspots to extract

        Returns:
            List of hotspot dictionaries (filtered to our codebase only)
        """
        s = io.StringIO()
        stats = pstats.Stats(profiler, stream=s)
        stats.sort_stats('cumulative')

        hotspots = []

        # Get all functions, filter to our codebase
        for func_info, (cc, nc, tt, ct, callers) in stats.stats.items():
            filename, line, func_name = func_info

            # Filter: only include ColorTransfer framework functions, cv2, and numpy
            # Skip built-in methods and stdlib
            if filename and ('color_transfer' in filename or 'cv2' in filename or 'numpy' in filename):
                hotspots.append({
                    "function": func_name,
                    "file": Path(filename).name if filename else "unknown",
                    "line": line,
                    "calls": nc,
                    "total_time_ms": tt * 1000,
                    "cumulative_time_ms": ct * 1000,
                    "time_per_call_ms": (tt / nc * 1000) if nc > 0 else 0
                })

        # Sort by cumulative time and return top N
        hotspots.sort(key=lambda x: x['cumulative_time_ms'], reverse=True)

        return hotspots[:n * 3]  # Return more since we filtered

    def profile_standard_transfer(
        self,
        source: np.ndarray,
        target: np.ndarray
    ) -> Tuple[ProfileResult, List[Dict[str, Any]]]:
        """
        Profile standard color transfer.

        Returns:
            (ProfileResult, hotspots)
        """
        print("Profiling standard transfer...")

        profiler = cProfile.Profile()
        tracemalloc.start()

        profiler.enable()
        start_time = time.perf_counter()

        result = self.orchestrator.transfer(
            source, target,
            config=self.config
        )

        end_time = time.perf_counter()
        profiler.disable()

        current_mem, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        stats = pstats.Stats(profiler)
        elapsed_ms = (end_time - start_time) * 1000

        profile = ProfileResult(
            operation="standard_transfer",
            total_time_ms=elapsed_ms,
            calls=stats.total_calls,
            time_per_call_ms=elapsed_ms / max(1, stats.total_calls),
            memory_mb=current_mem / 1024 / 1024,
            peak_memory_mb=peak_mem / 1024 / 1024
        )

        hotspots = self.extract_hotspots(profiler, n=15)

        return profile, hotspots

    def profile_tom_sawyer(
        self,
        source: np.ndarray,
        target: np.ndarray,
        num_workers: int = 6
    ) -> Tuple[ProfileResult, List[Dict[str, Any]]]:
        """
        Profile Tom Sawyer method.

        Returns:
            (ProfileResult, hotspots)
        """
        print(f"Profiling Tom Sawyer ({num_workers} workers)...")

        profiler = cProfile.Profile()
        tracemalloc.start()

        profiler.enable()
        start_time = time.perf_counter()

        result = self.orchestrator.transfer_tom_sawyer(
            source, target,
            config=self.config,
            num_workers=num_workers,
            enable_multi_param=True
        )

        end_time = time.perf_counter()
        profiler.disable()

        current_mem, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        stats = pstats.Stats(profiler)
        elapsed_ms = (end_time - start_time) * 1000

        profile = ProfileResult(
            operation=f"tom_sawyer_{num_workers}w",
            total_time_ms=elapsed_ms,
            calls=stats.total_calls,
            time_per_call_ms=elapsed_ms / max(1, stats.total_calls),
            memory_mb=current_mem / 1024 / 1024,
            peak_memory_mb=peak_mem / 1024 / 1024
        )

        hotspots = self.extract_hotspots(profiler, n=15)

        return profile, hotspots

    def analyze_bottlenecks(
        self,
        profiles: List[ProfileResult],
        hotspots: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Generate actionable recommendations from profiling data.

        Torvalds Criteria:
            - Specific (name the function)
            - Measurable (quantify the impact)
            - Actionable (how to fix it)
        """
        recommendations = []

        # Find slowest operations
        sorted_profiles = sorted(profiles, key=lambda p: p.total_time_ms, reverse=True)

        # Rec 1: Slowest overall operation
        slowest = sorted_profiles[0]
        recommendations.append(
            f"CRITICAL: {slowest.operation} takes {slowest.total_time_ms:.1f}ms - "
            f"optimize this first for maximum impact"
        )

        # Rec 2: Memory usage
        high_memory = [p for p in profiles if p.peak_memory_mb > 50]
        if high_memory:
            recommendations.append(
                f"HIGH: {len(high_memory)} operations use >50MB memory - "
                f"consider dtype optimization (float64→float32)"
            )

        # Rec 3: Hotspot analysis
        if hotspots:
            top_hotspot = hotspots[0]
            recommendations.append(
                f"MEDIUM: Hotspot in {top_hotspot['function']} "
                f"({top_hotspot['cumulative_time_ms']:.1f}ms cumulative) - "
                f"profile this function specifically"
            )

        # Rec 4: Parallel overhead
        tom_sawyer_profiles = [p for p in profiles if 'tom_sawyer' in p.operation]
        standard_profiles = [p for p in profiles if p.operation == 'standard_transfer']

        if tom_sawyer_profiles and standard_profiles:
            ts_time = tom_sawyer_profiles[0].total_time_ms
            std_time = standard_profiles[0].total_time_ms
            overhead = (ts_time - std_time) / std_time * 100

            if overhead > 50:
                recommendations.append(
                    f"HIGH: Tom Sawyer overhead is {overhead:.1f}% - "
                    f"reduce worker synchronization cost"
                )

        # Rec 5: GPU acceleration opportunity
        if any('histogram' in h['function'].lower() for h in hotspots):
            recommendations.append(
                "MEDIUM: Histogram operations detected in hotspots - "
                "GPU acceleration (cv2.cuda) could provide 3-10× speedup"
            )

        return recommendations

    def run_comprehensive_profile(
        self,
        image_sizes: List[Tuple[int, int]] = [(512, 512), (1024, 1024)]
    ) -> List[BottleneckReport]:
        """
        Run comprehensive profiling suite.

        Args:
            image_sizes: List of image sizes to test

        Returns:
            List of BottleneckReport objects
        """
        reports = []

        for size in image_sizes:
            print(f"\n{'='*60}")
            print(f"Profiling {size[0]}×{size[1]} images")
            print(f"{'='*60}\n")

            source, target = self.create_test_images(size)

            profiles = []
            all_hotspots = []

            # Profile standard transfer
            std_profile, std_hotspots = self.profile_standard_transfer(source, target)
            profiles.append(std_profile)
            all_hotspots.extend(std_hotspots)

            print(f"  Standard: {std_profile.total_time_ms:.1f}ms, "
                  f"{std_profile.peak_memory_mb:.1f}MB peak")

            # Profile Tom Sawyer with different worker counts
            for num_workers in [4, 6, 8]:
                ts_profile, ts_hotspots = self.profile_tom_sawyer(
                    source, target, num_workers
                )
                profiles.append(ts_profile)
                all_hotspots.extend(ts_hotspots)

                overhead = (ts_profile.total_time_ms - std_profile.total_time_ms) / std_profile.total_time_ms * 100

                print(f"  Tom Sawyer ({num_workers}w): {ts_profile.total_time_ms:.1f}ms "
                      f"({overhead:+.1f}% vs std), {ts_profile.peak_memory_mb:.1f}MB peak")

            # Analyze and generate recommendations
            recommendations = self.analyze_bottlenecks(profiles, all_hotspots)

            total_time = sum(p.total_time_ms for p in profiles)
            total_memory = max(p.peak_memory_mb for p in profiles)

            report = BottleneckReport(
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
                image_size=size,
                profiles=profiles,
                hotspots=all_hotspots[:10],  # Top 10
                total_time_ms=total_time,
                total_memory_mb=total_memory,
                recommendations=recommendations
            )

            reports.append(report)

        return reports

    def save_report(self, reports: List[BottleneckReport], filename: str = "bottleneck_report.json"):
        """Save profiling reports to JSON."""
        output_path = self.output_dir / filename

        # Convert to JSON-serializable format
        data = {
            "reports": [
                {
                    "timestamp": r.timestamp,
                    "image_size": r.image_size,
                    "profiles": [asdict(p) for p in r.profiles],
                    "hotspots": r.hotspots,
                    "total_time_ms": r.total_time_ms,
                    "total_memory_mb": r.total_memory_mb,
                    "recommendations": r.recommendations
                }
                for r in reports
            ]
        }

        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"\n✓ Report saved to {output_path}")

    def print_summary(self, reports: List[BottleneckReport]):
        """Print human-readable summary."""
        print(f"\n{'='*60}")
        print("PROFILING SUMMARY")
        print(f"{'='*60}\n")

        for report in reports:
            print(f"Image Size: {report.image_size[0]}×{report.image_size[1]}")
            print(f"Timestamp: {report.timestamp}")
            print(f"Total Time: {report.total_time_ms:.1f}ms")
            print(f"Peak Memory: {report.total_memory_mb:.1f}MB")
            print("\nTop Hotspots:")

            for i, hotspot in enumerate(report.hotspots[:5], 1):
                print(f"  {i}. {hotspot['function']} "
                      f"({hotspot['cumulative_time_ms']:.2f}ms, "
                      f"{hotspot['calls']} calls)")

            print("\nRecommendations:")
            for i, rec in enumerate(report.recommendations, 1):
                print(f"  {i}. {rec}")

            print()


def main():
    """Main profiling entry point."""
    parser = argparse.ArgumentParser(description="Profile ColorTransfer bottlenecks")
    parser.add_argument(
        '--sizes',
        nargs='+',
        type=int,
        default=[512, 1024],
        help='Image sizes to test (e.g., --sizes 512 1024 2048)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='profiling_results',
        help='Output directory for reports'
    )
    parser.add_argument(
        '--detailed',
        action='store_true',
        help='Include detailed hotspot analysis'
    )

    args = parser.parse_args()

    # Convert sizes to tuples
    image_sizes = [(size, size) for size in args.sizes]

    print("ColorTransfer Performance Profiler")
    print("=" * 60)
    print(f"Testing image sizes: {[f'{s}×{s}' for s in args.sizes]}")
    print(f"Output directory: {args.output}")
    print()

    profiler = PerformanceProfiler(output_dir=args.output)

    # Run profiling
    reports = profiler.run_comprehensive_profile(image_sizes=image_sizes)

    # Save and print results
    profiler.save_report(reports)
    profiler.print_summary(reports)

    print("\n✓ Profiling complete!")
    print(f"  Results saved to: {profiler.output_dir}/bottleneck_report.json")
    print("  Next step: Review recommendations and implement optimizations")


if __name__ == "__main__":
    main()
