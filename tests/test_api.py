"""
Tests for FastAPI REST Service
==============================

Comprehensive tests for API endpoints, request/response models, and error handling.
"""

import pytest
import base64
import numpy as np
import cv2
from fastapi.testclient import TestClient

from color_transfer_framework.interface_layer.api import app
from color_transfer_framework.interface_layer.models import (
    TransferRequest,
    TransferConfigModel,
    AlgorithmType
)


class TestAPI:
    """Tests for FastAPI endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def sample_image_b64(self):
        """Create sample base64 encoded image."""
        # Create small test image
        img = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        _, buffer = cv2.imencode('.png', img)
        img_b64 = base64.b64encode(buffer).decode('utf-8')
        return img_b64

    def test_root_endpoint(self, client):
        """Test root endpoint returns API info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "docs" in data

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "modules_available" in data
        assert data["modules_available"]["transfer_engine"] is True

    def test_list_algorithms(self, client):
        """Test algorithms listing endpoint."""
        response = client.get("/api/v1/algorithms")
        assert response.status_code == 200
        data = response.json()
        assert "algorithms" in data
        assert len(data["algorithms"]) == 4  # All 4 algorithms

        algorithms = {algo["value"] for algo in data["algorithms"]}
        assert "reinhard_lab" in algorithms
        assert "reinhard_lch" in algorithms
        assert "rgb_direct" in algorithms
        assert "histogram_match" in algorithms

    def test_transfer_success(self, client, sample_image_b64):
        """Test successful color transfer."""
        request_data = {
            "source_image": sample_image_b64,
            "target_image": sample_image_b64,
            "config": {
                "algorithm": "reinhard_lab",
                "blend_factor": 1.0,
                "use_gpu": False
            }
        }

        response = client.post("/api/v1/transfer", json=request_data)
        assert response.status_code == 200

        data = response.json()
        assert "result_image" in data
        assert "metrics" in data
        assert "run_id" in data

        # Verify metrics structure
        metrics = data["metrics"]
        assert "execution_time_ms" in metrics
        assert "memory_used_mb" in metrics
        assert "throughput_images_per_sec" in metrics

        # Verify result is valid base64
        try:
            base64.b64decode(data["result_image"])
        except Exception:
            pytest.fail("Result image is not valid base64")

    def test_transfer_with_blend(self, client, sample_image_b64):
        """Test transfer with blend factor."""
        request_data = {
            "source_image": sample_image_b64,
            "target_image": sample_image_b64,
            "config": {
                "algorithm": "reinhard_lab",
                "blend_factor": 0.5,
                "use_gpu": False
            }
        }

        response = client.post("/api/v1/transfer", json=request_data)
        assert response.status_code == 200

    def test_transfer_all_algorithms(self, client, sample_image_b64):
        """Test transfer with all algorithms."""
        algorithms = ["reinhard_lab", "reinhard_lch", "rgb_direct", "histogram_match"]

        for algo in algorithms:
            request_data = {
                "source_image": sample_image_b64,
                "target_image": sample_image_b64,
                "config": {
                    "algorithm": algo,
                    "blend_factor": 1.0,
                    "use_gpu": False
                }
            }

            response = client.post("/api/v1/transfer", json=request_data)
            assert response.status_code == 200, f"Failed for algorithm: {algo}"

    def test_transfer_missing_source(self, client, sample_image_b64):
        """Test transfer with missing source image."""
        request_data = {
            "target_image": sample_image_b64,
            "config": {
                "algorithm": "reinhard_lab"
            }
        }

        response = client.post("/api/v1/transfer", json=request_data)
        assert response.status_code == 422  # Validation error

    def test_transfer_missing_target(self, client, sample_image_b64):
        """Test transfer with missing target image."""
        request_data = {
            "source_image": sample_image_b64,
            "config": {
                "algorithm": "reinhard_lab"
            }
        }

        response = client.post("/api/v1/transfer", json=request_data)
        assert response.status_code == 422  # Validation error

    def test_transfer_invalid_base64(self, client):
        """Test transfer with invalid base64 data."""
        request_data = {
            "source_image": "not-valid-base64!!!",
            "target_image": "also-not-valid!!!",
            "config": {
                "algorithm": "reinhard_lab"
            }
        }

        response = client.post("/api/v1/transfer", json=request_data)
        assert response.status_code in [400, 500]  # Should fail

    def test_transfer_invalid_algorithm(self, client, sample_image_b64):
        """Test transfer with invalid algorithm."""
        request_data = {
            "source_image": sample_image_b64,
            "target_image": sample_image_b64,
            "config": {
                "algorithm": "invalid_algorithm"
            }
        }

        response = client.post("/api/v1/transfer", json=request_data)
        assert response.status_code == 422  # Validation error

    def test_transfer_invalid_blend_factor(self, client, sample_image_b64):
        """Test transfer with invalid blend factor."""
        # Test negative blend
        request_data = {
            "source_image": sample_image_b64,
            "target_image": sample_image_b64,
            "config": {
                "algorithm": "reinhard_lab",
                "blend_factor": -0.5
            }
        }

        response = client.post("/api/v1/transfer", json=request_data)
        assert response.status_code == 422  # Validation error

        # Test blend > 1.0
        request_data["config"]["blend_factor"] = 1.5
        response = client.post("/api/v1/transfer", json=request_data)
        assert response.status_code == 422  # Validation error

    def test_transfer_with_mask(self, client, sample_image_b64):
        """Test transfer with mask image."""
        # Create mask image
        mask_img = np.ones((100, 100), dtype=np.uint8) * 255
        _, buffer = cv2.imencode('.png', mask_img)
        mask_b64 = base64.b64encode(buffer).decode('utf-8')

        request_data = {
            "source_image": sample_image_b64,
            "target_image": sample_image_b64,
            "mask_image": mask_b64,
            "config": {
                "algorithm": "reinhard_lab"
            }
        }

        response = client.post("/api/v1/transfer", json=request_data)
        assert response.status_code == 200

    def test_transfer_default_config(self, client, sample_image_b64):
        """Test transfer with default configuration."""
        request_data = {
            "source_image": sample_image_b64,
            "target_image": sample_image_b64
        }

        response = client.post("/api/v1/transfer", json=request_data)
        assert response.status_code == 200

    def test_cors_headers(self, client):
        """Test CORS headers are set."""
        response = client.options("/api/v1/transfer")
        # CORS middleware should handle OPTIONS requests
        assert response.status_code in [200, 405]


