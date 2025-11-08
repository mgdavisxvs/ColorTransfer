"""
Transfer Orchestrator
====================

Central coordination logic for all interface types.

This module provides a unified, high-level API for performing color transfer
operations with integrated performance monitoring, diagnostics, and logging.

Design Principles:
- Facade Pattern: Simplified interface to complex subsystems
- Dependency Injection: Components injected for testability
- Single Responsibility: Orchestration only, no business logic
"""

import numpy as np
import cv2
import base64
import io
import hashlib
import time
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, Callable
from dataclasses import dataclass
import uuid
import asyncio

from ..transfer_engine import TransferEngine, TransferConfig, TransferAlgorithm
from ..optimizer_engine import OptimizerEngine, OptimizationMode, PerformanceMetrics
from ..color_space_manager import ColorSpaceManager
from ..diagnostics_visualizer import DiagnosticsVisualizer
from ..persistence_logger import PersistenceLogger

# Optional imports with graceful degradation
try:
    from ..complexity_analyzer import ComplexityAnalyzer
    ANALYZER_AVAILABLE = True
except ImportError:
    ANALYZER_AVAILABLE = False


@dataclass
class OrchestrationResult:
    """Complete result of a transfer operation."""
    result_image: np.ndarray
    metrics: PerformanceMetrics
    run_id: str
    source_hash: str
    target_hash: str
    result_hash: str
    config: TransferConfig
    visualization_paths: Optional[Dict[str, str]] = None


