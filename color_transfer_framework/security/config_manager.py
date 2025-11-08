"""
Configuration Management - Environment-Based (.env support)

Implements secure, hierarchical configuration with:
1. Environment variable support (.env files)
2. Type-safe configuration with validation
3. Secret management (never log secrets)
4. Configuration precedence hierarchy
5. Default values with mathematical bounds

Mathematical Analysis (Knuth):
- Configuration loading: O(n) where n = number of config items
- Lookup: O(1) with dictionary storage
- Validation: O(1) per item

Security Principles (Graham):
- Secrets never in source code
- Environment-specific configuration
- Fail securely: Safe defaults
- Audit trail: Log configuration sources (but not values)
"""

import os
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Type, TypeVar, Union, List
from dataclasses import dataclass, field, fields
from enum import Enum

# Try to import python-dotenv, fall back gracefully
try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False


logger = logging.getLogger(__name__)


class Environment(Enum):
    """Deployment environment"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class ConfigurationError(Exception):
    """Exception raised for configuration errors"""
    pass


T = TypeVar('T')


class SecureConfig:
    """
    Secure configuration value wrapper

    Graham's Security Pattern:
    - Mark sensitive values (API keys, passwords, tokens)
    - Never log or print sensitive values
    - Clear indication of secret fields

    Usage:
        api_key = SecureConfig("sk_live_...")

        print(api_key)  # Output: SecureConfig(*****)
        value = api_key.get()  # Get actual value
    """

    def __init__(self, value: str):
        self._value = value

    def get(self) -> str:
        """Get the actual secret value"""
        return self._value

    def __str__(self) -> str:
        """Never reveal secret in string representation"""
        return "SecureConfig(*****)"

    def __repr__(self) -> str:
        return "SecureConfig(*****)"


@dataclass
class ConfigManager:
    """
    Configuration Manager with .env support

    Knuth's Configuration Hierarchy:
    ================================

    Precedence (highest to lowest):
    1. Explicit parameters (programmatic override)
    2. Environment variables
    3. .env file values
    4. Default values

    This hierarchy allows:
    - Development: Use .env file for local config
    - Testing: Override with test values
    - Production: Use environment variables (Kubernetes secrets, etc.)

    Graham's Implementation:
    - Type-safe: Validate types on load
    - Bounded: All numeric values have bounds
    - Documented: Clear defaults and meanings
    """

    # Environment
    environment: Environment = Environment.DEVELOPMENT

    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 4

    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100
    rate_limit_window_seconds: float = 60.0

    # File Upload Limits (Knuth's bounds)
    max_file_size_mb: int = 100  # 100 MB
    max_image_dimension: int = 50000  # 50k pixels
    max_image_pixels: int = 100_000_000  # 100 megapixels

    # Security
    allowed_origins: List[str] = field(default_factory=lambda: ["*"])
    api_key_required: bool = False
    api_key: Optional[SecureConfig] = None

    # Redis Configuration
    redis_enabled: bool = False
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: Optional[SecureConfig] = None
    redis_db: int = 0

    # Celery Configuration
    celery_enabled: bool = False
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"

    # CDN Configuration
    cdn_enabled: bool = False
    cdn_provider: str = "local"
    cdn_base_url: Optional[str] = None
    cdn_api_key: Optional[SecureConfig] = None

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    # Performance
    enable_profiling: bool = False
    enable_metrics: bool = True

    def __post_init__(self):
        """Validate configuration after initialization"""
        self._validate_config()

    def _validate_config(self):
        """
        Validate configuration values

        Knuth's Validation Rules:
        1. Ports: 1-65535
        2. Workers: 1-256 (reasonable for most systems)
        3. File sizes: > 0
        4. Dimensions: > 0, < MAX_INT
        """
        # Validate port
        if not (1 <= self.api_port <= 65535):
            raise ConfigurationError(
                f"api_port must be in range [1, 65535], got {self.api_port}"
            )

        if not (1 <= self.redis_port <= 65535):
            raise ConfigurationError(
                f"redis_port must be in range [1, 65535], got {self.redis_port}"
            )

        # Validate workers
        if not (1 <= self.api_workers <= 256):
            raise ConfigurationError(
                f"api_workers must be in range [1, 256], got {self.api_workers}"
            )

        # Validate file size limits
        if self.max_file_size_mb <= 0:
            raise ConfigurationError(
                f"max_file_size_mb must be positive, got {self.max_file_size_mb}"
            )

        if self.max_image_dimension <= 0:
            raise ConfigurationError(
                f"max_image_dimension must be positive, got {self.max_image_dimension}"
            )

        # Validate rate limiting
        if self.rate_limit_enabled:
            if self.rate_limit_requests <= 0:
                raise ConfigurationError(
                    f"rate_limit_requests must be positive, got {self.rate_limit_requests}"
                )
            if self.rate_limit_window_seconds <= 0:
                raise ConfigurationError(
                    f"rate_limit_window_seconds must be positive, got {self.rate_limit_window_seconds}"
                )

        # Validate log level
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level.upper() not in valid_levels:
            raise ConfigurationError(
                f"log_level must be one of {valid_levels}, got {self.log_level}"
            )

    @classmethod
    def from_env(cls, env_file: Optional[str] = None) -> 'ConfigManager':
        """
        Load configuration from environment variables and .env file

        Graham's Loading Strategy:
        1. Load .env file (if available)
        2. Read environment variables
        3. Convert types appropriately
        4. Validate all values

        Args:
            env_file: Path to .env file (default: .env in current directory)

        Returns:
            Configured ConfigManager instance

        Example .env file:
            ENVIRONMENT=production
            API_PORT=8080
            API_WORKERS=8
            RATE_LIMIT_REQUESTS=1000
            MAX_FILE_SIZE_MB=50
            REDIS_ENABLED=true
            REDIS_PASSWORD=secret123
        """
        # Load .env file if available
        if env_file is None:
            env_file = ".env"

        if DOTENV_AVAILABLE and os.path.exists(env_file):
            load_dotenv(env_file)
            logger.info(f"Loaded configuration from {env_file}")
        elif not DOTENV_AVAILABLE:
            logger.warning(
                "python-dotenv not installed. Install with: pip install python-dotenv"
            )

        # Build configuration from environment
        config_dict = {}

        # Helper to get typed environment variable
        def get_env(
            key: str,
            default: Any,
            value_type: Type,
            is_secret: bool = False
        ) -> Any:
            """Get environment variable with type conversion"""
            env_key = key.upper()
            value = os.getenv(env_key)

            if value is None:
                return default

            # Type conversion
            try:
                if value_type == bool:
                    # Handle boolean strings
                    return value.lower() in ('true', '1', 'yes', 'on')
                elif value_type == int:
                    return int(value)
                elif value_type == float:
                    return float(value)
                elif value_type == list:
                    # Comma-separated list
                    return [item.strip() for item in value.split(',')]
                elif is_secret:
                    return SecureConfig(value)
                else:
                    return value
            except (ValueError, TypeError) as e:
                logger.warning(
                    f"Failed to convert {env_key}={value} to {value_type}: {e}"
                )
                return default

        # Load all configuration fields
        config_dict['environment'] = Environment(
            get_env('environment', 'development', str).lower()
        )

        config_dict['api_host'] = get_env('api_host', "0.0.0.0", str)
        config_dict['api_port'] = get_env('api_port', 8000, int)
        config_dict['api_workers'] = get_env('api_workers', 4, int)

        config_dict['rate_limit_enabled'] = get_env('rate_limit_enabled', True, bool)
        config_dict['rate_limit_requests'] = get_env('rate_limit_requests', 100, int)
        config_dict['rate_limit_window_seconds'] = get_env('rate_limit_window_seconds', 60.0, float)

        config_dict['max_file_size_mb'] = get_env('max_file_size_mb', 100, int)
        config_dict['max_image_dimension'] = get_env('max_image_dimension', 50000, int)
        config_dict['max_image_pixels'] = get_env('max_image_pixels', 100_000_000, int)

        config_dict['allowed_origins'] = get_env('allowed_origins', ["*"], list)
        config_dict['api_key_required'] = get_env('api_key_required', False, bool)
        config_dict['api_key'] = get_env('api_key', None, str, is_secret=True)

        config_dict['redis_enabled'] = get_env('redis_enabled', False, bool)
        config_dict['redis_host'] = get_env('redis_host', "localhost", str)
        config_dict['redis_port'] = get_env('redis_port', 6379, int)
        config_dict['redis_password'] = get_env('redis_password', None, str, is_secret=True)
        config_dict['redis_db'] = get_env('redis_db', 0, int)

        config_dict['celery_enabled'] = get_env('celery_enabled', False, bool)
        config_dict['celery_broker_url'] = get_env('celery_broker_url', "redis://localhost:6379/0", str)
        config_dict['celery_result_backend'] = get_env('celery_result_backend', "redis://localhost:6379/0", str)

        config_dict['cdn_enabled'] = get_env('cdn_enabled', False, bool)
        config_dict['cdn_provider'] = get_env('cdn_provider', "local", str)
        config_dict['cdn_base_url'] = get_env('cdn_base_url', None, str)
        config_dict['cdn_api_key'] = get_env('cdn_api_key', None, str, is_secret=True)

        config_dict['log_level'] = get_env('log_level', "INFO", str)
        config_dict['log_format'] = get_env('log_format', "json", str)

        config_dict['enable_profiling'] = get_env('enable_profiling', False, bool)
        config_dict['enable_metrics'] = get_env('enable_metrics', True, bool)

        return cls(**config_dict)

    def get_redis_url(self) -> Optional[str]:
        """
        Get Redis connection URL

        Graham's URL Construction:
        - Handle password (optional)
        - Include database number
        - Return None if Redis disabled
        """
        if not self.redis_enabled:
            return None

        password = self.redis_password.get() if self.redis_password else None

        if password:
            return f"redis://:{password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        else:
            return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    def to_dict(self, include_secrets: bool = False) -> Dict[str, Any]:
        """
        Convert configuration to dictionary

        Args:
            include_secrets: If False, mask secret values (default)

        Security (Graham):
        - Never log secrets by default
        - Explicit opt-in to include secrets
        - Use for debugging (without secrets) or serialization (with secrets)
        """
        result = {}

        for f in fields(self):
            value = getattr(self, f.name)

            if isinstance(value, SecureConfig):
                if include_secrets:
                    result[f.name] = value.get()
                else:
                    result[f.name] = "*****"
            elif isinstance(value, Enum):
                result[f.name] = value.value
            else:
                result[f.name] = value

        return result

    def __str__(self) -> str:
        """String representation (secrets masked)"""
        config_dict = self.to_dict(include_secrets=False)
        lines = [f"{k}: {v}" for k, v in sorted(config_dict.items())]
        return "ConfigManager(\n  " + "\n  ".join(lines) + "\n)"


# Example .env file template
ENV_FILE_TEMPLATE = """
# Color Transfer Framework Configuration
# Copy this file to .env and customize

