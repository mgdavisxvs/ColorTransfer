# Color Transfer Framework - Interface Layer

Complete guide to using the Color Transfer Framework through CLI, API, and WebUI interfaces.

## Table of Contents

1. [Installation](#installation)
2. [Command-Line Interface (CLI)](#command-line-interface-cli)
3. [REST API](#rest-api)
4. [Web Interface](#web-interface)
5. [Performance Benchmarking](#performance-benchmarking)
6. [Examples](#examples)

---

## Installation

### Core Dependencies

```bash
pip install -r requirements.txt
```

### Optional Dependencies

For GPU acceleration:
```bash
pip install torch torchvision
```

---

## Command-Line Interface (CLI)

The CLI provides a modern, user-friendly command-line interface powered by Typer.

### Basic Usage

Transfer colors from source to target:

```bash
python -m color_transfer_framework.interface_layer.cli transfer SOURCE.jpg TARGET.jpg -o RESULT.jpg
```

### Transfer Command

```
color-transfer transfer SOURCE TARGET [OPTIONS]
```

**Arguments:**
- `SOURCE`: Path to source image (color palette donor)
- `TARGET`: Path to target image (to be transformed)

**Options:**
- `-o, --output PATH`: Output file path (default: `target_transferred.png`)
- `-a, --algo ALGORITHM`: Algorithm to use
  - `reinhard_lab` (default): Reinhard method in L*a*b* space
  - `reinhard_lch`: Reinhard method in LCH space
  - `rgb_direct`: Direct RGB transfer
  - `histogram_match`: Histogram matching
- `-b, --blend FLOAT`: Blend factor 0.0-1.0 (default: 1.0)
- `-m, --mask PATH`: Path to mask image (optional)
- `--gpu`: Enable GPU acceleration
- `-v, --visualize`: Generate comprehensive diagnostic report
- `--preserve-luminance`: Preserve original luminance (LCH only)

### Examples

**Basic transfer:**
```bash
python -m color_transfer_framework.interface_layer.cli transfer sunset.jpg portrait.jpg
```

**With custom algorithm and blending:**
```bash
python -m color_transfer_framework.interface_layer.cli transfer source.jpg target.jpg \
    --algo reinhard_lch \
    --blend 0.7 \
    --output result.jpg
```

**With mask for selective transfer:**
```bash
python -m color_transfer_framework.interface_layer.cli transfer source.jpg target.jpg \
    --mask face_mask.png \
    --output result.jpg
```

**Generate diagnostic visualizations:**
```bash
python -m color_transfer_framework.interface_layer.cli transfer source.jpg target.jpg \
    --visualize \
    --output result.jpg
```

This creates a `diagnostics/` folder with:
- Histogram comparisons
- 3D color space plots
- Delta E perceptual difference maps
- Statistical summaries

### Other Commands

**List available algorithms:**
```bash
python -m color_transfer_framework.interface_layer.cli algorithms
```

**Show framework information:**
```bash
python -m color_transfer_framework.interface_layer.cli info
```

---

## Terminal User Interface (TUI)

Modern terminal-based interface built with Textual framework. ⭐ NEW in Phase 6

### Starting the TUI

```bash
python -m color_transfer_framework.interface_layer.tui
```

### Features

- **Interactive File Picker**: Navigate file system with tree view to select source/target images
- **Configuration Form**: Select algorithm and adjust blend factor
- **Real-time Progress**: Live progress bar with status updates
- **Result Metrics**: View execution time, memory usage, and throughput
- **Rich Logging**: Color-coded log display for operation history
- **Keyboard Shortcuts**:
  - `r`: Run transfer
  - `q`: Quit application

### Usage

1. Navigate the file tree panes to select source and target images
2. Configure algorithm and blend factor in the configuration pane
3. Click "Run Transfer" button or press `r`
4. Monitor progress in real-time in the status pane
5. View results and metrics when complete

---

## REST API

High-performance RESTful API built with FastAPI.

### WebSocket Support ⭐ NEW

The API now includes WebSocket support for real-time progress updates during transfer operations.

### Starting the Server

```bash
uvicorn color_transfer_framework.interface_layer.api:app --host 0.0.0.0 --port 8000
```

For development (with auto-reload):
```bash
uvicorn color_transfer_framework.interface_layer.api:app --reload
```

### API Documentation

Once running, visit:
- **Interactive docs:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

### Endpoints

#### WS /api/v1/ws/progress/{client_id} ⭐ NEW

WebSocket endpoint for real-time progress updates.

**Parameters:**
- `client_id`: Unique identifier for the client session

**Messages:**
```json
{
  "status": "applying_transform",
  "percent": 50
}
```

**Status values:**
- `initializing`: Starting transfer operation
- `loading_images`: Loading source and target images
- `calculating_statistics`: Computing color statistics
- `applying_transform`: Performing color transformation
- `processing_result`: Post-processing result
- `generating_diagnostics`: Creating diagnostic visualizations (if enabled)
- `saving_metadata`: Logging to persistence layer
- `complete`: Operation finished

**Example:**
```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/ws/progress/my_client_123');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(`Progress: ${data.percent}% - ${data.status}`);
};
```

#### GET /api/v1/health

Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "version": "2.0.0-alpha",
  "modules_available": {
    "transfer_engine": true,
    "optimizer_engine": true,
    "diagnostics_visualizer": true,
    "complexity_analyzer": true
  }
}
```

#### GET /api/v1/algorithms

List available transfer algorithms.

**Response:**
```json
{
  "algorithms": [
    {
      "name": "Reinhard L*a*b*",
      "value": "reinhard_lab",
      "description": "Reinhard et al. method in perceptually uniform L*a*b* color space (default)"
    },
    ...
  ]
}
```

#### POST /api/v1/transfer

Perform color transfer operation.

**Request:**
```json
{
  "source_image": "base64_encoded_image_data",
  "target_image": "base64_encoded_image_data",
  "mask_image": "base64_encoded_mask_data",  // Optional
  "client_id": "unique_client_identifier",  // Optional - for WebSocket progress updates ⭐ NEW
  "config": {
    "algorithm": "reinhard_lab",
    "blend_factor": 1.0,
    "clip_output": true,
    "preserve_luminance": false,
    "epsilon": 1e-10,
    "use_gpu": false
  }
}
```

**Response:**
```json
{
  "result_image": "base64_encoded_result",
  "metrics": {
    "execution_time_ms": 150.25,
    "memory_used_mb": 45.3,
    "throughput_images_per_sec": 6.66
  },
  "run_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Python Client Example

```python
import requests
import base64
from pathlib import Path

# Read and encode images
def encode_image(path):
    with open(path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

source_b64 = encode_image('source.jpg')
target_b64 = encode_image('target.jpg')

# Send request
response = requests.post(
    'http://localhost:8000/api/v1/transfer',
    json={
        'source_image': source_b64,
        'target_image': target_b64,
        'config': {
            'algorithm': 'reinhard_lab',
            'blend_factor': 0.8
        }
    }
)

result = response.json()

# Decode and save result
result_data = base64.b64decode(result['result_image'])
Path('result.png').write_bytes(result_data)

print(f"Execution time: {result['metrics']['execution_time_ms']:.2f} ms")
```

### JavaScript Client Example

```javascript
async function transferColors(sourceFile, targetFile) {
  // Convert files to base64
  const toBase64 = file => new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = () => resolve(reader.result.split(',')[1]);
    reader.onerror = error => reject(error);
  });

  const sourceB64 = await toBase64(sourceFile);
  const targetB64 = await toBase64(targetFile);

  // Send request
  const response = await fetch('http://localhost:8000/api/v1/transfer', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      source_image: sourceB64,
      target_image: targetB64,
      config: {
        algorithm: 'reinhard_lab',
        blend_factor: 1.0
      }
    })
  });

  const result = await response.json();
  return result;
}
```

---

## Web Interface

User-friendly web interface built with Flask.

### Starting the Web Server

```bash
python -m color_transfer_framework.interface_layer.web_enhanced
```

Then visit: http://localhost:5000

### Features

- **File Upload**: Drag-and-drop or browse for source and target images
- **Algorithm Selection**: Choose from 4 transfer algorithms
- **Blend Control**: Adjust blend factor with slider (0-100%)
- **GPU Toggle**: Enable GPU acceleration
- **Instant Results**: View transformed image immediately
- **Download**: Save result with one click
- **Performance Metrics**: See execution time, memory usage, and throughput
- **Real-time Progress** ⭐ NEW: WebSocket-based live progress updates with granular status
- **Undo/Redo** ⭐ NEW: Instantly toggle between original and transformed images
- **Configuration Management**: Save and load transfer configurations

### Usage

1. Upload source image (color palette donor)
2. Upload target image (image to transform)
3. Select algorithm from dropdown
4. Adjust blend factor slider
5. (Optional) Enable GPU acceleration
6. Click "Transfer Colors"
7. View result and download

---

## Performance Benchmarking

Comprehensive automated benchmarking suite.

### Running Benchmarks

**Full benchmark suite:**
```bash
python run_performance_suite.py
```

**Custom benchmark:**
```bash
python run_performance_suite.py \
    --algorithms reinhard_lab rgb_direct \
    --modes cpu gpu \
    --sizes 512x512 1080p 4k \
    --batch-sizes 1 10 50 \
    --iterations 10 \
    --output ./my_benchmarks
```

### Options

- `--algorithms`: Algorithms to benchmark (default: all)
- `--modes`: Execution modes: `cpu`, `gpu` (default: cpu)
- `--sizes`: Image sizes: `512x512`, `1080p`, `4k` or custom `WIDTHxHEIGHT`
- `--batch-sizes`: Batch sizes to test (default: 1, 10)
- `--iterations`: Iterations per test for averaging (default: 5)
- `--output`: Output directory (default: ./benchmarks)

### Output Files

- **benchmark_results.csv**: Raw results in CSV format
- **BENCHMARKS.md**: Human-readable summary report

### Benchmark Metrics

For each configuration, benchmarks measure:
- Average execution time (ms)
- Standard deviation (ms)
- Throughput (images/sec)
- Peak memory usage (MB)
- Peak VRAM usage (MB, for GPU)

---

## Examples

### Example 1: Sunset Color Grading

Transfer warm sunset colors to a daytime photo:

```bash
python -m color_transfer_framework.interface_layer.cli transfer \
    sunset_reference.jpg \
    daytime_photo.jpg \
    --algo reinhard_lch \
    --blend 0.6 \
    --output warm_graded.jpg
```

### Example 2: Artistic Style Transfer

Apply artistic color palette to photograph:

```bash
python -m color_transfer_framework.interface_layer.cli transfer \
    van_gogh_painting.jpg \
    modern_photo.jpg \
    --algo histogram_match \
    --visualize \
    --output artistic_result.jpg
```

### Example 3: Selective Face Color Correction

Transfer skin tones using a face mask:

```bash
python -m color_transfer_framework.interface_layer.cli transfer \
    reference_portrait.jpg \
    target_portrait.jpg \
    --mask face_mask.png \
    --blend 0.8 \
    --output corrected_portrait.jpg
```

### Example 4: Batch Processing via API

Process multiple images programmatically:

```python
import requests
import base64
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

def process_image(target_path, source_b64):
    with open(target_path, 'rb') as f:
        target_b64 = base64.b64encode(f.read()).decode()

    response = requests.post(
        'http://localhost:8000/api/v1/transfer',
        json={
            'source_image': source_b64,
            'target_image': target_b64,
            'config': {'algorithm': 'reinhard_lab'}
        }
    )

    result = response.json()
    output_path = target_path.parent / f"{target_path.stem}_transferred.png"
    output_path.write_bytes(base64.b64decode(result['result_image']))
    return output_path

# Load reference image once
with open('reference.jpg', 'rb') as f:
    reference_b64 = base64.b64encode(f.read()).decode()

# Process all images in directory
image_files = list(Path('./photos').glob('*.jpg'))

with ThreadPoolExecutor(max_workers=4) as executor:
    results = executor.map(
        lambda p: process_image(p, reference_b64),
        image_files
    )

print(f"Processed {len(list(results))} images")
```

### Example 5: Comparative Analysis

Generate diagnostic reports to compare algorithms:

```bash
for algo in reinhard_lab reinhard_lch rgb_direct histogram_match; do
    python -m color_transfer_framework.interface_layer.cli transfer \
        source.jpg target.jpg \
        --algo $algo \
        --visualize \
        --output results/${algo}_result.jpg
done
```

---

## Persistence and Logging

All transfer operations are automatically logged to `transfer_log.db` with:

- Unique run ID
- Timestamp
- Image hashes (source, target, result)
- Algorithm and configuration
- Performance metrics
- Interface type (CLI, API, WebUI)
- Success/error status

### Querying Logs

```python
from color_transfer_framework.persistence_logger import PersistenceLogger

logger = PersistenceLogger()

# Get recent history
history = logger.get_history(limit=10)

# Get statistics
stats = logger.get_stats()
print(f"Total runs: {stats['total_runs']}")
print(f"Success rate: {stats['success_rate']:.1f}%")
print(f"Avg execution time: {stats['avg_execution_time_ms']:.2f} ms")
```

---

## Troubleshooting

### GPU Not Available

If `--gpu` flag shows no improvement:
1. Check PyTorch installation: `python -c "import torch; print(torch.cuda.is_available())"`
2. Verify CUDA drivers
3. Install GPU-enabled PyTorch: `pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118`

### API Connection Refused

1. Ensure server is running: `uvicorn color_transfer_framework.interface_layer.api:app`
2. Check firewall settings
3. Verify port 8000 is not in use

### Out of Memory

For large images:
1. Use `rgb_direct` algorithm (fastest, lowest memory)
2. Process images at lower resolution
3. Enable GPU acceleration with `--gpu`

### Slow Performance

1. Run benchmarks to identify bottleneck: `python run_performance_suite.py`
2. Use GPU acceleration for batch processing
3. Choose faster algorithm (rgb_direct > reinhard_lab > histogram_match)

---

## Support

For issues, feature requests, or questions:
- GitHub Issues: https://github.com/your-org/ColorTransfer/issues
- Documentation: See `ARCHITECTURE.md` for technical details
- Examples: See `examples/` directory for more use cases
