"""
Unified Middleware Layer - Architectural Integration (Knuth/Graham)

Automatically applies security, performance, and operational features across all interfaces:
- Rate limiting (token bucket, sliding window)
- Input validation (file size, magic numbers, content)
- Health monitoring (liveness, readiness probes)
- Metrics collection (latency, throughput, errors)
- Request context management

Mathematical Analysis (Knuth):
- Middleware overhead: O(1) per request
- Validation overhead: O(1) for basic checks, O(n) for content (bounded)
- Total latency impact: < 10ms for typical requests

Architectural Design (Graham):
- Framework-agnostic core
- Framework-specific adapters (FastAPI, Flask)
- Decorator pattern for easy application
- Context manager for resource safety
"""

from .security_middleware import (
    SecurityMiddleware,
    RateLimitMiddleware,
    ValidationMiddleware
)

from .monitoring_middleware import (
    MonitoringMiddleware,
    HealthMiddleware,
    MetricsMiddleware
)

from .integration import (
    # FastAPI integration
    create_fastapi_middleware,
    fastapi_rate_limit,
    fastapi_validate_upload,

    # Flask integration
    create_flask_middleware,
    flask_rate_limit,
    flask_validate_upload,

    # Generic decorator
    with_rate_limit,
    with_validation,
    with_metrics
)

from .context import (
    RequestContext,
    get_request_context,
    set_request_context,
    clear_request_context
)

__all__ = [
    # Security
    'SecurityMiddleware',
    'RateLimitMiddleware',
    'ValidationMiddleware',

    # Monitoring
    'MonitoringMiddleware',
    'HealthMiddleware',
    'MetricsMiddleware',

    # Integration
    'create_fastapi_middleware',
    'fastapi_rate_limit',
    'fastapi_validate_upload',
    'create_flask_middleware',
    'flask_rate_limit',
    'flask_validate_upload',
    'with_rate_limit',
    'with_validation',
    'with_metrics',

    # Context
    'RequestContext',
    'get_request_context',
    'set_request_context',
    'clear_request_context'
]
