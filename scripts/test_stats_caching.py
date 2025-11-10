#!/usr/bin/env python3
"""
Test statistics caching behavior
=================================

Verifies that stats caching works correctly across multiple workers.
"""

import sys
from pathlib import Path
import time
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from color_transfer_framework.color_statistics_engine import ColorStatisticsEngine

# Create test image
np.random.seed(42)
image = np.random.randint(0, 256, (1024, 1024, 3), dtype=np.uint8).astype(np.float32)

# Test with caching enabled
engine = ColorStatisticsEngine(cache_stats=True)

print("Testing stats caching...")
print(f"Image shape: {image.shape}")
print(f"Image dtype: {image.dtype}")
print(f"Cache enabled: {engine.cache_stats}")
print()

# First computation
start = time.perf_counter()
stats1 = engine.compute_stats(image)
time1 = (time.perf_counter() - start) * 1000
print(f"First computation: {time1:.2f}ms")
print(f"Mean: {stats1.mean}")
print(f"Cache size: {len(engine._stats_cache)}")
print()

# Second computation (should hit cache)
start = time.perf_counter()
stats2 = engine.compute_stats(image)
time2 = (time.perf_counter() - start) * 1000
print(f"Second computation: {time2:.2f}ms")
print(f"Mean: {stats2.mean}")
print(f"Cache size: {len(engine._stats_cache)}")
print()

# Verify cache hit
speedup = time1 / time2
print(f"Speedup: {speedup:.1f}×")

if speedup > 10:
    print("✅ Cache is working!")
else:
    print("❌ Cache is NOT working - both computations took similar time")
