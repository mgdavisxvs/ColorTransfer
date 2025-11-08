"""
Flask Web Interface
==================

User-friendly web interface for color transfer operations.

Routes:
- GET /: Main page with upload form
- POST /transfer: Process transfer request
- GET /download/<filename>: Download result
- GET /health/live: Liveness probe (Kubernetes-compatible)
- GET /health/ready: Readiness probe (Kubernetes-compatible)
- GET /health: Full health status
- GET /metrics: Performance metrics
"""

from flask import Flask, render_template_string, request, send_file, jsonify, session
from werkzeug.utils import secure_filename
import os
import tempfile
import uuid
from pathlib import Path
import cv2
import numpy as np
import logging

from .orchestrator import TransferOrchestrator
from ..transfer_engine import TransferConfig, TransferAlgorithm
from .. import __version__

# Import middleware (Phase 13)
from ..middleware import create_flask_middleware
from ..security.health_checker import (
    create_disk_space_check,
    create_memory_check
)

logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload
app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()

# Initialize orchestrator
orchestrator = TransferOrchestrator()

# Initialize middleware (Phase 13: Security & Operations)
security_middleware, monitoring_middleware = create_flask_middleware(
    app,
    enable_rate_limiting=True,
    enable_metrics=True
)

# Add dependency checks to health checker
monitoring_middleware.health_checker.add_dependency_check(
    create_disk_space_check(min_free_gb=1.0)
)
monitoring_middleware.health_checker.add_dependency_check(
    create_memory_check(max_usage_percent=90.0)
)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'tiff'}


