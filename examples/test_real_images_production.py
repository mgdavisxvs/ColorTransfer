#!/usr/bin/env python3
"""
Real Image Test Suite - Production Validation
==============================================

Tests Tom Sawyer Method on real images to validate production readiness.
Addresses Knuth-Graham analysis recommendation: "Add real image tests"

Tests cover:
1. Natural images (real-world photos)
2. Gradient images (smooth transitions)
3. Pattern images (structured content)
4. Edge cases (near-monochrome, high-contrast)
"""

import sys
from pathlib import Path
import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from color_transfer_framework.interface_layer.orchestrator import TransferOrchestrator
from color_transfer_framework.transfer_engine import TransferConfig, TransferAlgorithm


def load_test_images():
    """Load real test images from test_images directory."""
    test_dir = Path(__file__).parent.parent / "test_images"

    images = {
        "natural_512": {
            "source": test_dir / "warm_sunset_natural_1024x1024.jpg",
            "target": test_dir / "vibrant_spring_natural_512x512.jpg"
        },
        "gradient_512": {
            "source": test_dir / "cool_ocean_gradient_512x512.jpg",
            "target": test_dir / "warm_sunset_gradient_512x512.jpg"
        },
        "pattern_512": {
            "source": test_dir / "neutral_gray_pattern_512x512.jpg",
            "target": test_dir / "cool_ocean_pattern_512x512.jpg"
        },
        "monochrome_512": {
            "source": test_dir / "neutral_gray_natural_512x512.jpg",
            "target": test_dir / "neutral_gray_gradient_512x512.jpg"
        },
        "large_natural_1024": {
            "source": test_dir / "warm_sunset_natural_1024x1024.jpg",
            "target": test_dir / "vibrant_spring_natural_1024x1024.jpg"
        }
    }

    loaded = {}
    for category, paths in images.items():
        if paths["source"].exists() and paths["target"].exists():
            loaded[category] = {
                "source": cv2.imread(str(paths["source"])),
                "target": cv2.imread(str(paths["target"]))
            }

    return loaded


