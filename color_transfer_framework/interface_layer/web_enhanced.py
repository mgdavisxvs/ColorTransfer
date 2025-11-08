"""
Enhanced Flask Web Interface
============================

Feature-rich web interface with advanced UX improvements:
- Image preview before processing
- Side-by-side comparison slider
- Configuration save/load
- Real-time progress updates (future: WebSocket)

Routes:
- GET /: Main page with upload form
- POST /transfer: Process transfer request
- GET /download/<filename>: Download result
- POST /save_config: Save configuration
- GET /load_config: Load saved configurations
"""

from flask import Flask, render_template_string, request, send_file, jsonify, session
from werkzeug.utils import secure_filename
import os
import tempfile
import uuid
import json
from pathlib import Path
from datetime import datetime
import cv2
import numpy as np
import base64
import asyncio
from typing import Dict
try:
    from flask_sock import Sock
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    print("Warning: flask-sock not installed. WebSocket progress updates will not be available.")
    print("Install with: pip install flask-sock")

from .orchestrator import TransferOrchestrator
from ..transfer_engine import TransferConfig, TransferAlgorithm
from .. import __version__

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload
app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()
app.config['CONFIG_FOLDER'] = Path.home() / '.color_transfer' / 'configs'
app.config['CONFIG_FOLDER'].mkdir(parents=True, exist_ok=True)

# Initialize orchestrator
orchestrator = TransferOrchestrator()

# Initialize WebSocket support if available
if WEBSOCKET_AVAILABLE:
    sock = Sock(app)

# WebSocket Connection Manager for Flask
class FlaskConnectionManager:
    """Manages active WebSocket connections for progress updates."""

    def __init__(self):
        self.active_connections: Dict[str, any] = {}

    def add_connection(self, client_id: str, ws):
        """Store a WebSocket connection."""
        self.active_connections[client_id] = ws

    def remove_connection(self, client_id: str):
        """Remove a WebSocket connection."""
        if client_id in self.active_connections:
            del self.active_connections[client_id]

    def send_progress(self, client_id: str, status: str, percent: int):
        """Send progress update to a specific client."""
        if client_id in self.active_connections:
            try:
                ws = self.active_connections[client_id]
                ws.send(json.dumps({
                    "status": status,
                    "percent": percent
                }))
            except Exception as e:
                print(f"Error sending progress to {client_id}: {e}")
                self.remove_connection(client_id)

# Initialize connection manager
flask_manager = FlaskConnectionManager()

# Allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'tiff'}


def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def image_to_base64(image_path):
    """Convert image file to base64 for preview."""
    with open(image_path, 'rb') as f:
        img_data = f.read()
        return base64.b64encode(img_data).decode('utf-8')