def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# HTML template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Color Transfer Framework</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }

        header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }

        h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }

        .version {
            opacity: 0.9;
            font-size: 0.9em;
        }

        .content {
            padding: 40px;
        }

        .upload-section {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 30px;
        }

        .upload-box {
            border: 2px dashed #ccc;
            border-radius: 8px;
            padding: 30px;
            text-align: center;
            transition: all 0.3s;
            background: #f8f9fa;
        }

        .upload-box:hover {
            border-color: #667eea;
            background: #f0f1ff;
        }

        .upload-box h3 {
            margin-bottom: 15px;
            color: #333;
        }

        input[type="file"] {
            margin: 10px 0;
        }

        .preview {
            max-width: 100%;
            max-height: 200px;
            margin-top: 15px;
            border-radius: 8px;
            display: none;
        }

        .config-section {
            background: #f8f9fa;
            padding: 25px;
            border-radius: 8px;
            margin-bottom: 30px;
        }

        .config-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }

        .config-item {
            margin-bottom: 15px;
        }

        label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #555;
        }

        select, input[type="range"] {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 6px;
            font-size: 14px;
        }

        input[type="range"] {
            padding: 0;
        }

        .blend-value {
            display: inline-block;
            margin-left: 10px;
            font-weight: bold;
            color: #667eea;
        }

        .checkbox-item {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        input[type="checkbox"] {
            width: 20px;
            height: 20px;
        }

        .submit-btn {
            width: 100%;
            padding: 15px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 18px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s;
        }

        .submit-btn:hover {
            transform: translateY(-2px);
        }

        .submit-btn:disabled {
            background: #ccc;
            cursor: not-allowed;
            transform: none;
        }

        .loading {
            display: none;
            text-align: center;
            padding: 40px;
        }

        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .result-section {
            display: none;
            margin-top: 30px;
            padding: 30px;
            background: #f8f9fa;
            border-radius: 8px;
        }

        .result-image {
            max-width: 100%;
            border-radius: 8px;
            margin: 20px 0;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }

        .metrics {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin: 20px 0;
        }

        .metric-card {
            background: white;
            padding: 15px;
            border-radius: 6px;
            text-align: center;
        }

        .metric-value {
            font-size: 1.8em;
            font-weight: bold;
            color: #667eea;
        }

        .metric-label {
            font-size: 0.9em;
            color: #666;
            margin-top: 5px;
        }

        .download-btn {
            display: inline-block;
            padding: 12px 30px;
            background: #28a745;
            color: white;
            text-decoration: none;
            border-radius: 6px;
            font-weight: 600;
            transition: background 0.3s;
        }

        .download-btn:hover {
            background: #218838;
        }

        .error {
            display: none;
            padding: 20px;
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
            border-radius: 6px;
            margin: 20px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🎨 Color Transfer Framework</h1>
            <p class="version">Version {{ version }}</p>
        </header>

        <div class="content">
            <form id="transferForm" enctype="multipart/form-data">
                <div class="upload-section">
                    <div class="upload-box">
                        <h3>📷 Source Image</h3>
                        <p>Color palette donor</p>
                        <input type="file" name="source" id="sourceFile" accept="image/*" required>
                        <img id="sourcePreview" class="preview">
                    </div>

                    <div class="upload-box">
                        <h3>🖼️ Target Image</h3>
                        <p>Image to be transformed</p>
                        <input type="file" name="target" id="targetFile" accept="image/*" required>
                        <img id="targetPreview" class="preview">
                    </div>
                </div>

                <div class="config-section">
                    <h3 style="margin-bottom: 20px;">⚙️ Configuration</h3>
                    <div class="config-grid">
                        <div class="config-item">
                            <label for="algorithm">Algorithm:</label>
                            <select name="algorithm" id="algorithm">
                                <option value="reinhard_lab">Reinhard L*a*b* (Default)</option>
                                <option value="reinhard_lch">Reinhard LCH</option>
                                <option value="rgb_direct">RGB Direct</option>
                                <option value="histogram_match">Histogram Match</option>
                            </select>
                        </div>

                        <div class="config-item">
                            <label for="blend">
                                Blend Factor: <span class="blend-value" id="blendValue">100%</span>
                            </label>
                            <input type="range" name="blend" id="blend" min="0" max="100" value="100">
                        </div>

                        <div class="config-item checkbox-item">
                            <input type="checkbox" name="use_gpu" id="useGpu">
                            <label for="useGpu" style="margin: 0;">Use GPU Acceleration</label>
                        </div>

                        <div class="config-item checkbox-item">
                            <input type="checkbox" name="preserve_luminance" id="preserveLuminance">
                            <label for="preserveLuminance" style="margin: 0;">Preserve Luminance (LCH only)</label>
                        </div>
                    </div>
                </div>

                <button type="submit" class="submit-btn" id="submitBtn">
                    🎨 Transfer Colors
                </button>
            </form>

            <div class="loading" id="loading">
                <div class="spinner"></div>
                <p>Processing your images...</p>
            </div>

            <div class="error" id="error"></div>

            <div class="result-section" id="resultSection">
                <h3>✨ Result</h3>
                <img id="resultImage" class="result-image">

                <div class="metrics">
                    <div class="metric-card">
                        <div class="metric-value" id="execTime">-</div>
                        <div class="metric-label">Execution Time (ms)</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value" id="memUsed">-</div>
                        <div class="metric-label">Memory Used (MB)</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value" id="throughput">-</div>
                        <div class="metric-label">Throughput (img/s)</div>
                    </div>
                </div>

                <a href="#" class="download-btn" id="downloadBtn">📥 Download Result</a>
            </div>
        </div>
    </div>

    <script>
        // Preview images
        function setupPreview(inputId, previewId) {
            document.getElementById(inputId).addEventListener('change', function(e) {
                const file = e.target.files[0];
                if (file) {
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        const preview = document.getElementById(previewId);
                        preview.src = e.target.result;
                        preview.style.display = 'block';
                    }
                    reader.readAsDataURL(file);
                }
            });
        }

        setupPreview('sourceFile', 'sourcePreview');
        setupPreview('targetFile', 'targetPreview');

        // Update blend value display
        document.getElementById('blend').addEventListener('input', function(e) {
            document.getElementById('blendValue').textContent = e.target.value + '%';
        });

        // Form submission
        document.getElementById('transferForm').addEventListener('submit', async function(e) {
            e.preventDefault();

            const formData = new FormData(this);

            // Show loading
            document.getElementById('submitBtn').disabled = true;
            document.getElementById('loading').style.display = 'block';
            document.getElementById('resultSection').style.display = 'none';
            document.getElementById('error').style.display = 'none';

            try {
                const response = await fetch('/transfer', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (!response.ok) {
                    throw new Error(data.error || 'Transfer failed');
                }

                // Display result
                document.getElementById('resultImage').src = 'data:image/png;base64,' + data.result_image;
                document.getElementById('execTime').textContent = data.metrics.execution_time_ms.toFixed(2);
                document.getElementById('memUsed').textContent = data.metrics.memory_used_mb.toFixed(2);
                document.getElementById('throughput').textContent = data.metrics.throughput_images_per_sec.toFixed(2);
                document.getElementById('downloadBtn').href = '/download/' + data.filename;

                document.getElementById('resultSection').style.display = 'block';

            } catch (error) {
                document.getElementById('error').textContent = 'Error: ' + error.message;
                document.getElementById('error').style.display = 'block';
            } finally {
                document.getElementById('loading').style.display = 'none';
                document.getElementById('submitBtn').disabled = false;
            }
        });
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    """Main page with upload form."""
    return render_template_string(HTML_TEMPLATE, version=__version__)


@app.route('/transfer', methods=['POST'])
def transfer():
    """Process transfer request."""
    try:
        # Validate files
        if 'source' not in request.files or 'target' not in request.files:
            return jsonify({'error': 'Source and target images required'}), 400

        source_file = request.files['source']
        target_file = request.files['target']

        if source_file.filename == '' or target_file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not allowed_file(source_file.filename) or not allowed_file(target_file.filename):
            return jsonify({'error': 'Invalid file type'}), 400

        # Save uploaded files
        source_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(source_file.filename))
        target_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(target_file.filename))
        source_file.save(source_path)
        target_file.save(target_path)

        # Read configuration
        algorithm = request.form.get('algorithm', 'reinhard_lab')
        blend_factor = float(request.form.get('blend', 100)) / 100.0
        use_gpu = request.form.get('use_gpu') == 'on'
        preserve_luminance = request.form.get('preserve_luminance') == 'on'

        # Build config
        config = TransferConfig(
            algorithm=TransferAlgorithm(algorithm),
            blend_factor=blend_factor,
            preserve_luminance=preserve_luminance
        )

        # Perform transfer
        result_filename = f"result_{uuid.uuid4()}.png"
        result_path = os.path.join(app.config['UPLOAD_FOLDER'], result_filename)

        orch_result = orchestrator.transfer_from_paths(
            source_path, target_path, result_path,
            config=config, enable_gpu=use_gpu,
            interface_type="WebUI"
        )

        # Read result and encode to base64
        result_image = cv2.imread(result_path)
        _, buffer = cv2.imencode('.png', result_image)
        result_b64 = buffer.tobytes().hex()  # Simple hex encoding for demo

        # Store filename in session for download
        session['last_result'] = result_filename

        return jsonify({
            'result_image': result_b64,
            'filename': result_filename,
            'metrics': {
                'execution_time_ms': orch_result.metrics.execution_time_ms,
                'memory_used_mb': orch_result.metrics.memory_used_mb,
                'throughput_images_per_sec': orch_result.metrics.throughput_images_per_sec
            },
            'run_id': orch_result.run_id
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/download/<filename>')
def download(filename):
    """Download result file."""
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename))
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404

        return send_file(file_path, as_attachment=True, download_name=filename)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Health Check Endpoints (Phase 13: Kubernetes-compatible)

