#!/usr/bin/env python3
"""
Tom Sawyer Method - Verification Script
========================================

Quick verification that Tom Sawyer implementation is working correctly.

This script:
1. Creates synthetic test images
2. Runs standard transfer
3. Runs Tom Sawyer transfer
4. Validates all components
5. Reports results
"""

import sys
from pathlib import Path
import numpy as np
import cv2

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from color_transfer_framework.tom_sawyer import (
    WorkerManager,
    VariationController,
    ConsensusAggregator,
    TomSawyerProcessor,
)
from color_transfer_framework.interface_layer.orchestrator import TransferOrchestrator
from color_transfer_framework.transfer_engine import TransferConfig, TransferAlgorithm


def create_test_images():
    """Create synthetic test images."""
    print("Creating synthetic test images...")

    # Source: Blue-tinted gradient
    source = np.zeros((256, 256, 3), dtype=np.uint8)
    for i in range(256):
        source[i, :, 0] = i  # B channel gradient
        source[i, :, 1] = i // 2  # G channel
        source[i, :, 2] = 50  # R channel constant

    # Target: Red-tinted gradient
    target = np.zeros((256, 256, 3), dtype=np.uint8)
    for i in range(256):
        target[i, :, 0] = 50  # B channel constant
        target[i, :, 1] = i // 2  # G channel
        target[i, :, 2] = i  # R channel gradient

    print(f"  ✓ Source: {source.shape} (blue-tinted)")
    print(f"  ✓ Target: {target.shape} (red-tinted)")

    return source, target


def test_worker_manager():
    """Test WorkerManager component."""
    print("\n[1/5] Testing WorkerManager...")

    try:
        manager = WorkerManager(num_workers=10)
        weights = manager.get_weights()

        assert len(weights) == 10, "Wrong number of weights"
        assert np.isclose(weights.sum(), 10.0), "Weights don't sum to num_workers"
        assert weights[4] > weights[0], "Center weights not heavier than edge"

        print("  ✓ Initialization: PASS")
        print("  ✓ Weight distribution: PASS")
        print(f"  ✓ Weights: {weights.round(2)}")
        return True
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        return False


def test_variation_controller():
    """Test VariationController component."""
    print("\n[2/5] Testing VariationController...")

    try:
        controller = VariationController(variation_range=(0.85, 1.15))
        base_config = TransferConfig(
            algorithm=TransferAlgorithm.REINHARD_LAB,
            blend_factor=1.0
        )

        variations = controller.generate_variations(base_config, num_workers=10)

        assert len(variations) == 10, "Wrong number of variations"
        assert np.isclose(variations[0].blend_factor, 0.85, atol=0.01), "First variation wrong"
        # Last variation is clamped to 1.0 (max valid blend_factor)
        assert np.isclose(variations[9].blend_factor, 1.0, atol=0.01), "Last variation wrong"

        print("  ✓ Variation generation: PASS")
        print(f"  ✓ First blend factor: {variations[0].blend_factor:.3f}")
        print(f"  ✓ Last blend factor: {variations[9].blend_factor:.3f}")
        return True
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        return False


def test_consensus_aggregator():
    """Test ConsensusAggregator component."""
    print("\n[3/5] Testing ConsensusAggregator...")

    try:
        aggregator = ConsensusAggregator(enable_outlier_rejection=True)

        # Create test results
        results = [np.ones((50, 50, 3)) * (100 + i * 5) for i in range(5)]
        weights = np.ones(5)

        consensus, metadata = aggregator.aggregate(results, weights)

        assert consensus.shape == (50, 50, 3), "Wrong consensus shape"
        assert metadata["num_workers"] == 5, "Wrong worker count"
        assert np.all(consensus > 0), "Invalid consensus values"

        quality = aggregator.compute_consensus_quality(results, consensus)

        print("  ✓ Aggregation: PASS")
        print(f"  ✓ Workers used: {metadata['num_used']}/{metadata['num_workers']}")
        print(f"  ✓ Consensus confidence: {quality['confidence']:.2%}")
        return True
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        return False


def test_tom_sawyer_processor(source, target):
    """Test TomSawyerProcessor component."""
    print("\n[4/5] Testing TomSawyerProcessor...")

    try:
        processor = TomSawyerProcessor(num_workers=5)  # Use 5 for faster testing
        config = TransferConfig(algorithm=TransferAlgorithm.REINHARD_LAB)

        # Mock transfer function
        def mock_transfer(src, tgt, cfg):
            return tgt.astype(float) * cfg.blend_factor

        # Process
        result, metrics = processor.process(
            source, target, config, mock_transfer,
            enable_parallel=False  # Sequential for testing
        )

        assert result.shape == target.shape, "Wrong result shape"
        assert metrics.num_workers == 5, "Wrong worker count"
        assert metrics.processing_time_ms > 0, "Invalid processing time"
        assert 0.0 <= metrics.consensus_confidence <= 1.0, "Invalid confidence"

        print("  ✓ Processing: PASS")
        print(f"  ✓ Processing time: {metrics.processing_time_ms:.2f}ms")
        print(f"  ✓ Consensus confidence: {metrics.consensus_confidence:.2%}")
        print(f"  ✓ Outliers rejected: {metrics.num_outliers}")
        return True
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_orchestrator_integration(source, target):
    """Test Orchestrator integration."""
    print("\n[5/5] Testing Orchestrator Integration...")

    try:
        orchestrator = TransferOrchestrator()
        config = TransferConfig(algorithm=TransferAlgorithm.REINHARD_LAB)

        # Standard transfer
        print("  Testing standard transfer...")
        std_result = orchestrator.transfer(source, target, config=config, profile_performance=True)
        assert std_result.result_image.shape == target.shape
        std_time = std_result.metrics.execution_time_ms
        print(f"    ✓ Standard: {std_time:.2f}ms")

        # Tom Sawyer transfer
        print("  Testing Tom Sawyer transfer...")
        ts_result = orchestrator.transfer_tom_sawyer(
            source, target, config,
            num_workers=5,  # Use 5 for faster testing
            variation_range=(0.9, 1.1),
            enable_parallel=False
        )

        assert ts_result.result_image.shape == target.shape
        assert ts_result.tom_sawyer_metrics is not None

        ts_time = ts_result.metrics.execution_time_ms
        overhead = (ts_time / std_time - 1.0) * 100

        print(f"    ✓ Tom Sawyer: {ts_time:.2f}ms")
        print(f"    ✓ Overhead: {overhead:+.1f}%")
        print(f"    ✓ Confidence: {ts_result.tom_sawyer_metrics.consensus_confidence:.2%}")

        return True
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all verification tests."""
    print("=" * 70)
    print("TOM SAWYER METHOD - VERIFICATION")
    print("=" * 70)

    # Create test images
    source, target = create_test_images()

    # Run component tests
    results = []
    results.append(test_worker_manager())
    results.append(test_variation_controller())
    results.append(test_consensus_aggregator())
    results.append(test_tom_sawyer_processor(source, target))
    results.append(test_orchestrator_integration(source, target))

    # Summary
    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)

    total = len(results)
    passed = sum(results)
    failed = total - passed

    print(f"\nTotal tests: {total}")
    print(f"Passed: {passed} ✓")
    print(f"Failed: {failed} ✗")

    if failed == 0:
        print("\n🎉 ALL TESTS PASSED - Tom Sawyer implementation is working correctly!")
        return 0
    else:
        print(f"\n⚠️  {failed} test(s) failed - Please review the errors above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