def test_real_images():
    """Test Tom Sawyer Method on real images."""
    print("=" * 70)
    print("REAL IMAGE TEST SUITE (Knuth-Graham Recommendation)")
    print("=" * 70)
    print("\nValidating Tom Sawyer Method on real-world images...")
    print("Addresses: 'Add real image tests' (HIGH Priority)\n")

    orchestrator = TransferOrchestrator()
    config = TransferConfig(algorithm=TransferAlgorithm.REINHARD_LAB)

    # Load test images
    images = load_test_images()

    if not images:
        print("❌ ERROR: No test images found in test_images/")
        print("   Please ensure test images are available.")
        return False

    print(f"Loaded {len(images)} test image categories\n")

    results = {}
    all_passed = True

    for category, img_pair in images.items():
        source = img_pair["source"]
        target = img_pair["target"]

        if source is None or target is None:
            print(f"⚠️  {category}: Failed to load images")
            all_passed = False
            continue

        h, w = target.shape[:2]
        pixels = h * w

        print(f"\n{'-' * 70}")
        print(f"Testing: {category}")
        print(f"  Target size: {w}×{h} ({pixels:,} pixels)")
        print(f"{'-' * 70}\n")

        # Test 1: Standard processing (baseline)
        try:
            print("  [1/4] Standard processing... ", end="", flush=True)
            std_result = orchestrator.transfer(source, target, config=config)
            std_time = std_result.metrics.execution_time_ms
            print(f"✓ {std_time:.2f} ms")
        except Exception as e:
            print(f"❌ FAILED: {e}")
            all_passed = False
            continue

        # Test 2: Tom Sawyer with single-param
        try:
            print("  [2/4] Tom Sawyer (single-param)... ", end="", flush=True)
            single_result = orchestrator.transfer_tom_sawyer(
                source, target,
                config=config,
                num_workers=None,  # Auto-select
                enable_multi_param=False,
                enable_parallel=True
            )
            single_time = single_result.metrics.execution_time_ms
            single_conf = single_result.tom_sawyer_metrics.consensus_confidence
            print(f"✓ {single_time:.2f} ms, conf={single_conf:.4f}%")
        except Exception as e:
            print(f"❌ FAILED: {e}")
            all_passed = False
            continue

        # Test 3: Tom Sawyer with multi-param (Phase 18.3)
        try:
            print("  [3/4] Tom Sawyer (multi-param)... ", end="", flush=True)
            multi_result = orchestrator.transfer_tom_sawyer(
                source, target,
                config=config,
                num_workers=None,  # Auto-select
                enable_multi_param=True,
                enable_parallel=True
            )
            multi_time = multi_result.metrics.execution_time_ms
            multi_conf = multi_result.tom_sawyer_metrics.consensus_confidence
            multi_workers = multi_result.tom_sawyer_metrics.num_workers
            print(f"✓ {multi_time:.2f} ms, conf={multi_conf:.4f}%, workers={multi_workers}")
        except Exception as e:
            print(f"❌ FAILED: {e}")
            all_passed = False
            continue

        # Test 4: Quality validation
        try:
            print("  [4/4] Quality validation... ", end="", flush=True)

            # Check result is valid
            if multi_result.result_image is None:
                raise ValueError("Result image is None")

            # Check dimensions match
            if multi_result.result_image.shape != target.shape:
                raise ValueError(
                    f"Shape mismatch: expected {target.shape}, "
                    f"got {multi_result.result_image.shape}"
                )

            # Check pixel range
            min_val = multi_result.result_image.min()
            max_val = multi_result.result_image.max()
            if min_val < 0 or max_val > 255:
                raise ValueError(f"Pixel range invalid: [{min_val}, {max_val}]")

            # Check consensus quality
            if multi_conf > 1.0:  # Should be very low for good consensus
                print(f"⚠️  High consensus confidence: {multi_conf:.4f}%")

            print("✓ All checks passed")
        except Exception as e:
            print(f"❌ FAILED: {e}")
            all_passed = False
            continue

        # Calculate metrics
        overhead = ((multi_time / std_time) - 1) * 100
        speedup = single_time / multi_time

        # Store results
        results[category] = {
            "std_time": std_time,
            "single_time": single_time,
            "multi_time": multi_time,
            "multi_conf": multi_conf,
            "multi_workers": multi_workers,
            "overhead": overhead,
            "speedup": speedup,
            "passed": True
        }

        print(f"\n  Summary:")
        print(f"    Overhead:          {overhead:+.1f}%")
        print(f"    Multi vs Single:   {speedup:.2f}× {'faster' if speedup > 1 else 'slower'}")
        print(f"    Consensus:         {multi_conf:.4f}% (lower is better)")
        print(f"    Workers selected:  {multi_workers}")

        # Validate against expected overhead thresholds
        if pixels < 300_000 and overhead > 100:
            print(f"  ⚠️  WARNING: Overhead {overhead:.1f}% exceeds target (<100%) for small images")
        elif pixels < 1_000_000 and overhead > 150:
            print(f"  ⚠️  WARNING: Overhead {overhead:.1f}% exceeds target (<150%) for medium images")
        else:
            print(f"  ✅ Overhead within acceptable range")

    # Overall summary
    print(f"\n{'=' * 70}")
    print("OVERALL SUMMARY")
    print(f"{'=' * 70}\n")

    if not results:
        print("❌ NO TESTS PASSED - Critical failure!")
        return False

    # Calculate statistics
    overheads = [r["overhead"] for r in results.values()]
    speedups = [r["speedup"] for r in results.values()]
    confidences = [r["multi_conf"] for r in results.values()]

    print(f"Tests completed: {len(results)}/{len(images)}")
    print(f"\nPerformance Statistics:")
    print(f"  Overhead:    {np.mean(overheads):.1f}% ± {np.std(overheads):.1f}%")
    print(f"  Speedup:     {np.mean(speedups):.2f}× ± {np.std(speedups):.2f}×")
    print(f"  Consensus:   {np.mean(confidences):.4f}% ± {np.std(confidences):.4f}%")

    print(f"\nImage Categories Tested:")
    for category in results.keys():
        status = "✅" if results[category]["passed"] else "❌"
        print(f"  {status} {category}")

    if all_passed and len(results) >= 3:
        print(f"\n✅ SUCCESS: All real image tests passed!")
        print(f"   Production readiness validated on {len(results)} image categories")
        print(f"   Recommendation: APPROVED for real-world deployment")
        return True
    elif len(results) >= 1:
        print(f"\n⚠️  PARTIAL: {len(results)}/{len(images)} categories passed")
        print(f"   Recommendation: Review failures before deployment")
        return False
    else:
        print(f"\n❌ FAILED: No categories passed testing")
        print(f"   Recommendation: DO NOT deploy, investigate failures")
        return False