class TransferOrchestrator:
    """
    Orchestrates color transfer operations across all framework components.

    This class serves as the primary integration point for the interface layer,
    coordinating the TransferEngine, OptimizerEngine, and DiagnosticsVisualizer.
    """

    def __init__(
        self,
        transfer_engine: Optional[TransferEngine] = None,
        optimizer_engine: Optional[OptimizerEngine] = None,
        visualizer: Optional[DiagnosticsVisualizer] = None,
        persistence_logger: Optional[PersistenceLogger] = None,
        enable_logging: bool = True
    ):
        """
        Initialize orchestrator.

        Parameters:
        ----------
        transfer_engine : TransferEngine, optional
            Engine for color transfer. Creates default if None.
        optimizer_engine : OptimizerEngine, optional
            Engine for performance optimization. Creates default if None.
        visualizer : DiagnosticsVisualizer, optional
            Visualizer for diagnostics. Creates default if None.
        persistence_logger : PersistenceLogger, optional
            Logger for persistence. Creates default if None.
        enable_logging : bool
            Whether to enable persistence logging
        """
        self.transfer_engine = transfer_engine or TransferEngine()
        self.optimizer_engine = optimizer_engine or OptimizerEngine()
        self.visualizer = visualizer or DiagnosticsVisualizer()
        self.persistence_logger = persistence_logger or PersistenceLogger()
        self.enable_logging = enable_logging

    def transfer(
        self,
        source_image: np.ndarray,
        target_image: np.ndarray,
        config: Optional[TransferConfig] = None,
        mask: Optional[np.ndarray] = None,
        enable_gpu: bool = False,
        generate_diagnostics: bool = False,
        output_dir: Optional[Path] = None,
        profile_performance: bool = True,
        interface_type: str = "DIRECT",
        progress_callback: Optional[Callable[[str, int], None]] = None
    ) -> OrchestrationResult:
        """
        Perform complete color transfer operation with optional diagnostics.

        Parameters:
        ----------
        source_image : np.ndarray
            Source image (color palette donor)
        target_image : np.ndarray
            Target image (to be transformed)
        config : TransferConfig, optional
            Transfer configuration
        mask : np.ndarray, optional
            Mask for selective transfer
        enable_gpu : bool
            Whether to use GPU acceleration
        generate_diagnostics : bool
            Whether to generate diagnostic visualizations
        output_dir : Path, optional
            Directory for diagnostic outputs
        profile_performance : bool
            Whether to profile performance metrics

        Returns:
        -------
        OrchestrationResult
            Complete results including image, metrics, and metadata
        """
        # Generate unique run ID
        run_id = str(uuid.uuid4())

        # Helper for progress updates
        def emit_progress(status: str, percent: int):
            if progress_callback:
                try:
                    progress_callback(status, percent)
                except Exception:
                    pass  # Don't fail if progress callback errors

        # Progress: Starting
        emit_progress("initializing", 0)

        # Use default config if not provided
        if config is None:
            config = TransferConfig()

        emit_progress("loading_images", 10)

        # Compute image hashes for tracking
        source_hash = self._compute_hash(source_image)
        target_hash = self._compute_hash(target_image)

        emit_progress("calculating_statistics", 30)

        # Perform transfer with optional profiling
        if profile_performance:
            start_time = time.perf_counter()

            emit_progress("applying_transform", 50)
            result = self.transfer_engine.transfer(
                source_image, target_image, config, mask
            )
            execution_time = (time.perf_counter() - start_time) * 1000  # ms

            # Create metrics
            metrics = PerformanceMetrics(
                execution_time_ms=execution_time,
                memory_used_mb=self.optimizer_engine.memory_tracker.get_peak_mb(),
                throughput_images_per_sec=1000.0 / execution_time if execution_time > 0 else 0.0
            )
        else:
            emit_progress("applying_transform", 50)
            result = self.transfer_engine.transfer(
                source_image, target_image, config, mask
            )
            metrics = PerformanceMetrics(
                execution_time_ms=0.0,
                memory_used_mb=0.0,
                throughput_images_per_sec=0.0
            )

        emit_progress("processing_result", 70)

        # Compute result hash
        result_hash = self._compute_hash(result)

        # Generate diagnostics if requested
        visualization_paths = None
        if generate_diagnostics and output_dir is not None:
            emit_progress("generating_diagnostics", 80)
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            visualization_paths = self.visualizer.generate_comprehensive_report(
                source_image, target_image, result, str(output_dir)
            )

        # Log to persistence layer
        if self.enable_logging:
            emit_progress("saving_metadata", 90)
            try:
                self.persistence_logger.log_transfer(
                    run_id=run_id,
                    source_hash=source_hash,
                    target_hash=target_hash,
                    result_hash=result_hash,
                    algorithm=config.algorithm.value,
                    config=config.to_dict(),
                    metrics={
                        'execution_time_ms': metrics.execution_time_ms,
                        'memory_used_mb': metrics.memory_used_mb,
                        'throughput_images_per_sec': metrics.throughput_images_per_sec
                    },
                    interface_type=interface_type,
                    success=True
                )
            except Exception as e:
                # Don't fail the operation if logging fails
                pass

        emit_progress("complete", 100)

        return OrchestrationResult(
            result_image=result,
            metrics=metrics,
            run_id=run_id,
            source_hash=source_hash,
            target_hash=target_hash,
            result_hash=result_hash,
            config=config,
            visualization_paths=visualization_paths
        )

    def transfer_from_paths(
        self,
        source_path: str,
        target_path: str,
        output_path: str,
        config: Optional[TransferConfig] = None,
        mask_path: Optional[str] = None,
        enable_gpu: bool = False,
        generate_diagnostics: bool = False,
        interface_type: str = "CLI"
    ) -> OrchestrationResult:
        """
        Perform transfer from file paths.

        Parameters:
        ----------
        source_path : str
            Path to source image
        target_path : str
            Path to target image
        output_path : str
            Path to save result
        config : TransferConfig, optional
            Transfer configuration
        mask_path : str, optional
            Path to mask image
        enable_gpu : bool
            Whether to use GPU acceleration
        generate_diagnostics : bool
            Whether to generate diagnostic visualizations

        Returns:
        -------
        OrchestrationResult
            Complete results
        """
        # Load images
        source = cv2.imread(source_path)
        target = cv2.imread(target_path)

        if source is None:
            raise ValueError(f"Failed to load source image: {source_path}")
        if target is None:
            raise ValueError(f"Failed to load target image: {target_path}")

        # Load mask if provided
        mask = None
        if mask_path:
            mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
            if mask is None:
                raise ValueError(f"Failed to load mask image: {mask_path}")

        # Determine output directory for diagnostics
        output_dir = None
        if generate_diagnostics:
            output_dir = Path(output_path).parent / "diagnostics"

        # Perform transfer
        result = self.transfer(
            source, target, config, mask, enable_gpu,
            generate_diagnostics, output_dir,
            interface_type=interface_type,
            progress_callback=None  # CLI doesn't use progress callbacks
        )

        # Save result image
        cv2.imwrite(output_path, result.result_image)

        return result

    def transfer_from_base64(
        self,
        source_b64: str,
        target_b64: str,
        config: Optional[TransferConfig] = None,
        mask_b64: Optional[str] = None,
        enable_gpu: bool = False,
        interface_type: str = "API",
        progress_callback: Optional[Callable[[str, int], None]] = None
    ) -> Tuple[str, OrchestrationResult]:
        """
        Perform transfer from base64 encoded images.

        Parameters:
        ----------
        source_b64 : str
            Base64 encoded source image
        target_b64 : str
            Base64 encoded target image
        config : TransferConfig, optional
            Transfer configuration
        mask_b64 : str, optional
            Base64 encoded mask image
        enable_gpu : bool
            Whether to use GPU acceleration

        Returns:
        -------
        tuple[str, OrchestrationResult]
            Base64 encoded result and orchestration result
        """
        # Decode images
        source = self._decode_base64_image(source_b64)
        target = self._decode_base64_image(target_b64)

        mask = None
        if mask_b64:
            mask = self._decode_base64_image(mask_b64, grayscale=True)

        # Perform transfer (no diagnostics for API)
        result = self.transfer(
            source, target, config, mask, enable_gpu,
            generate_diagnostics=False, profile_performance=True,
            interface_type=interface_type,
            progress_callback=progress_callback
        )

        # Encode result
        result_b64 = self._encode_base64_image(result.result_image)

        return result_b64, result

    @staticmethod
    def _compute_hash(image: np.ndarray) -> str:
        """Compute SHA256 hash of image."""
        return hashlib.sha256(image.tobytes()).hexdigest()

    @staticmethod
    def _decode_base64_image(b64_string: str, grayscale: bool = False) -> np.ndarray:
        """
        Decode base64 string to numpy array.

        Parameters:
        ----------
        b64_string : str
            Base64 encoded image
        grayscale : bool
            Whether to load as grayscale

        Returns:
        -------
        np.ndarray
            Decoded image
        """
        # Remove data URL prefix if present
        if ',' in b64_string:
            b64_string = b64_string.split(',', 1)[1]

        # Decode base64
        img_bytes = base64.b64decode(b64_string)

        # Convert to numpy array
        nparr = np.frombuffer(img_bytes, np.uint8)

        # Decode image
        if grayscale:
            img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
        else:
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            raise ValueError("Failed to decode base64 image")

        return img

    @staticmethod
    def _encode_base64_image(image: np.ndarray, format: str = '.png') -> str:
        """
        Encode numpy array to base64 string.

        Parameters:
        ----------
        image : np.ndarray
            Image to encode
        format : str
            Image format (e.g., '.png', '.jpg')

        Returns:
        -------
        str
            Base64 encoded image
        """
        # Encode image to bytes
        success, buffer = cv2.imencode(format, image)
        if not success:
            raise ValueError(f"Failed to encode image to {format}")

        # Convert to base64
        img_b64 = base64.b64encode(buffer).decode('utf-8')

        return img_b64
