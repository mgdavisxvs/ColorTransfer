"""
Batch Processor
===============

Process multiple images in a directory with color transfer operations.

Features:
- Recursive directory scanning
- Parallel processing with thread/process pools
- Progress tracking
- Error handling and recovery
- Result organization
"""

import cv2
import numpy as np
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import logging
from dataclasses import dataclass
from datetime import datetime

from ..transfer_engine import TransferConfig, TransferAlgorithm
from ..interface_layer.orchestrator import TransferOrchestrator

logger = logging.getLogger(__name__)


@dataclass
class BatchItem:
    """Single item in batch processing queue."""
    target_path: Path
    output_path: Path
    index: int
    total: int


@dataclass
class BatchResult:
    """Result of batch processing operation."""
    target_path: Path
    output_path: Path
    success: bool
    error: Optional[str] = None
    execution_time_ms: float = 0.0


class BatchProcessor:
    """
    Process multiple images with color transfer in batch mode.

    Example:
        >>> processor = BatchProcessor()
        >>> results = processor.process_directory(
        ...     source_image="palette.jpg",
        ...     target_dir="./photos",
        ...     output_dir="./results",
        ...     config=TransferConfig(),
        ...     recursive=True,
        ...     max_workers=4
        ... )
    """

    SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'}

    def __init__(self, orchestrator: Optional[TransferOrchestrator] = None):
        """
        Initialize batch processor.

        Parameters:
        -----------
        orchestrator : TransferOrchestrator, optional
            Orchestrator instance to use. Creates new one if not provided.
        """
        self.orchestrator = orchestrator or TransferOrchestrator()
        self.results: List[BatchResult] = []

    def process_directory(
        self,
        source_image: str,
        target_dir: str,
        output_dir: str,
        config: Optional[TransferConfig] = None,
        recursive: bool = True,
        max_workers: int = 4,
        use_processes: bool = False,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        pattern: str = "*"
    ) -> List[BatchResult]:
        """
        Process all images in a directory.

        Parameters:
        -----------
        source_image : str
            Path to source image (color palette donor)
        target_dir : str
            Directory containing target images to process
        output_dir : str
            Directory to save results
        config : TransferConfig, optional
            Transfer configuration
        recursive : bool
            Recursively scan subdirectories
        max_workers : int
            Number of parallel workers
        use_processes : bool
            Use ProcessPoolExecutor instead of ThreadPoolExecutor
        progress_callback : callable, optional
            Callback function(current, total, filename) for progress updates
        pattern : str
            File pattern to match (e.g., "*.jpg")

        Returns:
        --------
        List[BatchResult]
            Results for each processed image
        """
        source_path = Path(source_image)
        target_path = Path(target_dir)
        output_path = Path(output_dir)

        # Validate inputs
        if not source_path.exists():
            raise FileNotFoundError(f"Source image not found: {source_image}")
        if not target_path.exists():
            raise FileNotFoundError(f"Target directory not found: {target_dir}")

        # Create output directory
        output_path.mkdir(parents=True, exist_ok=True)

        # Find all target images
        target_images = self._find_images(target_path, recursive, pattern)

        if not target_images:
            logger.warning(f"No images found in {target_dir}")
            return []

        logger.info(f"Found {len(target_images)} images to process")

        # Load source image once
        source_img = cv2.imread(str(source_path))
        if source_img is None:
            raise ValueError(f"Failed to load source image: {source_image}")

        # Create batch items
        batch_items = []
        for idx, target_img_path in enumerate(target_images):
            # Preserve directory structure
            rel_path = target_img_path.relative_to(target_path)
            out_path = output_path / rel_path
            out_path.parent.mkdir(parents=True, exist_ok=True)

            batch_items.append(BatchItem(
                target_path=target_img_path,
                output_path=out_path,
                index=idx,
                total=len(target_images)
            ))

        # Process in parallel
        self.results = []
        executor_class = ProcessPoolExecutor if use_processes else ThreadPoolExecutor

        with executor_class(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    self._process_single,
                    source_img,
                    item,
                    config
                ): item for item in batch_items
            }

            for future in as_completed(futures):
                item = futures[future]
                try:
                    result = future.result()
                    self.results.append(result)

                    if progress_callback:
                        progress_callback(
                            len(self.results),
                            len(batch_items),
                            str(item.target_path.name)
                        )

                    if result.success:
                        logger.info(f"✓ Processed {item.target_path.name}")
                    else:
                        logger.error(f"✗ Failed {item.target_path.name}: {result.error}")

                except Exception as e:
                    logger.error(f"Exception processing {item.target_path.name}: {e}")
                    self.results.append(BatchResult(
                        target_path=item.target_path,
                        output_path=item.output_path,
                        success=False,
                        error=str(e)
                    ))

        return self.results

    def _process_single(
        self,
        source_img: np.ndarray,
        item: BatchItem,
        config: Optional[TransferConfig]
    ) -> BatchResult:
        """Process a single image."""
        start_time = datetime.now()

        try:
            # Load target image
            target_img = cv2.imread(str(item.target_path))
            if target_img is None:
                return BatchResult(
                    target_path=item.target_path,
                    output_path=item.output_path,
                    success=False,
                    error="Failed to load image"
                )

            # Perform transfer
            result = self.orchestrator.transfer(
                source_image=source_img,
                target_image=target_img,
                config=config,
                generate_diagnostics=False,
                profile_performance=True,
                interface_type="BATCH"
            )

            # Save result
            cv2.imwrite(str(item.output_path), result.result_image)

            execution_time = (datetime.now() - start_time).total_seconds() * 1000

            return BatchResult(
                target_path=item.target_path,
                output_path=item.output_path,
                success=True,
                execution_time_ms=execution_time
            )

        except Exception as e:
            return BatchResult(
                target_path=item.target_path,
                output_path=item.output_path,
                success=False,
                error=str(e)
            )

    def _find_images(
        self,
        directory: Path,
        recursive: bool,
        pattern: str
    ) -> List[Path]:
        """Find all image files in directory."""
        images = []

        if recursive:
            pattern_path = f"**/{pattern}"
        else:
            pattern_path = pattern

        for path in directory.glob(pattern_path):
            if path.is_file() and path.suffix.lower() in self.SUPPORTED_FORMATS:
                images.append(path)

        return sorted(images)

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of batch processing results."""
        if not self.results:
            return {
                "total": 0,
                "success": 0,
                "failed": 0,
                "success_rate": 0.0
            }

        total = len(self.results)
        success = sum(1 for r in self.results if r.success)
        failed = total - success

        successful_results = [r for r in self.results if r.success]
        avg_time = (
            sum(r.execution_time_ms for r in successful_results) / len(successful_results)
            if successful_results else 0.0
        )

        return {
            "total": total,
            "success": success,
            "failed": failed,
            "success_rate": (success / total) * 100 if total > 0 else 0.0,
            "avg_execution_time_ms": avg_time,
            "total_time_ms": sum(r.execution_time_ms for r in successful_results)
        }