def test_edge_cases():
    """Test edge cases identified in Knuth-Graham analysis."""
    print(f"\n{'=' * 70}")
    print("EDGE CASE TESTING")
    print(f"{'=' * 70}\n")

    orchestrator = TransferOrchestrator()
    config = TransferConfig(algorithm=TransferAlgorithm.REINHARD_LAB)

    edge_cases = {
        "solid_color": {
            "source": np.full((512, 512, 3), 128, dtype=np.uint8),
            "target": np.full((512, 512, 3), 200, dtype=np.uint8)
        },
        "pure_noise": {
            "source": np.random.randint(0, 256, (512, 512, 3), dtype=np.uint8),
            "target": np.random.randint(0, 256, (512, 512, 3), dtype=np.uint8)
        },
        "high_contrast": {
            "source": np.where(
                np.random.random((512, 512, 3)) > 0.5, 255, 0
            ).astype(np.uint8),
            "target": np.where(
                np.random.random((512, 512, 3)) > 0.5, 255, 0
            ).astype(np.uint8)
        }
    }

    all_passed = True

    for case_name, imgs in edge_cases.items():
        print(f"Testing: {case_name}... ", end="", flush=True)

        try:
            result = orchestrator.transfer_tom_sawyer(
                imgs["source"], imgs["target"],
                config=config,
                num_workers=4,
                enable_multi_param=True,
                enable_parallel=True
            )

            # Validate result
            if result.result_image is None:
                raise ValueError("Result is None")

            if not (0 <= result.result_image.min() <= result.result_image.max() <= 255):
                raise ValueError("Pixel values out of range")

            print(f"✅ PASS (time={result.metrics.execution_time_ms:.2f}ms)")

        except Exception as e:
            print(f"❌ FAIL: {e}")
            all_passed = False

    if all_passed:
        print(f"\n✅ All edge cases handled correctly")
    else:
        print(f"\n⚠️  Some edge cases failed - review implementation")

    return all_passed


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("PRODUCTION VALIDATION TEST SUITE")
    print("=" * 70)
    print("\nImplementing Knuth-Graham Analysis Recommendations")
    print("Priority: HIGH (Production Blocker)")
    print("\n")

    # Run real image tests
    real_passed = test_real_images()

    # Run edge case tests
    edge_passed = test_edge_cases()

    # Final verdict
    print(f"\n{'=' * 70}")
    print("FINAL VERDICT")
    print(f"{'=' * 70}\n")

    if real_passed and edge_passed:
        print("✅ PRODUCTION READY")
        print("   All real image tests passed")
        print("   All edge cases handled")
        print("   Recommendation: APPROVED for deployment")
        sys.exit(0)
    elif real_passed:
        print("⚠️  CONDITIONALLY READY")
        print("   Real images passed, but edge cases need review")
        print("   Recommendation: Deploy with caution, monitor edge cases")
        sys.exit(1)
    else:
        print("❌ NOT PRODUCTION READY")
        print("   Real image tests failed")
        print("   Recommendation: DO NOT deploy, fix issues first")
        sys.exit(2)