# Enhanced HTML template with all UX improvements
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Color Transfer Framework - Enhanced</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/image-compare-viewer/1.6.2/image-compare-viewer.min.css">
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
            max-width: 1400px;
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
            position: relative;
        }

        h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }

        .version {
            opacity: 0.9;
            font-size: 0.9em;
        }

        .config-controls {
            position: absolute;
            top: 20px;
            right: 20px;
            display: flex;
            gap: 10px;
        }

        .config-btn {
            padding: 8px 16px;
            background: rgba(255,255,255,0.2);
            color: white;
            border: 1px solid rgba(255,255,255,0.5);
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.9em;
            transition: all 0.3s;
        }

        .config-btn:hover {
            background: rgba(255,255,255,0.3);
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
            padding: 20px;
            text-align: center;
            transition: all 0.3s;
            background: #f8f9fa;
            position: relative;
        }

        .upload-box:hover {
            border-color: #667eea;
            background: #f0f1ff;
        }

        .upload-box.drag-over {
            border-color: #667eea;
            background: #e6e8ff;
            transform: scale(1.02);
        }

        .upload-box h3 {
            margin-bottom: 15px;
            color: #333;
        }

        input[type="file"] {
            margin: 10px 0;
        }

        .preview-container {
            margin-top: 15px;
            min-height: 200px;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .preview {
            max-width: 100%;
            max-height: 250px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            display: none;
        }

        .preview.visible {
            display: block;
        }

        .preview-placeholder {
            color: #999;
            font-size: 0.9em;
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

        select, input[type="range"], input[type="text"] {
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

        .progress-container {
            width: 100%;
            max-width: 500px;
            margin: 20px auto;
        }

        .progress-bar {
            width: 100%;
            height: 30px;
            background-color: #f3f3f3;
            border-radius: 15px;
            overflow: hidden;
            box-shadow: inset 0 2px 4px rgba(0,0,0,0.1);
        }

        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            border-radius: 15px;
            transition: width 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            font-size: 14px;
        }

        .progress-status {
            text-align: center;
            margin-top: 10px;
            color: #666;
            font-size: 14px;
        }

        .result-section {
            display: none;
            margin-top: 30px;
            padding: 30px;
            background: #f8f9fa;
            border-radius: 8px;
        }

        .comparison-container {
            margin: 20px 0;
            position: relative;
        }

        #comparison-slider {
            max-width: 100%;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
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

        .action-buttons {
            display: flex;
            gap: 15px;
            justify-content: center;
            margin-top: 20px;
        }

        .download-btn, .new-transfer-btn {
            padding: 12px 30px;
            background: #28a745;
            color: white;
            text-decoration: none;
            border: none;
            border-radius: 6px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.3s;
        }

        .download-btn:hover {
            background: #218838;
        }

        .new-transfer-btn {
            background: #667eea;
        }

        .new-transfer-btn:hover {
            background: #5568d3;
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

        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 1000;
            align-items: center;
            justify-content: center;
        }

        .modal.active {
            display: flex;
        }

        .modal-content {
            background: white;
            padding: 30px;
            border-radius: 12px;
            max-width: 500px;
            width: 90%;
            max-height: 80vh;
            overflow-y: auto;
        }

        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }

        .modal-header h2 {
            color: #333;
        }

        .close-btn {
            background: none;
            border: none;
            font-size: 24px;
            cursor: pointer;
            color: #999;
        }

        .config-list {
            list-style: none;
        }

        .config-item-list {
            padding: 15px;
            margin: 10px 0;
            background: #f8f9fa;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.3s;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .config-item-list:hover {
            background: #e9ecef;
            transform: translateX(5px);
        }

        .config-name {
            font-weight: 600;
            color: #333;
        }

        .config-date {
            font-size: 0.85em;
            color: #666;
        }

        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            border-bottom: 2px solid #e9ecef;
        }

        .tab {
            padding: 10px 20px;
            background: none;
            border: none;
            border-bottom: 3px solid transparent;
            cursor: pointer;
            font-weight: 600;
            color: #666;
            transition: all 0.3s;
        }

        .tab.active {
            color: #667eea;
            border-bottom-color: #667eea;
        }

        .tab-content {
            display: none;
        }

        .tab-content.active {
            display: block;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="config-controls">
                <button class="config-btn" onclick="openSaveConfig()">💾 Save Config</button>
                <button class="config-btn" onclick="openLoadConfig()">📂 Load Config</button>
            </div>
            <h1>🎨 Color Transfer Framework</h1>
            <p class="version">Enhanced Edition - Version {{ version }}</p>
        </header>

        <div class="content">
            <form id="transferForm" enctype="multipart/form-data">
                <div class="upload-section">
                    <div class="upload-box" id="sourceBox">
                        <h3>📷 Source Image</h3>
                        <p>Color palette donor</p>
                        <input type="file" name="source" id="sourceFile" accept="image/*" required>
                        <div class="preview-container">
                            <div class="preview-placeholder" id="sourcePlaceholder">No image selected</div>
                            <img id="sourcePreview" class="preview">
                        </div>
                    </div>

                    <div class="upload-box" id="targetBox">
                        <h3>🖼️ Target Image</h3>
                        <p>Image to be transformed</p>
                        <input type="file" name="target" id="targetFile" accept="image/*" required>
                        <div class="preview-container">
                            <div class="preview-placeholder" id="targetPlaceholder">No image selected</div>
                            <img id="targetPreview" class="preview">
                        </div>
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
                <div class="spinner" id="spinner"></div>
                <div class="progress-container" id="progressContainer" style="display: none;">
                    <div class="progress-bar">
                        <div class="progress-fill" id="progressFill" style="width: 0%;">
                            <span id="progressPercent">0%</span>
                        </div>
                    </div>
                    <div class="progress-status" id="progressStatus">Initializing...</div>
                </div>
                <p id="loadingText">Processing your images...</p>
            </div>

            <div class="error" id="error"></div>

            <div class="result-section" id="resultSection">
                <div class="tabs">
                    <button class="tab active" onclick="switchTab('comparison')">Comparison</button>
                    <button class="tab" onclick="switchTab('result')">Result Only</button>
                    <button class="tab" onclick="switchTab('metrics')">Metrics</button>
                </div>

                <div class="tab-content active" id="comparisonTab">
                    <h3>✨ Before / After Comparison</h3>
                    <p style="margin: 10px 0; color: #666; font-size: 0.9em;">Drag the slider to compare</p>
                    <div class="comparison-container" id="comparisonContainer">
                        <!-- Comparison slider will be inserted here -->
                    </div>
                </div>

                <div class="tab-content" id="resultTab">
                    <h3>✨ Result</h3>
                    <img id="resultImage" class="result-image">
                </div>

                <div class="tab-content" id="metricsTab">
                    <h3>📊 Performance Metrics</h3>
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
                </div>

                <div class="action-buttons">
                    <button class="new-transfer-btn" onclick="undoTransfer()" id="undoBtn" style="display: none;">↶ Undo</button>
                    <button class="new-transfer-btn" onclick="redoTransfer()" id="redoBtn" style="display: none;">↷ Redo</button>
                    <a href="#" class="download-btn" id="downloadBtn">📥 Download Result</a>
                    <button class="new-transfer-btn" onclick="resetForm()">🔄 New Transfer</button>
                </div>
            </div>
        </div>
    </div>

    <!-- Save Config Modal -->
    <div class="modal" id="saveConfigModal">
        <div class="modal-content">
            <div class="modal-header">
                <h2>Save Configuration</h2>
                <button class="close-btn" onclick="closeSaveConfig()">&times;</button>
            </div>
            <div class="config-item">
                <label for="configName">Configuration Name:</label>
                <input type="text" id="configName" placeholder="My Favorite Config">
            </div>
            <button class="submit-btn" style="margin-top: 20px;" onclick="saveConfig()">Save</button>
        </div>
    </div>

    <!-- Load Config Modal -->
    <div class="modal" id="loadConfigModal">
        <div class="modal-content">
            <div class="modal-header">
                <h2>Load Configuration</h2>
                <button class="close-btn" onclick="closeLoadConfig()">&times;</button>
            </div>
            <ul class="config-list" id="configList">
                <!-- Configs will be loaded here -->
            </ul>
        </div>
    </div>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/image-compare-viewer/1.6.2/image-compare-viewer.min.js"></script>
    <script>
        let targetImageData = null;
        let resultImageData = null;

        // State management for Undo/Redo
        const stateCache = {
            originalTarget: null,
            currentResult: null,
            isShowingOriginal: false
        };

        // Setup drag and drop
        function setupDragDrop(boxId, inputId) {
            const box = document.getElementById(boxId);
            const input = document.getElementById(inputId);

            ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
                box.addEventListener(eventName, preventDefaults, false);
            });

            function preventDefaults(e) {
                e.preventDefault();
                e.stopPropagation();
            }

            ['dragenter', 'dragover'].forEach(eventName => {
                box.addEventListener(eventName, () => box.classList.add('drag-over'), false);
            });

            ['dragleave', 'drop'].forEach(eventName => {
                box.addEventListener(eventName, () => box.classList.remove('drag-over'), false);
            });

            box.addEventListener('drop', (e) => {
                const dt = e.dataTransfer;
                const files = dt.files;
                input.files = files;
                input.dispatchEvent(new Event('change'));
            });
        }

        setupDragDrop('sourceBox', 'sourceFile');
        setupDragDrop('targetBox', 'targetFile');

        // Preview images
        function setupPreview(inputId, previewId, placeholderId) {
            document.getElementById(inputId).addEventListener('change', function(e) {
                const file = e.target.files[0];
                if (file) {
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        const preview = document.getElementById(previewId);
                        const placeholder = document.getElementById(placeholderId);
                        preview.src = e.target.result;
                        preview.classList.add('visible');
                        placeholder.style.display = 'none';

                        if (inputId === 'targetFile') {
                            targetImageData = e.target.result;
                        }
                    }
                    reader.readAsDataURL(file);
                }
            });
        }

        setupPreview('sourceFile', 'sourcePreview', 'sourcePlaceholder');
        setupPreview('targetFile', 'targetPreview', 'targetPlaceholder');

        // Update blend value display
        document.getElementById('blend').addEventListener('input', function(e) {
            document.getElementById('blendValue').textContent = e.target.value + '%';
        });

        // Tab switching
        function switchTab(tabName) {
            document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

            event.target.classList.add('active');
            document.getElementById(tabName + 'Tab').classList.add('active');
        }

        // Generate unique client ID
        function generateClientId() {
            return 'client_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        }

        // Update progress bar
        function updateProgress(percent, status) {
            const progressFill = document.getElementById('progressFill');
            const progressPercent = document.getElementById('progressPercent');
            const progressStatus = document.getElementById('progressStatus');

            progressFill.style.width = percent + '%';
            progressPercent.textContent = percent + '%';

            // Format status text
            const statusTexts = {
                'initializing': 'Initializing...',
                'loading_images': 'Loading images...',
                'calculating_statistics': 'Calculating color statistics...',
                'applying_transform': 'Applying color transformation...',
                'processing_result': 'Processing result...',
                'generating_diagnostics': 'Generating diagnostics...',
                'saving_metadata': 'Saving metadata...',
                'complete': 'Complete!'
            };

            progressStatus.textContent = statusTexts[status] || status;
        }

        // Form submission with WebSocket progress
        document.getElementById('transferForm').addEventListener('submit', async function(e) {
            e.preventDefault();

            const formData = new FormData(this);
            const clientId = generateClientId();

            // Show loading and hide spinner, show progress bar
            document.getElementById('submitBtn').disabled = true;
            document.getElementById('loading').style.display = 'block';
            document.getElementById('resultSection').style.display = 'none';
            document.getElementById('error').style.display = 'none';
            document.getElementById('spinner').style.display = 'none';
            document.getElementById('progressContainer').style.display = 'block';
            document.getElementById('loadingText').textContent = 'Connecting...';

            // Establish WebSocket connection
            const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${wsProtocol}//${window.location.host}/ws/progress/${clientId}`;
            const ws = new WebSocket(wsUrl);

            ws.onopen = () => {
                console.log('WebSocket connected');
                document.getElementById('loadingText').textContent = 'Processing...';
            };

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                updateProgress(data.percent, data.status);
            };

            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                // Fall back to spinner if WebSocket fails
                document.getElementById('progressContainer').style.display = 'none';
                document.getElementById('spinner').style.display = 'block';
            };

            ws.onclose = () => {
                console.log('WebSocket disconnected');
            };

            try {
                // Add client_id to formData
                formData.append('client_id', clientId);

                const response = await fetch('/transfer', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (!response.ok) {
                    throw new Error(data.error || 'Transfer failed');
                }

                // Display result
                const resultImg = 'data:image/png;base64,' + data.result_image;
                resultImageData = resultImg;

                // Cache images for Undo/Redo
                stateCache.originalTarget = targetImageData;
                stateCache.currentResult = resultImg;
                stateCache.isShowingOriginal = false;

                document.getElementById('resultImage').src = resultImg;
                document.getElementById('execTime').textContent = data.metrics.execution_time_ms.toFixed(2);
                document.getElementById('memUsed').textContent = data.metrics.memory_used_mb.toFixed(2);
                document.getElementById('throughput').textContent = data.metrics.throughput_images_per_sec.toFixed(2);
                document.getElementById('downloadBtn').href = '/download/' + data.filename;

                // Setup comparison slider
                setupComparisonSlider(targetImageData, resultImg);

                // Show Undo button, hide Redo button
                document.getElementById('undoBtn').style.display = 'inline-block';
                document.getElementById('redoBtn').style.display = 'none';

                document.getElementById('resultSection').style.display = 'block';

            } catch (error) {
                document.getElementById('error').textContent = 'Error: ' + error.message;
                document.getElementById('error').style.display = 'block';
            } finally {
                // Close WebSocket
                if (ws.readyState === WebSocket.OPEN) {
                    ws.close();
                }

                // Reset loading UI
                document.getElementById('loading').style.display = 'none';
                document.getElementById('submitBtn').disabled = false;
                document.getElementById('spinner').style.display = 'block';
                document.getElementById('progressContainer').style.display = 'none';
                updateProgress(0, 'initializing');
            }
        });

        function setupComparisonSlider(beforeImg, afterImg) {
            const container = document.getElementById('comparisonContainer');
            container.innerHTML = `
                <div id="comparison-slider">
                    <img src="${beforeImg}" alt="Before">
                    <img src="${afterImg}" alt="After">
                </div>
            `;

            // Initialize image comparison slider
            const element = document.getElementById('comparison-slider');
            const viewer = new ImageCompare(element, {
                controlColor: "#667eea",
                controlShadow: true,
                addCircle: true,
                addCircleBlur: false,
                showLabels: true,
                labelOptions: {
                    before: 'Original',
                    after: 'Transformed',
                    onHover: false
                }
            }).mount();
        }

        function resetForm() {
            location.reload();
        }

        // Undo/Redo functionality
        function undoTransfer() {
            if (!stateCache.originalTarget) return;

            stateCache.isShowingOriginal = true;
            document.getElementById('resultImage').src = stateCache.originalTarget;

            // Update button visibility
            document.getElementById('undoBtn').style.display = 'none';
            document.getElementById('redoBtn').style.display = 'inline-block';

            // Update comparison slider to show original
            setupComparisonSlider(stateCache.originalTarget, stateCache.originalTarget);
        }

        function redoTransfer() {
            if (!stateCache.currentResult) return;

            stateCache.isShowingOriginal = false;
            document.getElementById('resultImage').src = stateCache.currentResult;

            // Update button visibility
            document.getElementById('undoBtn').style.display = 'inline-block';
            document.getElementById('redoBtn').style.display = 'none';

            // Restore comparison slider with result
            setupComparisonSlider(stateCache.originalTarget, stateCache.currentResult);
        }

        // Configuration Save/Load
        function getCurrentConfig() {
            return {
                algorithm: document.getElementById('algorithm').value,
                blend: parseInt(document.getElementById('blend').value),
                use_gpu: document.getElementById('useGpu').checked,
                preserve_luminance: document.getElementById('preserveLuminance').checked,
                timestamp: new Date().toISOString()
            };
        }

        function loadConfig(config) {
            document.getElementById('algorithm').value = config.algorithm;
            document.getElementById('blend').value = config.blend;
            document.getElementById('blendValue').textContent = config.blend + '%';
            document.getElementById('useGpu').checked = config.use_gpu;
            document.getElementById('preserveLuminance').checked = config.preserve_luminance;
        }

        function openSaveConfig() {
            document.getElementById('saveConfigModal').classList.add('active');
        }

        function closeSaveConfig() {
            document.getElementById('saveConfigModal').classList.remove('active');
        }

        async function saveConfig() {
            const name = document.getElementById('configName').value;
            if (!name) {
                alert('Please enter a configuration name');
                return;
            }

            const config = getCurrentConfig();

            try {
                const response = await fetch('/save_config', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({name, config})
                });

                const data = await response.json();
                if (response.ok) {
                    alert('Configuration saved successfully!');
                    closeSaveConfig();
                    document.getElementById('configName').value = '';
                } else {
                    alert('Failed to save configuration: ' + data.error);
                }
            } catch (error) {
                alert('Error saving configuration: ' + error.message);
            }
        }

        async function openLoadConfig() {
            document.getElementById('loadConfigModal').classList.add('active');

            try {
                const response = await fetch('/load_configs');
                const data = await response.json();

                const configList = document.getElementById('configList');
                configList.innerHTML = '';

                if (data.configs.length === 0) {
                    configList.innerHTML = '<p style="color: #999; text-align: center; padding: 20px;">No saved configurations</p>';
                } else {
                    data.configs.forEach(item => {
                        const li = document.createElement('li');
                        li.className = 'config-item-list';
                        li.innerHTML = `
                            <div>
                                <div class="config-name">${item.name}</div>
                                <div class="config-date">${new Date(item.config.timestamp).toLocaleString()}</div>
                            </div>
                            <button class="config-btn" onclick='loadSavedConfig(${JSON.stringify(item.config)})'>Load</button>
                        `;
                        configList.appendChild(li);
                    });
                }
            } catch (error) {
                alert('Error loading configurations: ' + error.message);
            }
        }

        function closeLoadConfig() {
            document.getElementById('loadConfigModal').classList.remove('active');
        }

        function loadSavedConfig(config) {
            loadConfig(config);
            closeLoadConfig();
            alert('Configuration loaded!');
        }
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    """Main page with upload form."""
    return render_template_string(HTML_TEMPLATE, version=__version__)


