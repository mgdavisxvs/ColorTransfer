"""
InterfaceLayer Package
=====================

Unified interface layer providing CLI, API, and WebUI access to the framework.

This package serves as the entry point for all user interactions with the
Color Transfer Framework, exposing functionality through multiple interfaces.

Available Interfaces:
- CLI: Command-line interface (Typer)
- API: RESTful service (FastAPI)
- WebUI: Web interface (Flask)

Components:
- orchestrator: Central coordination logic
- models: Pydantic data models
"""

from .orchestrator import TransferOrchestrator, OrchestrationResult
from .models import (
    TransferRequest,
    TransferResponse,
    TransferConfigModel,
    PerformanceMetricsModel,
    AlgorithmsResponse,
    HealthResponse
)

__all__ = [
    'TransferOrchestrator',
    'OrchestrationResult',
    'TransferRequest',
    'TransferResponse',
    'TransferConfigModel',
    'PerformanceMetricsModel',
    'AlgorithmsResponse',
    'HealthResponse',
]
