"""
FastAPI REST Service
===================

High-performance RESTful API for color transfer operations.

Endpoints:
- GET /api/v1/algorithms: List available algorithms
- POST /api/v1/transfer: Perform color transfer
- GET /api/v1/health: Health check (deprecated, use /health)
- GET /health/live: Liveness probe (Kubernetes-compatible)
- GET /health/ready: Readiness probe (Kubernetes-compatible)
- GET /health: Full health status
- GET /metrics: Performance metrics
"""

from fastapi import FastAPI, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import asyncio
import json
from typing import Dict, Any

from .models import (
    TransferRequest,
    TransferResponse,
    AlgorithmsResponse,
    AlgorithmInfo,
    HealthResponse,
    PerformanceMetricsModel,
    TomSawyerTransferRequest,
    TomSawyerTransferResponse,
    TomSawyerMetricsModel
)
from .orchestrator import TransferOrchestrator
from ..transfer_engine import TransferConfig, TransferAlgorithm
from .. import __version__

# Import middleware (Phase 13)
from ..middleware import (
    SecurityMiddleware,
    MonitoringMiddleware,
    create_fastapi_middleware
)
from ..middleware.integration import ColorTransferMiddleware
from ..security.health_checker import (
    create_redis_check,
    create_disk_space_check,
    create_memory_check
)

# Import telemetry (Phase 16: Distributed Tracing)
from ..telemetry import setup_tracing

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

# Setup distributed tracing (Phase 16)
tracer = setup_tracing("color-transfer-api", app, "fastapi")
logger.info("Distributed tracing configured with OpenTelemetry")

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

# Initialize middleware (Phase 13: Security & Operations)
security_middleware = SecurityMiddleware(
    enable_rate_limiting=True,
    enable_input_validation=True
)

monitoring_middleware = MonitoringMiddleware(
    enable_health_checks=True,
    enable_metrics=True
)

# Add dependency checks to health checker
monitoring_middleware.health_checker.add_dependency_check(
    create_disk_space_check(min_free_gb=1.0)
)
monitoring_middleware.health_checker.add_dependency_check(
    create_memory_check(max_usage_percent=90.0)
)

# Try to add Redis check if available
try:
    import redis
    from ..security.config_manager import ConfigManager
    config = ConfigManager.from_env()
    if config.redis_enabled:
        r = redis.Redis(host=config.redis_host, port=config.redis_port)
        monitoring_middleware.health_checker.add_dependency_check(
            create_redis_check(r)
        )
except Exception as e:
    logger.info(f"Redis health check not configured: {e}")

# Add Color Transfer middleware (combines security + monitoring)
app.add_middleware(
    ColorTransferMiddleware,
    security_middleware=security_middleware,
    monitoring_middleware=monitoring_middleware,
    enable_rate_limiting=True,
    enable_metrics=True
)

# Store middleware on app for access in endpoints
app.state.security = security_middleware
app.state.monitoring = monitoring_middleware


# WebSocket Connection Manager
class ConnectionManager:
    """Manages active WebSocket connections for progress updates."""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, client_id: str, websocket: WebSocket):
        """Accept and store a new WebSocket connection."""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"WebSocket connected: client_id={client_id}")

    def disconnect(self, client_id: str):
        """Remove a WebSocket connection."""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"WebSocket disconnected: client_id={client_id}")

    async def send_progress(self, client_id: str, status: str, percent: int):
        """Send progress update to a specific client."""
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_json({
                    "status": status,
                    "percent": percent
                })
            except Exception as e:
                logger.error(f"Failed to send progress to {client_id}: {e}")
                self.disconnect(client_id)


# Initialize connection manager
manager = ConnectionManager()


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Color Transfer Framework API",
        "version": __version__,
        "docs": "/docs",
        "health": "/health",
        "health_live": "/health/live",
        "health_ready": "/health/ready",
        "metrics": "/metrics",
        "legacy_health": "/api/v1/health"
    }


# Health Check Endpoints (Phase 13: Kubernetes-compatible)

