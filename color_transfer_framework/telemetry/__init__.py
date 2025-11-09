"""
OpenTelemetry Configuration for Color Transfer Framework

Provides distributed tracing across all services using OpenTelemetry and Jaeger.

Knuth's Observability Philosophy:
"You can't improve what you don't measure. Tracing shows us the complete story
 of each request through the system."

Graham's Practical Tracing:
"Instrument once, visualize everywhere. Make tracing automatic and transparent."
"""

import os
import logging
from typing import Optional

from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor

logger = logging.getLogger(__name__)


def configure_tracing(
    service_name: str,
    jaeger_host: Optional[str] = None,
    jaeger_port: Optional[int] = None,
    enabled: Optional[bool] = None
) -> Optional[trace.Tracer]:
    """
    Configure OpenTelemetry distributed tracing.

    Args:
        service_name: Name of the service (e.g., "color-transfer-api")
        jaeger_host: Jaeger agent host (default: from JAEGER_HOST env or "localhost")
        jaeger_port: Jaeger agent port (default: from JAEGER_PORT env or 6831)
        enabled: Enable tracing (default: from ENABLE_TRACING env or True)

    Returns:
        Tracer instance if enabled, None otherwise

    Example:
        >>> tracer = configure_tracing("color-transfer-api")
        >>> with tracer.start_as_current_span("my_operation"):
        ...     # Your code here
        ...     pass
    """
    # Check if tracing is enabled
    if enabled is None:
        enabled = os.getenv("ENABLE_TRACING", "true").lower() == "true"

    if not enabled:
        logger.info("Distributed tracing is disabled")
        return None

    # Get Jaeger configuration
    if jaeger_host is None:
        jaeger_host = os.getenv("JAEGER_HOST", "localhost")

    if jaeger_port is None:
        jaeger_port = int(os.getenv("JAEGER_PORT", "6831"))

    try:
        # Create resource with service name
        resource = Resource(attributes={
            SERVICE_NAME: service_name,
            "service.version": "2.0.0",
            "deployment.environment": os.getenv("ENVIRONMENT", "production")
        })

        # Create Jaeger exporter
        jaeger_exporter = JaegerExporter(
            agent_host_name=jaeger_host,
            agent_port=jaeger_port,
        )

        # Create tracer provider
        provider = TracerProvider(resource=resource)

        # Add span processor
        processor = BatchSpanProcessor(jaeger_exporter)
        provider.add_span_processor(processor)

        # Set global tracer provider
        trace.set_tracer_provider(provider)

        logger.info(
            f"✅ Distributed tracing enabled for {service_name} "
            f"(Jaeger: {jaeger_host}:{jaeger_port})"
        )

        return trace.get_tracer(__name__)

    except Exception as e:
        logger.error(f"Failed to configure tracing: {e}")
        return None


def instrument_fastapi(app):
    """
    Instrument FastAPI application with OpenTelemetry.

    Args:
        app: FastAPI application instance

    Example:
        >>> from fastapi import FastAPI
        >>> app = FastAPI()
        >>> instrument_fastapi(app)
    """
    try:
        FastAPIInstrumentor.instrument_app(app)
        logger.info("✅ FastAPI instrumented with OpenTelemetry")
    except Exception as e:
        logger.error(f"Failed to instrument FastAPI: {e}")


def instrument_flask(app):
    """
    Instrument Flask application with OpenTelemetry.

    Args:
        app: Flask application instance

    Example:
        >>> from flask import Flask
        >>> app = Flask(__name__)
        >>> instrument_flask(app)
    """
    try:
        FlaskInstrumentor().instrument_app(app)
        logger.info("✅ Flask instrumented with OpenTelemetry")
    except Exception as e:
        logger.error(f"Failed to instrument Flask: {e}")


def instrument_requests():
    """
    Instrument HTTP requests library with OpenTelemetry.

    This will automatically trace all outgoing HTTP requests.

    Example:
        >>> instrument_requests()
        >>> import requests
        >>> requests.get("http://example.com")  # Automatically traced
    """
    try:
        RequestsInstrumentor().instrument()
        logger.info("✅ Requests library instrumented with OpenTelemetry")
    except Exception as e:
        logger.error(f"Failed to instrument requests: {e}")


def instrument_redis():
    """
    Instrument Redis client with OpenTelemetry.

    This will automatically trace all Redis operations.

    Example:
        >>> instrument_redis()
        >>> import redis
        >>> r = redis.Redis()
        >>> r.get("key")  # Automatically traced
    """
    try:
        RedisInstrumentor().instrument()
        logger.info("✅ Redis instrumented with OpenTelemetry")
    except Exception as e:
        logger.error(f"Failed to instrument Redis: {e}")


def instrument_all():
    """
    Instrument all common libraries with OpenTelemetry.

    This is a convenience function that instruments:
    - HTTP requests library
    - Redis client

    Example:
        >>> instrument_all()
    """
    instrument_requests()
    instrument_redis()


# Convenience function for quick setup
def setup_tracing(service_name: str, app=None, app_type: str = "fastapi"):
    """
    Quick setup for distributed tracing.

    Args:
        service_name: Name of the service
        app: Application instance (FastAPI or Flask)
        app_type: Type of application ("fastapi" or "flask")

    Returns:
        Tracer instance if enabled, None otherwise

    Example:
        >>> from fastapi import FastAPI
        >>> app = FastAPI()
        >>> tracer = setup_tracing("color-transfer-api", app, "fastapi")
    """
    # Configure tracing
    tracer = configure_tracing(service_name)

    if tracer is None:
        return None

    # Instrument application
    if app is not None:
        if app_type == "fastapi":
            instrument_fastapi(app)
        elif app_type == "flask":
            instrument_flask(app)

    # Instrument common libraries
    instrument_all()

    return tracer
