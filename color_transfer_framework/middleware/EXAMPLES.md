# Middleware Integration Examples

Comprehensive examples for using the Color Transfer Framework middleware layer.

## Table of Contents

1. [FastAPI Integration](#fastapi-integration)
2. [Flask Integration](#flask-integration)
3. [Generic Decorators](#generic-decorators)
4. [Custom Configuration](#custom-configuration)
5. [Health Checks](#health-checks)
6. [Metrics Collection](#metrics-collection)

---

## FastAPI Integration

### Basic Setup (Global Middleware)

```python
from fastapi import FastAPI
from color_transfer_framework.middleware import create_fastapi_middleware

app = FastAPI()

# Automatically applies rate limiting, validation, and monitoring to ALL endpoints
create_fastapi_middleware(
    app,
    enable_rate_limiting=True,
    enable_metrics=True
)

@app.get("/")
async def root():
    return {"message": "Hello World"}

# All endpoints now have:
# - Rate limiting
# - Request context
# - Metrics collection
# - Health checks available at /health/live, /health/ready
```

### Selective Rate Limiting (Decorator)

```python
from fastapi import FastAPI
from color_transfer_framework.middleware import fastapi_rate_limit

app = FastAPI()

@app.post("/cheap-operation")
async def cheap():
    # Uses default cost (1 token)
    return {"result": "ok"}

@app.post("/expensive-operation")
@fastapi_rate_limit(cost=10)  # Costs 10 tokens
async def expensive():
    # This operation costs 10x more
    return {"result": "ok"}

@app.post("/very-expensive-ml-inference")
@fastapi_rate_limit(cost=100)  # Costs 100 tokens
async def ml_inference():
    # ML operations cost much more
    return {"result": "ok"}
```

### File Upload Validation

```python
from fastapi import FastAPI, UploadFile, File
from color_transfer_framework.middleware import fastapi_validate_upload

app = FastAPI()

@app.post("/upload")
@fastapi_validate_upload(check_content=True)
async def upload_image(file: UploadFile = File(...)):
    # File is automatically validated for:
    # - Size limits
    # - Magic number verification
    # - Image content integrity
    # - Malicious filename patterns

    return {"filename": file.filename, "status": "validated"}
```

### Health Check Endpoints

```python
from fastapi import FastAPI
from color_transfer_framework.middleware import create_fastapi_middleware

app = FastAPI()
create_fastapi_middleware(app)

# Health endpoints automatically available:
# GET /health/live   - Liveness probe (Kubernetes)
# GET /health/ready  - Readiness probe (Kubernetes)
# GET /health        - Full health status
# GET /metrics       - Performance metrics

# Kubernetes deployment.yaml:
"""
livenessProbe:
  httpGet:
    path: /health/live
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /health/ready
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
"""
```

### Complete FastAPI Example

```python
from fastapi import FastAPI, UploadFile, File, HTTPException
from color_transfer_framework.middleware import (
    create_fastapi_middleware,
    fastapi_rate_limit,
    fastapi_validate_upload
)

app = FastAPI(title="My Color Transfer API")

# Global middleware
create_fastapi_middleware(
    app,
    enable_rate_limiting=True,
    enable_metrics=True
)

@app.get("/")
async def root():
    return {
        "name": "My API",
        "health": "/health",
        "metrics": "/metrics"
    }

@app.post("/transfer")
@fastapi_rate_limit(cost=50)  # Expensive operation
@fastapi_validate_upload(check_content=True)
async def transfer(
    source: UploadFile = File(...),
    target: UploadFile = File(...)
):
    # Both files validated, rate limited
    # Process color transfer...
    return {"status": "success"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

## Flask Integration

### Basic Setup (Global Middleware)

```python
from flask import Flask
from color_transfer_framework.middleware import create_flask_middleware

app = Flask(__name__)

# Automatically applies to ALL endpoints
security, monitoring = create_flask_middleware(
    app,
    enable_rate_limiting=True,
    enable_metrics=True
)

@app.route("/")
def root():
    return {"message": "Hello World"}

# All endpoints now have rate limiting and metrics
```

### Selective Rate Limiting (Decorator)

```python
from flask import Flask
from color_transfer_framework.middleware import flask_rate_limit

app = Flask(__name__)

@app.route("/cheap")
def cheap():
    return {"result": "ok"}

@app.route("/expensive", methods=["POST"])
@flask_rate_limit(cost=10)
def expensive():
    return {"result": "ok"}
```

### File Upload Validation

```python
from flask import Flask, request
from color_transfer_framework.middleware import flask_validate_upload

app = Flask(__name__)

@app.route("/upload", methods=["POST"])
@flask_validate_upload(form_field="image", check_content=True)
def upload():
    # File "image" is automatically validated
    file = request.files["image"]
    return {"filename": file.filename}
```

### Complete Flask Example

```python
from flask import Flask, request, jsonify
from color_transfer_framework.middleware import (
    create_flask_middleware,
    flask_rate_limit,
    flask_validate_upload
)

app = Flask(__name__)

# Global middleware
security, monitoring = create_flask_middleware(
    app,
    enable_rate_limiting=True,
    enable_metrics=True
)

@app.route("/")
def root():
    return jsonify({
        "name": "My API",
        "health": "/health",
        "metrics": "/metrics"
    })

@app.route("/transfer", methods=["POST"])
@flask_rate_limit(cost=50)
@flask_validate_upload(form_field="source", check_content=True)
def transfer():
    source = request.files["source"]
    # Process...
    return jsonify({"status": "success"})

# Health endpoints
@app.route("/health/live")
def health_live():
    result = monitoring.check_liveness()
    return jsonify(result.to_dict()), 200 if result.status.value == "healthy" else 503

@app.route("/health/ready")
def health_ready():
    result = monitoring.check_readiness()
    status_code = 200 if result.status.value == "healthy" else 503
    return jsonify(result.to_dict()), status_code

@app.route("/metrics")
def metrics():
    return jsonify(monitoring.get_metrics())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
```

---

## Generic Decorators

For non-web applications or custom frameworks:

### Rate Limiting

```python
from color_transfer_framework.middleware import with_rate_limit

def get_user_id():
    # Extract user ID from context
    return "user_123"

@with_rate_limit(client_id_func=get_user_id, cost=5)
def expensive_batch_job():
    # Rate limited by user ID
    # Costs 5 tokens
    process_data()

# Use it
expensive_batch_job()  # Rate limited
```

### Input Validation

```python
from color_transfer_framework.middleware import with_validation

@with_validation(file_path_arg="image_path", check_content=True)
def process_image(image_path: str):
    # image_path is validated before this runs
    # Size, magic numbers, content all checked
    do_processing(image_path)

# Use it
process_image(image_path="/path/to/image.jpg")  # Validated
```

### Metrics Collection

```python
from color_transfer_framework.middleware import with_metrics

@with_metrics(func_name="image_processing")
def process_image(path: str):
    # Automatically collects:
    # - Execution time
    # - Success/failure
    # - Exceptions
    return do_work(path)

# Use it
result = process_image("/path/to/image.jpg")

# Get metrics
from color_transfer_framework.middleware import MetricsMiddleware
metrics = MetricsMiddleware()
stats = metrics.get_stats()
print(f"p95 latency: {stats['latency_percentiles_ms']['p95']:.2f}ms")
```

### Manual Context Management

```python
from color_transfer_framework.middleware import RequestContextManager

def batch_processor(items):
    with RequestContextManager(
        request_id="batch-001",
        client_id="system",
        method="BATCH",
        path="/batch"
    ) as ctx:
        for item in items:
            process(item)

        # Add custom metrics
        ctx.add_metric("items_processed", len(items))
        ctx.add_metric("cache_hits", 42)

    # Context automatically cleaned up
    # Metrics recorded
```

---

## Custom Configuration

### From Environment Variables

```python
from color_transfer_framework.security import ConfigManager
from color_transfer_framework.middleware import (
    SecurityMiddleware,
    MonitoringMiddleware
)

# Load from .env file
config = ConfigManager.from_env()

# Create middleware with custom limits
security = SecurityMiddleware(
    enable_rate_limiting=config.rate_limit_enabled
)

# Configure rate limiter
from color_transfer_framework.security import RateLimiter, RateLimitConfig

rate_limiter = RateLimiter(
    config=RateLimitConfig(
        rate=config.rate_limit_requests,
        window_seconds=config.rate_limit_window_seconds,
        burst_size=config.rate_limit_requests + 20  # 20% burst
    )
)

security = SecurityMiddleware(
    rate_limiter=rate_limiter,
    enable_rate_limiting=True
)
```

### Example .env File

```bash
# .env
ENVIRONMENT=production

# API Configuration
API_PORT=8000
API_WORKERS=4

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=1000
RATE_LIMIT_WINDOW_SECONDS=60

# File Upload Limits
MAX_FILE_SIZE_MB=50
MAX_IMAGE_DIMENSION=10000

# Redis
REDIS_ENABLED=true
REDIS_HOST=localhost
REDIS_PORT=6379

# Logging
LOG_LEVEL=INFO
```

---

## Health Checks

### Adding Custom Dependency Checks

```python
from color_transfer_framework.middleware import MonitoringMiddleware
from color_transfer_framework.security.health_checker import (
    HealthCheck,
    HealthStatus,
    create_redis_check,
    create_disk_space_check,
    create_memory_check
)

monitoring = MonitoringMiddleware()

# Add standard checks
monitoring.health_checker.add_dependency_check(
    create_redis_check(redis_client)
)
monitoring.health_checker.add_dependency_check(
    create_disk_space_check(min_free_gb=5.0)
)
monitoring.health_checker.add_dependency_check(
    create_memory_check(max_usage_percent=85.0)
)

# Add custom check
def check_database():
    import time
    start = time.time()
    try:
        db.ping()
        latency_ms = (time.time() - start) * 1000
        return HealthCheck(
            name="database",
            status=HealthStatus.HEALTHY,
            latency_ms=latency_ms,
            message="Database connected"
        )
    except Exception as e:
        latency_ms = (time.time() - start) * 1000
        return HealthCheck(
            name="database",
            status=HealthStatus.UNHEALTHY,
            latency_ms=latency_ms,
            message=f"Database error: {e}"
        )

monitoring.health_checker.add_dependency_check(check_database)
```

### Kubernetes Deployment

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: color-transfer-api
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: api
        image: color-transfer:latest
        ports:
        - containerPort: 8000
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
          failureThreshold: 2
          successThreshold: 2
```

---

## Metrics Collection

### Accessing Metrics

```python
from color_transfer_framework.middleware import MonitoringMiddleware

monitoring = MonitoringMiddleware(enable_metrics=True)

# After some requests...
stats = monitoring.get_metrics()

print(f"Total requests: {stats['total_requests']}")
print(f"Error rate: {stats['error_rate']:.2%}")
print(f"Throughput: {stats['throughput_rps']:.2f} req/s")

# Latency percentiles
latency = stats['latency_percentiles_ms']
print(f"p50: {latency['p50']:.2f}ms")
print(f"p95: {latency['p95']:.2f}ms")
print(f"p99: {latency['p99']:.2f}ms")

# Status codes
codes = stats['status_codes']
print(f"2xx: {codes.get(200, 0)}")
print(f"4xx: {codes.get(400, 0) + codes.get(429, 0)}")
print(f"5xx: {codes.get(500, 0)}")
```

### Prometheus Export

```python
# endpoint for Prometheus scraping
@app.get("/metrics/prometheus")
async def prometheus_metrics():
    stats = monitoring_middleware.get_metrics()

    # Convert to Prometheus format
    lines = []

    # Request count
    lines.append(f"# HELP http_requests_total Total HTTP requests")
    lines.append(f"# TYPE http_requests_total counter")
    lines.append(f"http_requests_total {stats['total_requests']}")

    # Latency percentiles
    lines.append(f"# HELP http_request_duration_ms Request duration percentiles")
    lines.append(f"# TYPE http_request_duration_ms summary")
    for p, val in stats['latency_percentiles_ms'].items():
        lines.append(f'http_request_duration_ms{{quantile="{p}"}} {val}')

    # Throughput
    lines.append(f"# HELP http_requests_per_second Current throughput")
    lines.append(f"# TYPE http_requests_per_second gauge")
    lines.append(f"http_requests_per_second {stats['throughput_rps']}")

    # Error rate
    lines.append(f"# HELP http_error_rate Current error rate")
    lines.append(f"# TYPE http_error_rate gauge")
    lines.append(f"http_error_rate {stats['error_rate']}")

    return "\n".join(lines)
```

---

## Best Practices

### 1. Always Use Global Middleware

```python
# Good ✅
create_fastapi_middleware(app)

# Bad ❌ - Manually adding to each endpoint
@app.post("/endpoint1")
@fastapi_rate_limit()
def endpoint1(): pass

@app.post("/endpoint2")
@fastapi_rate_limit()  # Repeated everywhere
def endpoint2(): pass
```

### 2. Use Decorators for Exceptions

```python
# Global middleware for all endpoints (default cost=1)
create_fastapi_middleware(app)

# Decorator only for expensive endpoints
@app.post("/expensive")
@fastapi_rate_limit(cost=100)  # Much higher cost
async def expensive(): pass
```

### 3. Validate All User Uploads

```python
@app.post("/upload")
@fastapi_validate_upload(check_content=True)  # Always validate
async def upload(file: UploadFile):
    # File is safe to process
    pass
```

### 4. Monitor Health in Production

```python
# Add all relevant dependency checks
monitoring.health_checker.add_dependency_check(create_redis_check(redis))
monitoring.health_checker.add_dependency_check(create_disk_space_check(min_free_gb=10.0))
monitoring.health_checker.add_dependency_check(create_memory_check(max_usage_percent=80.0))

# Kubernetes will automatically restart if unhealthy
```

### 5. Export Metrics to Monitoring Systems

```python
# Prometheus, Grafana, Datadog, etc.
stats = monitoring.get_metrics()

# Send to your monitoring system
send_to_datadog(stats)
send_to_prometheus(stats)
send_to_grafana(stats)
```

---

## Troubleshooting

### Rate Limit Too Aggressive

```python
# Increase rate limit
from color_transfer_framework.security import RateLimitConfig

config = RateLimitConfig(
    rate=1000,  # 1000 requests
    window_seconds=60.0,  # per 60 seconds
    burst_size=1200  # Allow bursts up to 1200
)
```

### File Validation Too Strict

```python
from color_transfer_framework.security import InputValidator

validator = InputValidator(
    max_file_size=500 * 1024 * 1024,  # 500 MB instead of 100 MB
    max_dimension=100000,  # 100k pixels instead of 50k
    max_pixels=500_000_000  # 500 megapixels
)
```

### Health Checks Failing

```python
# Check individual dependencies
result = monitoring.check_readiness()
print(result.to_dict())

# Look at dependency details
for dep in result.details['dependencies']:
    print(f"{dep['name']}: {dep['status']} - {dep['message']}")
```

---

For more information, see the individual module documentation:
- `security/rate_limiter.py` - Rate limiting algorithms
- `security/input_validator.py` - Input validation
- `security/health_checker.py` - Health checks
- `middleware/integration.py` - Framework integration