@app.route('/health/live')
def health_liveness():
    """
    Liveness probe (Kubernetes-compatible).

    Checks if the process is alive and responsive.
    Returns 200 if healthy, 503 if unhealthy.
    """
    result = monitoring_middleware.check_liveness()

    if result.status.value == "healthy":
        return jsonify(result.to_dict()), 200
    else:
        return jsonify(result.to_dict()), 503


@app.route('/health/ready')
def health_readiness():
    """
    Readiness probe (Kubernetes-compatible).

    Checks if the service can handle requests (dependencies available).
    Returns 200 if ready, 503 if not ready.
    """
    result = monitoring_middleware.check_readiness()

    if result.status.value == "healthy":
        return jsonify(result.to_dict()), 200
    elif result.status.value == "degraded":
        return jsonify(result.to_dict()), 429  # Partial capacity
    else:
        return jsonify(result.to_dict()), 503


@app.route('/health')
def health_full():
    """
    Full health status with all checks and metrics.

    Returns comprehensive health information including:
    - Liveness status
    - Readiness status
    - Dependency health
    - Uptime metrics
    - Success rate
    """
    return jsonify(monitoring_middleware.get_health_status())


@app.route('/metrics')
def metrics():
    """
    Prometheus-compatible metrics endpoint.

    Returns performance metrics including:
    - Request latency percentiles (p50, p95, p99)
    - Throughput (requests per second)
    - Error rate
    - Status code distribution
    """
    return jsonify(monitoring_middleware.get_metrics())


def create_app():
    """Factory function to create Flask app."""
    return app


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
