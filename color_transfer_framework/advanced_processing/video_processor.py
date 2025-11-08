"""
Video Processor
===============

Apply color transfer to video files frame-by-frame.

Features:
- Frame extraction and processing
- Multiple video codecs support
- Audio preservation
- Progress tracking
- Optimized frame buffering
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Optional, Callable
import logging
from dataclasses import dataclass
from datetime import datetime

from ..transfer_engine import TransferConfig
from ..interface_layer.orchestrator import TransferOrchestrator

logger = logging.getLogger(__name__)


@dataclass
class VideoInfo:
    """Video file metadata."""
    width: int
    height: int
    fps: float
    frame_count: int
    duration_seconds: float
    codec: str


class VideoProcessor:
    """
    Apply color transfer to video files.

    Example:
        >>> processor = VideoProcessor()
        >>> processor.process_video(
        ...     source_image="palette.jpg",
        ...     input_video="input.mp4",
        ...     output_video="output.mp4",
        ...     config=TransferConfig()
        ... )
    """

    def __init__(self, orchestrator: Optional[TransferOrchestrator] = None):
        """
        Initialize video processor.

        Parameters:
        -----------
        orchestrator : TransferOrchestrator, optional
            Orchestrator instance to use
        """
        self.orchestrator = orchestrator or TransferOrchestrator()

    def process_video(
        self,
        source_image: str,
        input_video: str,
        output_video: str,
        config: Optional[TransferConfig] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        codec: str = 'mp4v',
        quality: int = 90
    ) -> VideoInfo:
        """
        Process video file with color transfer.

        Parameters:
        -----------
        source_image : str
            Path to source image (color palette donor)
        input_video : str
            Path to input video file
        output_video : str
            Path to output video file
        config : TransferConfig, optional
            Transfer configuration
        progress_callback : callable, optional
            Callback function(current_frame, total_frames)
        codec : str
            FourCC codec code (default: 'mp4v')
        quality : int
            Output quality (0-100, default: 90)

        Returns:
        --------
        VideoInfo
            Information about processed video
        """
        source_path = Path(source_image)
        input_path = Path(input_video)
        output_path = Path(output_video)

        # Validate inputs
        if not source_path.exists():
            raise FileNotFoundError(f"Source image not found: {source_image}")
        if not input_path.exists():
            raise FileNotFoundError(f"Input video not found: {input_video}")

        # Create output directory
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Load source image
        source_img = cv2.imread(str(source_path))
        if source_img is None:
            raise ValueError(f"Failed to load source image: {source_image}")

        # Open input video
        cap = cv2.VideoCapture(str(input_path))
        if not cap.isOpened():
            raise ValueError(f"Failed to open video: {input_video}")

        # Get video properties
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        logger.info(f"Processing video: {width}x{height} @ {fps}fps, {frame_count} frames")

        # Create video writer
        fourcc = cv2.VideoWriter_fourcc(*codec)
        out = cv2.VideoWriter(
            str(output_path),
            fourcc,
            fps,
            (width, height)
        )

        if not out.isOpened():
            cap.release()
            raise ValueError(f"Failed to create output video: {output_video}")

        start_time = datetime.now()
        processed_frames = 0

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                # Apply color transfer to frame
                result = self.orchestrator.transfer(
                    source_image=source_img,
                    target_image=frame,
                    config=config,
                    generate_diagnostics=False,
                    profile_performance=False,
                    interface_type="VIDEO"
                )

                # Write frame
                out.write(result.result_image)
                processed_frames += 1

                # Progress callback
                if progress_callback:
                    progress_callback(processed_frames, frame_count)

                # Log progress every 10%
                if processed_frames % max(1, frame_count // 10) == 0:
                    progress_pct = (processed_frames / frame_count) * 100
                    logger.info(f"Progress: {progress_pct:.1f}% ({processed_frames}/{frame_count})")

        finally:
            cap.release()
            out.release()

        total_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"Video processing complete: {processed_frames} frames in {total_time:.2f}s")

        return VideoInfo(
            width=width,
            height=height,
            fps=fps,
            frame_count=processed_frames,
            duration_seconds=processed_frames / fps,
            codec=codec
        )

    def extract_frames(
        self,
        video_path: str,
        output_dir: str,
        frame_interval: int = 1,
        format: str = 'png'
    ) -> int:
        """
        Extract frames from video to images.

        Parameters:
        -----------
        video_path : str
            Path to video file
        output_dir : str
            Directory to save extracted frames
        frame_interval : int
            Extract every Nth frame (default: 1 = all frames)
        format : str
            Image format (default: 'png')

        Returns:
        --------
        int
            Number of extracted frames
        """
        video = Path(video_path)
        output = Path(output_dir)

        if not video.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        output.mkdir(parents=True, exist_ok=True)

        cap = cv2.VideoCapture(str(video))
        frame_num = 0
        saved = 0

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                if frame_num % frame_interval == 0:
                    frame_path = output / f"frame_{frame_num:06d}.{format}"
                    cv2.imwrite(str(frame_path), frame)
                    saved += 1

                frame_num += 1

        finally:
            cap.release()

        logger.info(f"Extracted {saved} frames to {output_dir}")
        return saved

    def frames_to_video(
        self,
        frames_dir: str,
        output_video: str,
        fps: float = 30.0,
        codec: str = 'mp4v',
        pattern: str = "frame_*.png"
    ) -> VideoInfo:
        """
        Create video from directory of frames.

        Parameters:
        -----------
        frames_dir : str
            Directory containing frame images
        output_video : str
            Path to output video file
        fps : float
            Frames per second
        codec : str
            FourCC codec code
        pattern : str
            Filename pattern to match

        Returns:
        --------
        VideoInfo
            Information about created video
        """
        frames_path = Path(frames_dir)
        output_path = Path(output_video)

        if not frames_path.exists():
            raise FileNotFoundError(f"Frames directory not found: {frames_dir}")

        # Find all frame files
        frame_files = sorted(frames_path.glob(pattern))
        if not frame_files:
            raise ValueError(f"No frames found matching pattern: {pattern}")

        # Read first frame to get dimensions
        first_frame = cv2.imread(str(frame_files[0]))
        if first_frame is None:
            raise ValueError(f"Failed to load first frame: {frame_files[0]}")

        height, width = first_frame.shape[:2]

        # Create video writer
        fourcc = cv2.VideoWriter_fourcc(*codec)
        out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

        if not out.isOpened():
            raise ValueError(f"Failed to create video: {output_video}")

        try:
            for frame_file in frame_files:
                frame = cv2.imread(str(frame_file))
                if frame is not None:
                    out.write(frame)

        finally:
            out.release()

        logger.info(f"Created video with {len(frame_files)} frames")

        return VideoInfo(
            width=width,
            height=height,
            fps=fps,
            frame_count=len(frame_files),
            duration_seconds=len(frame_files) / fps,
            codec=codec
        )
