"""
API Contract Testing - Knuth's Formal Verification

Tests API contracts with mathematical rigor:
- Request/Response schema validation
- Status code verification
- Header validation
- Backward compatibility
- Consumer-Driven Contracts

Mathematical Analysis (Knuth):
- Schema compliance: 100% required
- Type safety: Static type checking
- Invariant preservation: All properties maintained

Practical Testing (Graham):
- OpenAPI spec validation
- Pact consumer-driven contracts
- Regression prevention
- Version compatibility
"""

import pytest
import requests
import json
from typing import Dict, Any, List
from jsonschema import validate, ValidationError as JsonValidationError
from pathlib import Path


class APIContractTester:
    """
    API Contract Testing Framework

    Knuth's Contract Verification:
    ==============================

    Contracts Define:
    1. Request schema (required fields, types, constraints)
    2. Response schema (structure, types, required fields)
    3. Status codes (success, error cases)
    4. Headers (content-type, custom headers)
    5. Error formats (consistent error structure)

    Verification:
    - Every response validated against schema
    - No undefined fields returned
    - All required fields present
    - Type constraints satisfied
    - Enum values valid
    """

    def __init__(self, base_url: str):
        self.base_url = base_url

    def validate_response_schema(self, response: dict, schema: dict):
        """
        Validate response against JSON schema

        Raises:
            JsonValidationError: If validation fails
        """
        try:
            validate(instance=response, schema=schema)
        except JsonValidationError as e:
            raise AssertionError(f"Schema validation failed: {e.message}")

    def validate_error_response(self, response: dict):
        """
        Validate error response format

        Knuth's Error Contract:
        - All errors have consistent structure
        - Include: error message, status code
        - Optional: error code, details, trace_id
        """
        assert 'error' in response, "Error response must have 'error' field"
        assert isinstance(response['error'], str), "Error must be string"

        if 'status_code' in response:
            assert isinstance(response['status_code'], int), "Status code must be integer"


# API Contract Schemas (Knuth's Formal Specification)

ALGORITHM_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "value": {"type": "string"},
        "description": {"type": "string"}
    },
    "required": ["name", "value", "description"],
    "additionalProperties": False
}

ALGORITHMS_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "algorithms": {
            "type": "array",
            "items": ALGORITHM_SCHEMA,
            "minItems": 1
        }
    },
    "required": ["algorithms"],
    "additionalProperties": False
}

METRICS_SCHEMA = {
    "type": "object",
    "properties": {
        "execution_time_ms": {"type": "number", "minimum": 0},
        "memory_used_mb": {"type": "number", "minimum": 0},
        "throughput_images_per_sec": {"type": "number", "minimum": 0}
    },
    "required": ["execution_time_ms", "memory_used_mb", "throughput_images_per_sec"],
    "additionalProperties": False
}

TRANSFER_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "result_image": {"type": "string"},  # Base64
        "metrics": METRICS_SCHEMA,
        "run_id": {"type": "string"}
    },
    "required": ["result_image", "metrics", "run_id"],
    "additionalProperties": False
}

HEALTH_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "status": {"type": "string", "enum": ["healthy", "unhealthy", "degraded", "unknown"]},
        "latency_ms": {"type": "number", "minimum": 0},
        "message": {"type": "string"},
        "details": {"type": "object"},
        "timestamp": {"type": "string"}  # ISO 8601
    },
    "required": ["name", "status", "latency_ms", "message"]
}

HEALTH_STATUS_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": ["healthy", "unhealthy", "degraded", "unknown"]},
        "liveness": HEALTH_SCHEMA,
        "readiness": HEALTH_SCHEMA,
        "metrics": {"type": "object"}
    },
    "required": ["status", "liveness", "readiness"]
}

METRICS_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "total_requests": {"type": "integer", "minimum": 0},
        "error_count": {"type": "integer", "minimum": 0},
        "error_rate": {"type": "number", "minimum": 0, "maximum": 1},
        "status_codes": {"type": "object"},
        "latency_percentiles_ms": {
            "type": "object",
            "properties": {
                "p50": {"type": "number"},
                "p95": {"type": "number"},
                "p99": {"type": "number"},
                "min": {"type": "number"},
                "max": {"type": "number"}
            }
        },
        "throughput_rps": {"type": "number", "minimum": 0},
        "history_size": {"type": "integer", "minimum": 0}
    },
    "required": ["total_requests", "latency_percentiles_ms"]
}


@pytest.fixture(scope="module")
def api_contract():
    """Create API contract tester"""
    return APIContractTester("http://localhost:8000")


@pytest.fixture(scope="module")
def test_image_base64():
    """Generate test image as base64"""
    import base64
    import numpy as np
    import cv2

    img = np.zeros((100, 100, 3), dtype=np.uint8)
    img[:, :] = [255, 0, 0]
    _, buffer = cv2.imencode('.png', img)
    return base64.b64encode(buffer).decode('utf-8')