@app.route('/ws/progress/<client_id>')
def websocket_progress(client_id):
    """WebSocket endpoint for real-time progress updates (Flask)."""
    if not WEBSOCKET_AVAILABLE:
        return jsonify({'error': 'WebSocket support not available'}), 501

    ws = sock(request.environ)
    flask_manager.add_connection(client_id, ws)

    try:
        # Keep connection alive and listen for client messages
        while True:
            data = ws.receive()
            if data is None:
                break
    except Exception as e:
        print(f"WebSocket error for {client_id}: {e}")
    finally:
        flask_manager.remove_connection(client_id)

    return ''


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
        client_id = request.form.get('client_id')  # Get client_id for WebSocket updates

        # Build config
        config = TransferConfig(
            algorithm=TransferAlgorithm(algorithm),
            blend_factor=blend_factor,
            preserve_luminance=preserve_luminance
        )

        # Create progress callback if client_id provided
        progress_callback = None
        if client_id and WEBSOCKET_AVAILABLE:
            def progress_callback(status: str, percent: int):
                flask_manager.send_progress(client_id, status, percent)

        # Load images
        source_image = cv2.imread(source_path)
        target_image = cv2.imread(target_path)

        if source_image is None or target_image is None:
            return jsonify({'error': 'Failed to load images'}), 400

        # Perform transfer with progress callback
        result_filename = f"result_{uuid.uuid4()}.png"
        result_path = os.path.join(app.config['UPLOAD_FOLDER'], result_filename)

        orch_result = orchestrator.transfer(
            source_image, target_image,
            config=config,
            enable_gpu=use_gpu,
            generate_diagnostics=False,
            profile_performance=True,
            interface_type="WebUI",
            progress_callback=progress_callback
        )

        # Save result
        cv2.imwrite(result_path, orch_result.result_image)

        # Read result and encode to base64
        _, buffer = cv2.imencode('.png', orch_result.result_image)
        result_b64 = base64.b64encode(buffer).decode('utf-8')

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


@app.route('/save_config', methods=['POST'])
def save_config():
    """Save configuration to file."""
    try:
        data = request.json
        name = data.get('name')
        config = data.get('config')

        if not name or not config:
            return jsonify({'error': 'Name and config required'}), 400

        # Save to config folder
        config_file = app.config['CONFIG_FOLDER'] / f"{name}.json"
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)

        return jsonify({'success': True, 'path': str(config_file)})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/load_configs')
def load_configs():
    """Load all saved configurations."""
    try:
        configs = []
        for config_file in app.config['CONFIG_FOLDER'].glob('*.json'):
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    configs.append({
                        'name': config_file.stem,
                        'config': config
                    })
            except:
                pass

        return jsonify({'configs': configs})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


def create_app():
    """Factory function to create Flask app."""
    return app


if __name__ == '__main__':
    print("=" * 70)
    print("Color Transfer Framework - Enhanced WebUI")
    print("=" * 70)
    print(f"Starting server at http://localhost:5000")
    print(f"Config folder: {app.config['CONFIG_FOLDER']}")
    print("=" * 70)
    app.run(debug=True, host='0.0.0.0', port=5000)