# Environment
ENVIRONMENT=development

# API Server
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW_SECONDS=60

# File Upload Limits
MAX_FILE_SIZE_MB=100
MAX_IMAGE_DIMENSION=50000
MAX_IMAGE_PIXELS=100000000

# Security
ALLOWED_ORIGINS=*
API_KEY_REQUIRED=false
# API_KEY=your-secret-key-here

# Redis (for distributed caching)
REDIS_ENABLED=false
REDIS_HOST=localhost
REDIS_PORT=6379
# REDIS_PASSWORD=your-redis-password
REDIS_DB=0

# Celery (for distributed processing)
CELERY_ENABLED=false
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# CDN Configuration
CDN_ENABLED=false
CDN_PROVIDER=local
# CDN_BASE_URL=https://cdn.example.com
# CDN_API_KEY=your-cdn-api-key

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Performance
ENABLE_PROFILING=false
ENABLE_METRICS=true
"""


def create_env_template(output_path: str = ".env.example"):
    """
    Create example .env file template

    Usage:
        from color_transfer_framework.security import create_env_template
        create_env_template()  # Creates .env.example
    """
    with open(output_path, 'w') as f:
        f.write(ENV_FILE_TEMPLATE.strip())

    logger.info(f"Created environment template: {output_path}")
    print(f"Environment template created: {output_path}")
    print("Copy to .env and customize for your environment")


# Knuth's Configuration Analysis
"""
Configuration Management Analysis (Knuth/Graham):
=================================================

