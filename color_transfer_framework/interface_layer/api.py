"""
FastAPI REST Service
===================

High-performance RESTful API for color transfer operations.

Endpoints:
- GET /api/v1/algorithms: List available algorithms
- POST /api/v1/transfer: Perform color transfer
- GET /api/v1/health: Health check
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from typing import Dict, Any

from .models import (
    TransferRequest,
    TransferResponse,
    AlgorithmsResponse,
    AlgorithmInfo,
    HealthResponse,
    PerformanceMetricsModel
)
from .orchestrator import TransferOrchestrator
from ..transfer_engine import TransferConfig, TransferAlgorithm
from .. import __version__

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Color Transfer Framework API",
    description="RESTful API for transferring color palettes between images",
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize orchestrator (singleton for the app lifecycle)
orchestrator = TransferOrchestrator()


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Color Transfer Framework API",
        "version": __version__,
        "docs": "/docs",
        "health": "/api/v1/health"
    }


@app.get("/api/v1/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.

    Returns service status and available modules.
    """
    # Check module availability
    modules_available = {
        "transfer_engine": True,
        "optimizer_engine": True,
        "diagnostics_visualizer": True,
    }

    try:
        from ..complexity_analyzer import ComplexityAnalyzer
        modules_available["complexity_analyzer"] = True
    except ImportError:
        modules_available["complexity_analyzer"] = False

    return HealthResponse(
        status="ok",
        version=__version__,
        modules_available=modules_available
    )


@app.get("/api/v1/algorithms", response_model=AlgorithmsResponse)
async def list_algorithms():
    """
    List all available color transfer algorithms.

    Returns:
    -------
    AlgorithmsResponse
        List of available algorithms with descriptions
    """
    algorithms = [
        AlgorithmInfo(
            name="Reinhard L*a*b*",
            value="reinhard_lab",
            description="Reinhard et al. method in perceptually uniform L*a*b* color space (default)"
        ),
        AlgorithmInfo(
            name="Reinhard LCH",
            value="reinhard_lch",
            description="Reinhard method in cylindrical LCH space (preserves hue relationships)"
        ),
        AlgorithmInfo(
            name="RGB Direct",
            value="rgb_direct",
            description="Direct RGB channel transfer (fast but less perceptually accurate)"
        ),
        AlgorithmInfo(
            name="Histogram Match",
            value="histogram_match",
            description="Histogram matching algorithm (precise distribution matching)"
        ),
    ]

    return AlgorithmsResponse(algorithms=algorithms)


@app.post("/api/v1/transfer", response_model=TransferResponse)
async def transfer_colors(request: TransferRequest):
    """
    Perform color transfer operation.

    This endpoint accepts base64-encoded images and returns the transformed result
    along with performance metrics.

    Parameters:
    ----------
    request : TransferRequest
        Transfer request containing source, target, and configuration

    Returns:
    -------
    TransferResponse
        Result image (base64) and performance metrics

    Raises:
    ------
    HTTPException
        400: Invalid request (malformed base64, invalid config)
        422: Unprocessable entity (validation errors)
        500: Server error (processing failure)
    """
    try:
        logger.info(f"Transfer request: algorithm={request.config.algorithm}")

        # Build transfer configuration
        config = TransferConfig(
            algorithm=TransferAlgorithm(request.config.algorithm),
            blend_factor=request.config.blend_factor,
            clip_output=request.config.clip_output,
            preserve_luminance=request.config.preserve_luminance,
            epsilon=request.config.epsilon
        )

        # Perform transfer
        result_b64, orch_result = orchestrator.transfer_from_base64(
            source_b64=request.source_image,
            target_b64=request.target_image,
            config=config,
            mask_b64=request.mask_image,
            enable_gpu=request.config.use_gpu,
            interface_type="API"
        )

        # Convert metrics
        metrics = PerformanceMetricsModel(
            execution_time_ms=orch_result.metrics.execution_time_ms,
            memory_used_mb=orch_result.metrics.memory_used_mb,
            throughput_images_per_sec=orch_result.metrics.throughput_images_per_sec
        )

        logger.info(f"Transfer complete: run_id={orch_result.run_id}, time={metrics.execution_time_ms:.2f}ms")

        return TransferResponse(
            result_image=result_b64,
            metrics=metrics,
            run_id=orch_result.run_id
        )

    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid request: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Processing error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process transfer: {str(e)}"
        )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """Custom exception handler for consistent error responses."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code
        }
    )


def create_app() -> FastAPI:
    """Factory function to create configured FastAPI app."""
    return app


# For uvicorn: uvicorn color_transfer_framework.interface_layer.api:app --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
