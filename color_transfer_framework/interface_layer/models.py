"""
Pydantic Models for InterfaceLayer
==================================

Data models for API requests/responses and configuration.

This module defines the data structures used across all interface types
(CLI, API, WebUI) for consistency and validation.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List
from enum import Enum


class AlgorithmType(str, Enum):
    """Available transfer algorithms."""
    REINHARD_LAB = "reinhard_lab"
    REINHARD_LCH = "reinhard_lch"
    RGB_DIRECT = "rgb_direct"
    HISTOGRAM_MATCH = "histogram_match"


class OptimizationMode(str, Enum):
    """Execution modes."""
    CPU = "cpu"
    GPU = "gpu"


class TransferConfigModel(BaseModel):
    """Transfer configuration for API requests."""
    algorithm: AlgorithmType = AlgorithmType.REINHARD_LAB
    blend_factor: float = Field(default=1.0, ge=0.0, le=1.0)
    clip_output: bool = True
    preserve_luminance: bool = False
    epsilon: float = Field(default=1e-10, gt=0.0)
    use_gpu: bool = False

    class Config:
        use_enum_values = True


class TransferRequest(BaseModel):
    """Request for color transfer operation."""
    source_image: str = Field(..., description="Base64 encoded source image")
    target_image: str = Field(..., description="Base64 encoded target image")
    mask_image: Optional[str] = Field(None, description="Base64 encoded mask image (optional)")
    config: TransferConfigModel = Field(default_factory=TransferConfigModel)
    client_id: Optional[str] = Field(None, description="Client ID for WebSocket progress updates (optional)")

    @field_validator('source_image', 'target_image', 'mask_image')
    @classmethod
    def validate_base64(cls, v):
        """Validate base64 strings are not empty."""
        if v is not None and len(v) == 0:
            raise ValueError("Base64 image string cannot be empty")
        return v


class PerformanceMetricsModel(BaseModel):
    """Performance metrics for transfer operation."""
    execution_time_ms: float
    memory_used_mb: float
    throughput_images_per_sec: float
    peak_vram_mb: Optional[float] = None


class TransferResponse(BaseModel):
    """Response from color transfer operation."""
    result_image: str = Field(..., description="Base64 encoded result image")
    metrics: PerformanceMetricsModel
    run_id: Optional[str] = None


class AlgorithmInfo(BaseModel):
    """Information about a transfer algorithm."""
    name: str
    value: str
    description: str


class AlgorithmsResponse(BaseModel):
    """List of available algorithms."""
    algorithms: List[AlgorithmInfo]


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    modules_available: Dict[str, bool]


class ErrorResponse(BaseModel):
    """Error response."""
    error: str
    detail: Optional[str] = None
    status_code: int


class BenchmarkRequest(BaseModel):
    """Request for benchmarking operation."""
    image_sizes: List[str] = Field(default=["512x512", "1080p", "4k"])
    modes: List[OptimizationMode] = Field(default=[OptimizationMode.CPU])
    algorithms: Optional[List[AlgorithmType]] = None
    batch_sizes: List[int] = Field(default=[1, 10])
    output_path: Optional[str] = None

    @field_validator('image_sizes')
    @classmethod
    def validate_sizes(cls, v):
        """Validate image size specifications."""
        valid_sizes = ["512x512", "1080p", "4k", "small", "hd"]
        for size in v:
            if size not in valid_sizes and 'x' not in size:
                raise ValueError(f"Invalid size: {size}. Must be one of {valid_sizes} or WxH format")
        return v


class BenchmarkResult(BaseModel):
    """Single benchmark result."""
    algorithm: str
    mode: str
    image_size: str
    batch_size: int
    avg_execution_time_ms: float
    throughput_images_per_sec: float
    peak_memory_mb: float
    peak_vram_mb: Optional[float] = None


class BenchmarkResponse(BaseModel):
    """Complete benchmark results."""
    results: List[BenchmarkResult]
    summary: Dict[str, Any]
    output_files: List[str]