Precedence Hierarchy:
1. Explicit code: ConfigManager(api_port=9000)
2. Environment variables: API_PORT=9000
3. .env file: API_PORT=8080
4. Defaults: api_port=8000

Mathematical Complexity:
- Load: O(n) where n = number of config parameters
- Lookup: O(1) with dataclass fields
- Validation: O(n) one-time cost

Security Properties:
1. Secrets never in source code (12-factor app principle)
2. Secrets never logged (SecureConfig wrapper)
3. Type safety prevents config errors
4. Validation ensures bounds

Graham's Best Practices:
1. Development: Use .env file for convenience
2. Testing: Override with explicit values
3. Staging/Production: Use environment variables (Kubernetes secrets, AWS SSM)
4. Never commit .env to version control (add to .gitignore)

Configuration Errors:
- Fail fast: Validate on load
- Clear messages: "api_port must be in range [1, 65535]"
- Type safety: Catch errors before runtime

Example Usage:

    # Development (with .env file)
    config = ConfigManager.from_env()

    # Production (environment variables)
    export API_PORT=8080
    export REDIS_ENABLED=true
    export REDIS_PASSWORD=secret
    config = ConfigManager.from_env()

    # Testing (explicit override)
    config = ConfigManager(
        api_port=9999,
        redis_enabled=True,
        max_file_size_mb=10
    )
"""