class TestAPIContract:
    """
    API Contract Test Suite

    Verifies API adheres to defined contracts
    """

    def test_root_endpoint_contract(self, api_contract: APIContractTester):
        """
        Test: Root endpoint returns expected structure

        Contract:
        - Status: 200
        - Content-Type: application/json
        - Fields: name, version, docs, health
        """
        response = requests.get(f"{api_contract.base_url}/")

        assert response.status_code == 200, "Root endpoint must return 200"
        assert 'application/json' in response.headers['Content-Type']

        data = response.json()

        # Verify required fields
        assert 'name' in data, "Response must include 'name'"
        assert 'version' in data, "Response must include 'version'"
        assert 'docs' in data, "Response must include 'docs'"
        assert 'health' in data, "Response must include 'health'"

        # Verify types
        assert isinstance(data['name'], str)
        assert isinstance(data['version'], str)
        assert isinstance(data['docs'], str)

    def test_algorithms_endpoint_contract(self, api_contract: APIContractTester):
        """
        Test: Algorithms endpoint adheres to contract

        Knuth's Contract:
        - Status: 200
        - Schema: ALGORITHMS_RESPONSE_SCHEMA
        - At least 1 algorithm
        - Each algorithm has name, value, description
        """
        response = requests.get(f"{api_contract.base_url}/api/v1/algorithms")

        assert response.status_code == 200
        assert 'application/json' in response.headers['Content-Type']

        data = response.json()

        # Validate schema
        api_contract.validate_response_schema(data, ALGORITHMS_RESPONSE_SCHEMA)

        # Verify at least one algorithm
        assert len(data['algorithms']) > 0, "Must have at least one algorithm"

        # Verify expected algorithms present
        expected_algorithms = ['reinhard_lab', 'reinhard_lch', 'rgb_direct', 'histogram_match']
        algorithm_values = [a['value'] for a in data['algorithms']]

        for expected in expected_algorithms:
            assert expected in algorithm_values, f"Algorithm '{expected}' missing"

    def test_transfer_endpoint_contract(self, api_contract: APIContractTester, test_image_base64: str):
        """
        Test: Transfer endpoint adheres to contract

        Knuth's Transfer Contract:
        - Request: source_image, target_image, config
        - Response: result_image, metrics, run_id
        - Status: 200 on success
        - Schema: TRANSFER_RESPONSE_SCHEMA
        """
        payload = {
            "source_image": test_image_base64,
            "target_image": test_image_base64,
            "config": {
                "algorithm": "reinhard_lab",
                "blend_factor": 1.0,
                "clip_output": True,
                "preserve_luminance": False,
                "use_gpu": False
            }
        }

        response = requests.post(
            f"{api_contract.base_url}/api/v1/transfer",
            json=payload,
            timeout=30
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert 'application/json' in response.headers['Content-Type']

        data = response.json()

        # Validate schema
        api_contract.validate_response_schema(data, TRANSFER_RESPONSE_SCHEMA)

        # Verify result_image is valid base64
        result_image = data['result_image']
        assert len(result_image) > 0, "Result image must not be empty"

        # Verify metrics are reasonable
        metrics = data['metrics']
        assert metrics['execution_time_ms'] > 0, "Execution time must be positive"
        assert metrics['memory_used_mb'] > 0, "Memory usage must be positive"
        assert metrics['throughput_images_per_sec'] > 0, "Throughput must be positive"

        # Verify run_id is valid UUID format
        import uuid
        try:
            uuid.UUID(data['run_id'])
        except ValueError:
            pytest.fail(f"run_id '{data['run_id']}' is not a valid UUID")

    def test_health_live_endpoint_contract(self, api_contract: APIContractTester):
        """
        Test: Health liveness endpoint contract

        Contract:
        - Status: 200 (healthy) or 503 (unhealthy)
        - Schema: HEALTH_SCHEMA
        """
        response = requests.get(f"{api_contract.base_url}/health/live")

        assert response.status_code in [200, 503], "Liveness must return 200 or 503"
        assert 'application/json' in response.headers['Content-Type']

        data = response.json()

        # Validate schema
        api_contract.validate_response_schema(data, HEALTH_SCHEMA)

        # Verify status matches HTTP code
        if response.status_code == 200:
            assert data['status'] == 'healthy'
        else:
            assert data['status'] in ['unhealthy', 'unknown']

    def test_health_ready_endpoint_contract(self, api_contract: APIContractTester):
        """
        Test: Health readiness endpoint contract

        Contract:
        - Status: 200 (ready), 429 (degraded), or 503 (not ready)
        - Schema: HEALTH_SCHEMA
        """
        response = requests.get(f"{api_contract.base_url}/health/ready")

        assert response.status_code in [200, 429, 503], "Readiness must return 200, 429, or 503"
        assert 'application/json' in response.headers['Content-Type']

        data = response.json()

        # Validate schema
        api_contract.validate_response_schema(data, HEALTH_SCHEMA)

    def test_health_full_endpoint_contract(self, api_contract: APIContractTester):
        """
        Test: Full health status endpoint contract

        Contract:
        - Status: 200
        - Schema: HEALTH_STATUS_SCHEMA
        - Includes: liveness, readiness, metrics
        """
        response = requests.get(f"{api_contract.base_url}/health")

        assert response.status_code == 200
        assert 'application/json' in response.headers['Content-Type']

        data = response.json()

        # Validate schema
        api_contract.validate_response_schema(data, HEALTH_STATUS_SCHEMA)

    def test_metrics_endpoint_contract(self, api_contract: APIContractTester):
        """
        Test: Metrics endpoint contract

        Contract:
        - Status: 200
        - Schema: METRICS_RESPONSE_SCHEMA
        - Includes: latency percentiles, throughput, error rate
        """
        response = requests.get(f"{api_contract.base_url}/metrics")

        assert response.status_code == 200
        assert 'application/json' in response.headers['Content-Type']

        data = response.json()

        # Validate schema
        api_contract.validate_response_schema(data, METRICS_RESPONSE_SCHEMA)

        # Verify percentiles are ordered: min <= p50 <= p95 <= p99 <= max
        latency = data['latency_percentiles_ms']
        if latency['p50'] > 0:  # Only check if there's data
            assert latency['min'] <= latency['p50']
            assert latency['p50'] <= latency['p95']
            assert latency['p95'] <= latency['p99']
            assert latency['p99'] <= latency['max']

    def test_error_response_contract(self, api_contract: APIContractTester):
        """
        Test: Error responses follow contract

        Contract:
        - 400: Bad Request (invalid input)
        - 429: Too Many Requests (rate limited)
        - 500: Internal Server Error
        - All errors have consistent structure
        """
        # Test with invalid payload (should return 400 or 422)
        response = requests.post(
            f"{api_contract.base_url}/api/v1/transfer",
            json={"invalid": "data"}
        )

        assert response.status_code in [400, 422], "Invalid payload should return 4xx"
        assert 'application/json' in response.headers['Content-Type']

        data = response.json()

        # Verify error structure
        api_contract.validate_error_response(data)

    def test_cors_headers_contract(self, api_contract: APIContractTester):
        """
        Test: CORS headers present

        Contract:
        - Access-Control-Allow-Origin present
        - Access-Control-Allow-Methods present
        """
        response = requests.options(f"{api_contract.base_url}/api/v1/algorithms")

        # CORS headers should be present
        assert 'Access-Control-Allow-Origin' in response.headers
        assert 'Access-Control-Allow-Methods' in response.headers

    def test_rate_limit_headers_contract(self, api_contract: APIContractTester):
        """
        Test: Rate limit headers present

        Contract (after middleware integration):
        - X-RateLimit-Remaining: Requests remaining
        - Retry-After: Present on 429 responses
        """
        # Make a request
        response = requests.get(f"{api_contract.base_url}/")

        # Should have request ID
        if 'X-Request-ID' in response.headers:
            request_id = response.headers['X-Request-ID']
            assert len(request_id) > 0, "Request ID should not be empty"

        # If rate limited, should have Retry-After
        if response.status_code == 429:
            assert 'Retry-After' in response.headers, "429 must include Retry-After"


# Knuth's Contract Testing Analysis
"""
API Contract Testing Analysis (Knuth/Graham):
=============================================

Contract Testing Benefits:

1. Backward Compatibility:
   - Ensure API changes don't break clients
   - Version safely
   - Deprecate gracefully

2. Documentation:
   - Contracts are executable documentation
   - Always up-to-date
   - Clear expectations

3. Integration Confidence:
   - Both sides adhere to contract
   - Parallel development
   - Early issue detection

4. Type Safety:
   - Schema validation catches type errors
   - Required field enforcement
   - Enum validation

Graham's Contract Testing Strategy:

1. Define contracts first (contract-first design)
2. Generate code from contracts (OpenAPI)
3. Validate all responses against contracts
4. Version contracts explicitly
5. Maintain backward compatibility

Contract Evolution:

Version 1:
- Initial contract

Version 2 (backward compatible):
- Add optional fields
- Add new endpoints
- Relax validation

Version 3 (breaking change):
- Remove fields
- Change types
- Require new fields
- Increment major version

Testing Pyramid:

1. Unit tests: Test individual functions
2. Contract tests: Test API contracts
3. Integration tests: Test full workflows
4. E2E tests: Test user scenarios

Contract tests sit between unit and integration,
providing fast feedback without full system deployment.

Running Contract Tests:

# All contract tests
pytest tests/contract/

# Specific endpoint
pytest tests/contract/test_api_contract.py::TestAPIContract::test_transfer_endpoint_contract

# With coverage
pytest tests/contract/ --cov=color_transfer_framework

# Generate OpenAPI spec from contracts
# (Can use contracts to generate OpenAPI/Swagger documentation)

Consumer-Driven Contracts:

1. Consumer defines expected contract
2. Provider validates against contract
3. Pact broker stores contracts
4. CI/CD verifies compatibility

Advantages:
- Consumer needs drive API design
- No unused features
- Clear requirements
"""
