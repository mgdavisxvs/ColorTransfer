"""
Webcam Processor
================

Real-time color transfer for webcam/camera feeds.

Features:
- Real-time video processing
- Multiple camera support
- FPS monitoring
- Frame buffering for performance
- Recording support
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Optional, Callable
import logging
from datetime import datetime
from collections import deque
import time

from ..transfer_engine import TransferConfig
from ..interface_layer.orchestrator import TransferOrchestrator

logger = logging.getLogger(__name__)


class WebcamProcessor:
    """
    Real-time color transfer for webcam/camera feeds.

    Example:
        >>> processor = WebcamProcessor()
        >>> processor.start_preview(
        ...     source_image="palette.jpg",
        ...     camera_id=0,
        ...     config=TransferConfig()
        ... )
    """

    def __init__(self, orchestrator: Optional[TransferOrchestrator] = None):
        """
        Initialize webcam processor.

        Parameters:
        -----------
        orchestrator : TransferOrchestrator, optional
            Orchestrator instance to use
        """
        self.orchestrator = orchestrator or TransferOrchestrator()
        self.is_running = False
        self.fps_history = deque(maxlen=30)

    def start_preview(
        self,
        source_image: str,
        camera_id: int = 0,
        config: Optional[TransferConfig] = None,
        show_fps: bool = True,
        window_name: str = "Color Transfer - Webcam",
        record_output: Optional[str] = None,
        frame_skip: int = 0
    ) -> None:
        """
        Start real-time webcam preview with color transfer.

        Parameters:
        -----------
        source_image : str
            Path to source image (color palette donor)
        camera_id : int
            Camera device ID (default: 0)
        config : TransferConfig, optional
            Transfer configuration
        show_fps : bool
            Display FPS counter on preview
        window_name : str
            Preview window title
        record_output : str, optional
            Path to save recorded output video
        frame_skip : int
            Skip N frames between processing (0 = process all frames)

        Controls:
        ---------
        - Press 'q' to quit
        - Press 's' to save current frame
        - Press 'r' to toggle recording
        - Press 'p' to pause/resume
        """
        source_path = Path(source_image)

        if not source_path.exists():
            raise FileNotFoundError(f"Source image not found: {source_image}")

        # Load source image
        source_img = cv2.imread(str(source_path))
        if source_img is None:
            raise ValueError(f"Failed to load source image: {source_image}")

        # Open camera
        cap = cv2.VideoCapture(camera_id)
        if not cap.isOpened():
            raise ValueError(f"Failed to open camera {camera_id}")

        # Get camera properties
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

        logger.info(f"Camera opened: {width}x{height} @ {fps}fps")

        # Setup video recorder if requested
        out = None
        if record_output:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(record_output, fourcc, fps, (width, height))
            logger.info(f"Recording to: {record_output}")

        self.is_running = True
        is_recording = record_output is not None
        is_paused = False
        frame_count = 0

        try:
            while self.is_running:
                start_time = time.time()

                ret, frame = cap.read()
                if not ret:
                    logger.error("Failed to read frame from camera")
                    break

                frame_count += 1

                # Skip frames for performance if needed
                if frame_skip > 0 and frame_count % (frame_skip + 1) != 0:
                    display_frame = frame
                else:
                    if not is_paused:
                        # Apply color transfer
                        result = self.orchestrator.transfer(
                            source_image=source_img,
                            target_image=frame,
                            config=config,
                            generate_diagnostics=False,
                            profile_performance=False,
                            interface_type="WEBCAM"
                        )
                        display_frame = result.result_image
                    else:
                        display_frame = frame

                # Show FPS
                if show_fps:
                    fps_value = self._calculate_fps(time.time() - start_time)
                    cv2.putText(
                        display_frame,
                        f"FPS: {fps_value:.1f}",
                        (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1,
                        (0, 255, 0),
                        2
                    )

                # Show status indicators
                status_y = 70
                if is_paused:
                    cv2.putText(
                        display_frame,
                        "PAUSED",
                        (10, status_y),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1,
                        (0, 255, 255),
                        2
                    )
                    status_y += 40

                if is_recording:
                    cv2.circle(display_frame, (20, status_y + 10), 10, (0, 0, 255), -1)
                    cv2.putText(
                        display_frame,
                        "REC",
                        (40, status_y + 20),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 0, 255),
                        2
                    )

                # Record frame if recording
                if is_recording and out is not None and not is_paused:
                    out.write(display_frame)

                # Display
                cv2.imshow(window_name, display_frame)

                # Handle keyboard input
                key = cv2.waitKey(1) & 0xFF

                if key == ord('q'):
                    # Quit
                    logger.info("Quitting...")
                    break

                elif key == ord('s'):
                    # Save current frame
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    save_path = f"webcam_frame_{timestamp}.png"
                    cv2.imwrite(save_path, display_frame)
                    logger.info(f"Frame saved: {save_path}")

                elif key == ord('r'):
                    # Toggle recording
                    if out is None:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        output_path = f"webcam_recording_{timestamp}.mp4"
                        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
                        is_recording = True
                        logger.info(f"Recording started: {output_path}")
                    else:
                        is_recording = not is_recording
                        logger.info(f"Recording {'resumed' if is_recording else 'paused'}")

                elif key == ord('p'):
                    # Toggle pause
                    is_paused = not is_paused
                    logger.info(f"Preview {'paused' if is_paused else 'resumed'}")

        finally:
            self.is_running = False
            cap.release()
            if out is not None:
                out.release()
            cv2.destroyAllWindows()
            logger.info("Webcam processor stopped")

    def _calculate_fps(self, frame_time: float) -> float:
        """Calculate current FPS from frame time."""
        if frame_time > 0:
            fps = 1.0 / frame_time
            self.fps_history.append(fps)

        if self.fps_history:
            return sum(self.fps_history) / len(self.fps_history)
        return 0.0

    def process_camera_frame(
        self,
        source_image: np.ndarray,
        frame: np.ndarray,
        config: Optional[TransferConfig] = None
    ) -> np.ndarray:
        """
        Process a single camera frame.

        Parameters:
        -----------
        source_image : np.ndarray
            Source image (color palette donor)
        frame : np.ndarray
            Camera frame to process
        config : TransferConfig, optional
            Transfer configuration

        Returns:
        --------
        np.ndarray
            Processed frame
        """
        result = self.orchestrator.transfer(
            source_image=source_image,
            target_image=frame,
            config=config,
            generate_diagnostics=False,
            profile_performance=False,
            interface_type="WEBCAM"
        )
        return result.result_image

    def stop(self):
        """Stop the webcam processor."""
        self.is_running = False