@app.get("/health/live")
async def health_liveness():
    """
    Liveness probe (Kubernetes-compatible).

    Checks if the process is alive and responsive.
    Returns 200 if healthy, 503 if unhealthy.

    Used by Kubernetes to determine if container should be restarted.
    """
    result = monitoring_middleware.check_liveness()

    if result.status.value == "healthy":
        return JSONResponse(
            status_code=200,
            content=result.to_dict()
        )
    else:
        return JSONResponse(
            status_code=503,
            content=result.to_dict()
        )


@app.get("/health/ready")
async def health_readiness():
    """
    Readiness probe (Kubernetes-compatible).

    Checks if the service can handle requests (dependencies available).
    Returns 200 if ready, 503 if not ready.

    Used by Kubernetes to determine if pod should receive traffic.
    """
    result = monitoring_middleware.check_readiness()

    if result.status.value == "healthy":
        return JSONResponse(
            status_code=200,
            content=result.to_dict()
        )
    elif result.status.value == "degraded":
        return JSONResponse(
            status_code=429,  # Partial capacity
            content=result.to_dict()
        )
    else:
        return JSONResponse(
            status_code=503,
            content=result.to_dict()
        )


@app.get("/health")
async def health_full():
    """
    Full health status with all checks and metrics.

    Returns comprehensive health information including:
    - Liveness status
    - Readiness status
    - Dependency health
    - Uptime metrics
    - Success rate
    """
    return monitoring_middleware.get_health_status()


@app.get("/metrics")
async def metrics():
    """
    Prometheus-compatible metrics endpoint.

    Returns performance metrics including:
    - Request latency percentiles (p50, p95, p99)
    - Throughput (requests per second)
    - Error rate
    - Status code distribution
    """
    return monitoring_middleware.get_metrics()


