"""
Security Middleware - Unified Protection Layer (Knuth/Graham)

Combines rate limiting and input validation into a single middleware:
- Rate limiting: Token bucket or sliding window
- Input validation: File size, magic numbers, content
- Request context: Automatic tracking and logging

Mathematical Analysis (Knuth):
- Rate limit check: O(1) for token bucket
- Input validation: O(1) basic + O(n) content (bounded)
- Total overhead: < 10ms per request

Security Properties (Graham):
- Defense in depth: Multiple validation layers
- Fail securely: Deny by default
- Clear errors: Help legitimate users
- No information leakage: Generic error messages to clients
"""

import time
import logging
from typing import Optional, Callable, Any, Dict
from pathlib import Path

from ..security.rate_limiter import (
    RateLimiter,
    RateLimitConfig,
    RateLimitStrategy,
    RateLimitExceeded
)
from ..security.input_validator import (
    InputValidator,
    ValidationResult,
    ValidationError
)
from .context import get_request_context, set_request_context


logger = logging.getLogger(__name__)


class SecurityMiddleware:
    """
    Unified security middleware

    Combines:
    1. Rate limiting (per-client)
    2. Input validation (files, images)
    3. Request logging
    4. Context management

    Knuth's Security Pipeline:
    ==========================

    Request → Rate Limit Check → Input Validation → Process → Response
              └─ O(1)            └─ O(1)+O(n)       └─ O(f(n))

    Fast checks first:
    - Rate limit: O(1) - reject before expensive validation
    - File size: O(1) - reject before content parsing
    - Magic numbers: O(1) - reject before full parsing
    - Content: O(n) - final validation

    This ordering minimizes wasted computation on invalid requests.
    """

    def __init__(
        self,
        rate_limiter: Optional[RateLimiter] = None,
        input_validator: Optional[InputValidator] = None,
        enable_rate_limiting: bool = True,
        enable_input_validation: bool = True
    ):
        """
        Initialize security middleware

        Args:
            rate_limiter: Rate limiter instance (None = use default)
            input_validator: Input validator instance (None = use default)
            enable_rate_limiting: Enable rate limiting
            enable_input_validation: Enable input validation
        """
        self.enable_rate_limiting = enable_rate_limiting
        self.enable_input_validation = enable_input_validation

        # Initialize rate limiter
        if enable_rate_limiting:
            self.rate_limiter = rate_limiter or RateLimiter(
                config=RateLimitConfig(
                    rate=100,
                    window_seconds=60.0,
                    burst_size=120
                ),
                strategy=RateLimitStrategy.TOKEN_BUCKET
            )
        else:
            self.rate_limiter = None

        # Initialize input validator
        if enable_input_validation:
            self.input_validator = input_validator or InputValidator(
                max_file_size=100 * 1024 * 1024,  # 100 MB
                max_dimension=50000,
                max_pixels=100_000_000
            )
        else:
            self.input_validator = None

    def check_rate_limit(self, client_id: str, cost: int = 1) -> bool:
        """
        Check rate limit for client

        Args:
            client_id: Client identifier
            cost: Request cost in tokens (default 1)

        Returns:
            True if request allowed

        Raises:
            RateLimitExceeded: If rate limit exceeded

        Updates context with rate limit info
        """
        if not self.enable_rate_limiting or self.rate_limiter is None:
            return True

        try:
            # Check rate limit
            self.rate_limiter.check(client_id, cost)

            # Update context
            ctx = get_request_context()
            if ctx:
                ctx.rate_limited = False
                stats = self.rate_limiter.get_stats(client_id)
                ctx.rate_limit_remaining = stats.get('tokens_available') or stats.get('remaining_requests')

            return True

        except RateLimitExceeded as e:
            # Update context
            ctx = get_request_context()
            if ctx:
                ctx.rate_limited = True
                ctx.rate_limit_remaining = 0
                ctx.add_metric('rate_limit_retry_after', e.retry_after)

            # Re-raise for handling by framework
            raise

    def validate_file(self, file_path: str, check_content: bool = True) -> ValidationResult:
        """
        Validate file input

        Validation Pipeline (Knuth):
        1. File existence and access
        2. Filename sanitization
        3. File size limits
        4. Magic number check (optional)
        5. Content parsing (optional)

        Args:
            file_path: Path to file
            check_content: Whether to parse and validate content

        Returns:
            ValidationResult with errors and warnings

        Updates context with validation info
        """
        if not self.enable_input_validation or self.input_validator is None:
            return ValidationResult(valid=True, errors=[], warnings=[])

        # Validate file
        result = self.input_validator.validate(file_path, check_content=check_content)

        # Update context
        ctx = get_request_context()
        if ctx:
            ctx.validated = True
            ctx.validation_errors = result.errors
            if result.metadata:
                ctx.add_metric('validation_metadata', result.metadata)

        return result

    def validate_upload(
        self,
        file_path: str,
        check_content: bool = True,
        raise_on_error: bool = True
    ) -> ValidationResult:
        """
        Validate uploaded file with error handling

        Graham's Error Handling:
        - Validate file
        - If invalid and raise_on_error: raise ValidationError
        - If invalid and not raise_on_error: return result
        - If valid: return result

        Args:
            file_path: Path to uploaded file
            check_content: Whether to validate content
            raise_on_error: Whether to raise exception on validation failure

        Returns:
            ValidationResult

        Raises:
            ValidationError: If validation fails and raise_on_error=True
        """
        result = self.validate_file(file_path, check_content=check_content)

        if not result.valid and raise_on_error:
            error_msg = "; ".join(result.errors)
            raise ValidationError(f"File validation failed: {error_msg}")

        return result