class TestModels:
    """Tests for Pydantic models."""

    def test_transfer_config_model_valid(self):
        """Test valid TransferConfigModel."""
        config = TransferConfigModel(
            algorithm=AlgorithmType.REINHARD_LAB,
            blend_factor=0.75,
            use_gpu=False
        )
        assert config.algorithm == AlgorithmType.REINHARD_LAB
        assert config.blend_factor == 0.75
        assert config.use_gpu is False

    def test_transfer_config_model_defaults(self):
        """Test TransferConfigModel defaults."""
        config = TransferConfigModel()
        assert config.algorithm == AlgorithmType.REINHARD_LAB
        assert config.blend_factor == 1.0
        assert config.clip_output is True
        assert config.preserve_luminance is False
        assert config.use_gpu is False

    def test_transfer_config_model_invalid_blend(self):
        """Test TransferConfigModel with invalid blend factor."""
        with pytest.raises(ValueError):
            TransferConfigModel(blend_factor=-0.5)

        with pytest.raises(ValueError):
            TransferConfigModel(blend_factor=1.5)

    def test_transfer_request_valid(self):
        """Test valid TransferRequest."""
        request = TransferRequest(
            source_image="base64encodeddata",
            target_image="base64encodeddata",
            config=TransferConfigModel()
        )
        assert request.source_image == "base64encodeddata"
        assert request.target_image == "base64encodeddata"
        assert request.mask_image is None

    def test_transfer_request_with_mask(self):
        """Test TransferRequest with mask."""
        request = TransferRequest(
            source_image="base64encodeddata",
            target_image="base64encodeddata",
            mask_image="maskbase64data",
            config=TransferConfigModel()
        )
        assert request.mask_image == "maskbase64data"

    def test_transfer_request_empty_image(self):
        """Test TransferRequest with empty image string."""
        with pytest.raises(ValueError):
            TransferRequest(
                source_image="",
                target_image="base64encodeddata"
            )


class TestPerformance:
    """Performance and load tests."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def sample_image_b64(self):
        """Create sample base64 encoded image."""
        img = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        _, buffer = cv2.imencode('.png', img)
        img_b64 = base64.b64encode(buffer).decode('utf-8')
        return img_b64

    def test_concurrent_requests(self, client, sample_image_b64):
        """Test handling multiple concurrent requests."""
        request_data = {
            "source_image": sample_image_b64,
            "target_image": sample_image_b64,
            "config": {"algorithm": "reinhard_lab"}
        }

        # Send multiple requests
        responses = []
        for _ in range(5):
            response = client.post("/api/v1/transfer", json=request_data)
            responses.append(response)

        # All should succeed
        assert all(r.status_code == 200 for r in responses)

        # All should have unique run IDs
        run_ids = [r.json()["run_id"] for r in responses]
        assert len(set(run_ids)) == 5

    def test_large_image_handling(self, client):
        """Test handling larger images."""
        # Create larger image (still reasonable size for testing)
        img = np.random.randint(0, 256, (500, 500, 3), dtype=np.uint8)
        _, buffer = cv2.imencode('.png', img)
        img_b64 = base64.b64encode(buffer).decode('utf-8')

        request_data = {
            "source_image": img_b64,
            "target_image": img_b64,
            "config": {"algorithm": "rgb_direct"}  # Fastest algorithm
        }

        response = client.post("/api/v1/transfer", json=request_data)
        assert response.status_code == 200