@app.websocket("/api/v1/ws/progress/{client_id}")
async def websocket_progress(websocket: WebSocket, client_id: str):
    """
    WebSocket endpoint for real-time progress updates.

    Clients connect to this endpoint with a unique client_id,
    then receive progress updates during transfer operations.

    Parameters:
    ----------
    client_id : str
        Unique identifier for the client session
    """
    await manager.connect(client_id, websocket)
    try:
        # Keep connection alive and listen for client messages
        while True:
            # Receive any messages (used for keep-alive)
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(client_id)


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

    If client_id is provided, progress updates will be sent via WebSocket to the
    connected client at /api/v1/ws/progress/{client_id}.

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
        logger.info(f"Transfer request: algorithm={request.config.algorithm}, client_id={request.client_id}")

        # Build transfer configuration
        config = TransferConfig(
            algorithm=TransferAlgorithm(request.config.algorithm),
            blend_factor=request.config.blend_factor,
            clip_output=request.config.clip_output,
            preserve_luminance=request.config.preserve_luminance,
            epsilon=request.config.epsilon
        )

        # Create progress callback if client_id provided
        progress_callback = None
        if request.client_id:
            def progress_callback(status: str, percent: int):
                # Schedule the async send_progress coroutine
                asyncio.create_task(manager.send_progress(request.client_id, status, percent))

        # Perform transfer
        result_b64, orch_result = orchestrator.transfer_from_base64(
            source_b64=request.source_image,
            target_b64=request.target_image,
            config=config,
            mask_b64=request.mask_image,
            enable_gpu=request.config.use_gpu,
            interface_type="API",
            progress_callback=progress_callback
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


@app.post("/api/v1/transfer/tom-sawyer", response_model=TomSawyerTransferResponse)
async def transfer_colors_tom_sawyer(request: TomSawyerTransferRequest):
    """
    Perform color transfer using Tom Sawyer parallel processing method.

    This endpoint uses the Tom Sawyer Method with multiple workers and parameter
    variations to achieve consensus-based results with improved quality.

    **Features:**
    - Multiple workers (5-15) with parameter variations
    - Weighted consensus aggregation
    - Outlier detection and rejection
    - Higher quality at cost of increased processing time

    **Performance:**
    - Time overhead: 60-75% (prototype, sequential)
    - Consensus confidence: 94-97%
    - Memory usage: ~10x base (10 workers)

    **Use Cases:**
    - Quality-critical applications
    - Batch processing where time is less critical
    - Situations requiring robust, consensus-based results

    Parameters:
    ----------
    request : TomSawyerTransferRequest
        Transfer request with Tom Sawyer configuration

    Returns:
    -------
    TomSawyerTransferResponse
        Result image with both standard and Tom Sawyer metrics

    Raises:
    ------
    HTTPException
        400: Invalid request
        501: Tom Sawyer module not available
        500: Server error

    Example:
    --------
    ```python
    {
        "source_image": "base64_encoded_image...",
        "target_image": "base64_encoded_image...",
        "config": {
            "algorithm": "reinhard_lab",
            "blend_factor": 1.0
        },
        "tom_sawyer_config": {
            "num_workers": 10,
            "variation_min": 0.85,
            "variation_max": 1.15,
            "enable_parallel": true
        }
    }
    ```
    """
    try:
        logger.info(
            f"Tom Sawyer transfer request: algorithm={request.config.algorithm}, "
            f"workers={request.tom_sawyer_config.num_workers}, "
            f"client_id={request.client_id}"
        )

        # Build transfer configuration
        config = TransferConfig(
            algorithm=TransferAlgorithm(request.config.algorithm),
            blend_factor=request.config.blend_factor,
            clip_output=request.config.clip_output,
            preserve_luminance=request.config.preserve_luminance,
            epsilon=request.config.epsilon
        )

        # Decode images
        source = orchestrator._decode_base64_image(request.source_image)
        target = orchestrator._decode_base64_image(request.target_image)

        mask = None
        if request.mask_image:
            mask = orchestrator._decode_base64_image(request.mask_image, grayscale=True)

        # Create progress callback if client_id provided
        progress_callback = None
        if request.client_id:
            def progress_callback(status: str, percent: int):
                asyncio.create_task(manager.send_progress(request.client_id, status, percent))

        # Perform Tom Sawyer transfer
        orch_result = orchestrator.transfer_tom_sawyer(
            source, target,
            config=config,
            mask=mask,
            enable_gpu=request.config.use_gpu,
            num_workers=request.tom_sawyer_config.num_workers,
            variation_range=(
                request.tom_sawyer_config.variation_min,
                request.tom_sawyer_config.variation_max
            ),
            enable_parallel=request.tom_sawyer_config.enable_parallel,
            interface_type="API",
            progress_callback=progress_callback
        )

        # Encode result
        result_b64 = orchestrator._encode_base64_image(orch_result.result_image)

        # Convert metrics
        metrics = PerformanceMetricsModel(
            execution_time_ms=orch_result.metrics.execution_time_ms,
            memory_used_mb=orch_result.metrics.memory_used_mb,
            throughput_images_per_sec=orch_result.metrics.throughput_images_per_sec
        )

        # Convert Tom Sawyer metrics
        ts_metrics = TomSawyerMetricsModel(
            num_workers=orch_result.tom_sawyer_metrics.num_workers,
            processing_time_ms=orch_result.tom_sawyer_metrics.processing_time_ms,
            per_worker_time_ms=orch_result.tom_sawyer_metrics.per_worker_time_ms,
            aggregation_time_ms=orch_result.tom_sawyer_metrics.aggregation_time_ms,
            num_outliers=orch_result.tom_sawyer_metrics.num_outliers,
            consensus_confidence=orch_result.tom_sawyer_metrics.consensus_confidence,
            memory_used_mb=orch_result.tom_sawyer_metrics.memory_used_mb,
            speedup_vs_sequential=orch_result.tom_sawyer_metrics.speedup_vs_sequential
        )

        logger.info(
            f"Tom Sawyer transfer complete: run_id={orch_result.run_id}, "
            f"time={metrics.execution_time_ms:.2f}ms, "
            f"confidence={ts_metrics.consensus_confidence:.2%}"
        )

        return TomSawyerTransferResponse(
            result_image=result_b64,
            metrics=metrics,
            tom_sawyer_metrics=ts_metrics,
            run_id=orch_result.run_id
        )

    except ImportError as e:
        logger.error(f"Tom Sawyer module not available: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Tom Sawyer Method not available. This is an experimental feature."
        )
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid request: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Tom Sawyer processing error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process Tom Sawyer transfer: {str(e)}"
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