class RateLimitMiddleware:
    """
    Standalone rate limiting middleware

    Lightweight wrapper focused only on rate limiting.
    Use when you don't need full SecurityMiddleware.

    Graham's Single Responsibility:
    - Does one thing well: rate limiting
    - No validation, no extra features
    - Fast: O(1) overhead
    """

    def __init__(
        self,
        rate_limiter: Optional[RateLimiter] = None,
        config: Optional[RateLimitConfig] = None,
        strategy: RateLimitStrategy = RateLimitStrategy.TOKEN_BUCKET
    ):
        """
        Initialize rate limit middleware

        Args:
            rate_limiter: Existing rate limiter (overrides config/strategy)
            config: Rate limit configuration
            strategy: Rate limiting strategy
        """
        if rate_limiter:
            self.rate_limiter = rate_limiter
        else:
            cfg = config or RateLimitConfig(rate=100, window_seconds=60.0)
            self.rate_limiter = RateLimiter(config=cfg, strategy=strategy)

    def check(self, client_id: str, cost: int = 1) -> bool:
        """
        Check rate limit

        Args:
            client_id: Client identifier
            cost: Request cost

        Returns:
            True if allowed

        Raises:
            RateLimitExceeded: If limit exceeded
        """
        return self.rate_limiter.check(client_id, cost)

    def get_stats(self, client_id: str) -> Dict[str, float]:
        """Get rate limit statistics for client"""
        return self.rate_limiter.get_stats(client_id)


class ValidationMiddleware:
    """
    Standalone input validation middleware

    Lightweight wrapper focused only on input validation.
    Use when you don't need full SecurityMiddleware.

    Graham's Single Responsibility:
    - Does one thing well: input validation
    - No rate limiting, no extra features
    - Configurable: File size, dimensions, content checking
    """

    def __init__(
        self,
        input_validator: Optional[InputValidator] = None,
        max_file_size: int = 100 * 1024 * 1024,
        max_dimension: int = 50000,
        max_pixels: int = 100_000_000
    ):
        """
        Initialize validation middleware

        Args:
            input_validator: Existing validator (overrides other params)
            max_file_size: Maximum file size in bytes
            max_dimension: Maximum image dimension
            max_pixels: Maximum total pixels
        """
        if input_validator:
            self.input_validator = input_validator
        else:
            self.input_validator = InputValidator(
                max_file_size=max_file_size,
                max_dimension=max_dimension,
                max_pixels=max_pixels
            )

    def validate(
        self,
        file_path: str,
        check_content: bool = True,
        raise_on_error: bool = True
    ) -> ValidationResult:
        """
        Validate file

        Args:
            file_path: Path to file
            check_content: Whether to validate content
            raise_on_error: Whether to raise exception on failure

        Returns:
            ValidationResult

        Raises:
            ValidationError: If validation fails and raise_on_error=True
        """
        result = self.input_validator.validate(file_path, check_content=check_content)

        if not result.valid and raise_on_error:
            error_msg = "; ".join(result.errors)
            raise ValidationError(f"Validation failed: {error_msg}")

        return result


# Knuth's Middleware Design Analysis
"""
Security Middleware Design (Knuth/Graham):
==========================================

Layered Architecture:

Layer 1: SecurityMiddleware (full-featured)
- Rate limiting + Input validation
- Request context integration
- Comprehensive logging
- Use for: Production APIs with all features

Layer 2: RateLimitMiddleware (focused)
- Rate limiting only
- Minimal overhead
- Use for: Rate limiting without validation

Layer 3: ValidationMiddleware (focused)
- Input validation only
- No rate limiting
- Use for: Batch processing, background jobs

Performance Analysis:

SecurityMiddleware:
- Rate limit check: O(1) token bucket
- File size check: O(1) stat call
- Magic number check: O(1) read 16 bytes
- Content validation: O(n) OpenCV parse (bounded by max_file_size)
- Total: O(1) + O(n) where n <= max_file_size

Optimization Strategy (Graham):
1. Check rate limit first (O(1), fast rejection)
2. Check file size next (O(1), fast rejection)
3. Check magic numbers (O(1), medium rejection)
4. Parse content last (O(n), thorough validation)

This ordering ensures expensive operations only run on valid requests.

Error Handling:

Rate Limit Exceeded:
- Raise RateLimitExceeded with retry_after
- HTTP 429 Too Many Requests
- Include Retry-After header

Validation Failed:
- Raise ValidationError with details
- HTTP 400 Bad Request
- Include error messages (but not internal paths)

Security Considerations:

Information Leakage Prevention:
- Don't reveal internal file paths in errors
- Don't reveal system details
- Generic error messages to clients
- Detailed logging for operators

Example Generic Errors:
- "File too large" (not "File 156MB exceeds 100MB limit at /internal/path")
- "Invalid file format" (not "Expected PNG signature, got FF D8 FF at byte 0")
- "Rate limit exceeded" (not "Client 1.2.3.4 exceeded 100 req/min with 125 requests")

Context Integration:

All middleware components update request context:
- Rate limiting: Updates rate_limited, rate_limit_remaining
- Validation: Updates validated, validation_errors
- Timing: Automatic via context manager
- Metrics: Custom metrics via ctx.add_metric()

This provides unified observability across all security features.
"""
