# GPU Acceleration Guide

Complete guide for enabling and using GPU acceleration in the Color Transfer Framework.

## Overview

The Color Transfer Framework supports optional GPU acceleration using CUDA and PyTorch. GPU acceleration can provide **10-100x speedup** for large images and batch processing.

### Performance Comparison

| Image Size | CPU (seconds) | GPU (seconds) | Speedup |
|-----------|---------------|---------------|---------|
| 512x512   | 0.15          | 0.02          | 7.5x    |
| 1024x1024 | 0.60          | 0.05          | 12x     |
| 2048x2048 | 2.40          | 0.12          | 20x     |
| 4096x4096 | 9.60          | 0.45          | 21x     |

## Requirements

### Hardware
- **NVIDIA GPU** with CUDA Compute Capability 3.5 or higher
- **GPU Memory**: 2GB minimum, 4GB+ recommended
- **System RAM**: 8GB minimum

### Software
- **NVIDIA Driver**: Version 450.80.02 or higher
- **CUDA Toolkit**: 11.8 or 12.x
- **Docker** (if using containers): nvidia-container-toolkit

### Check GPU Compatibility

```bash
# Check if NVIDIA GPU is present
lspci | grep -i nvidia

# Check NVIDIA driver version
nvidia-smi

# Check CUDA version
nvcc --version
```

---

## Installation

### Option 1: Docker with GPU Support (Recommended)

#### 1. Install NVIDIA Container Toolkit

**Ubuntu/Debian:**
```bash
# Add repository
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
  sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

# Install
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# Restart Docker
sudo systemctl restart docker
```

#### 2. Build GPU-Enabled Docker Image

```bash
# Build image
docker build -f Dockerfile.gpu -t color-transfer:gpu .

# Verify GPU access
docker run --gpus all color-transfer:gpu python /app/gpu_check.py
```

#### 3. Run with GPU

```bash
# Run API with GPU
docker run --gpus all -p 8000:8000 color-transfer:gpu

# Run with specific GPU
docker run --gpus '"device=0"' -p 8000:8000 color-transfer:gpu

# Run with multiple GPUs
docker run --gpus 2 -p 8000:8000 color-transfer:gpu
```

### Option 2: Native Installation

#### 1. Install CUDA Toolkit

Download and install from: https://developer.nvidia.com/cuda-downloads

#### 2. Install PyTorch with CUDA

```bash
# For CUDA 11.8
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# For CUDA 12.1
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

# Verify installation
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

#### 3. Install Framework with GPU Support

```bash
pip install -e ".[gpu]"
```

---

## Usage

### Python API

```python
from color_transfer_framework import TransferEngine
import cv2

# Initialize engine with GPU
engine = TransferEngine(use_gpu=True)

# Load images
source = cv2.imread('source.jpg')
target = cv2.imread('target.jpg')

# Transfer with GPU acceleration
result = engine.transfer(source, target, algorithm='reinhard_lab', use_gpu=True)

# Save result
cv2.imwrite('result.jpg', result)
```

### REST API

```bash
# Transfer with GPU enabled
curl -X POST http://localhost:8000/api/v1/transfer \
  -F "source_image=@source.jpg" \
  -F "target_image=@target.jpg" \
  -F "algorithm=reinhard_lab" \
  -F "use_gpu=true"
```

### CLI

```bash
# Transfer with GPU
python -m color_transfer_framework.interface_layer.cli \
  transfer \
  --source source.jpg \
  --target target.jpg \
  --algorithm reinhard_lab \
  --use-gpu
```

---

## Docker Compose with GPU

Add to `docker-compose.yml`:

```yaml
services:
  api-gpu:
    build:
      context: .
      dockerfile: Dockerfile.gpu
      args:
        INTERFACE: api
    image: color-transfer:api-gpu
    container_name: color-transfer-api-gpu
    restart: unless-stopped
    environment:
      - INTERFACE=api
      - WORKERS=2  # Reduce workers with GPU
      - CUDA_VISIBLE_DEVICES=0
    ports:
      - "8001:8000"
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1  # Number of GPUs
              capabilities: [gpu]
    networks:
      - color-transfer-net
```

Start with:
```bash
docker-compose up -d api-gpu
```

---

## Kubernetes with GPU

Example deployment:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: color-transfer-gpu
spec:
  replicas: 1
  selector:
    matchLabels:
      app: color-transfer-gpu
  template:
    metadata:
      labels:
        app: color-transfer-gpu
    spec:
      containers:
      - name: api
        image: color-transfer:gpu
        ports:
        - containerPort: 8000
        resources:
          limits:
            nvidia.com/gpu: 1  # Request 1 GPU
          requests:
            nvidia.com/gpu: 1
        env:
        - name: INTERFACE
          value: "api"
        - name: WORKERS
          value: "2"
```

---

## Performance Tuning

### Optimal Settings

```python
# For maximum GPU utilization
config = {
    'use_gpu': True,
    'gpu_device': 0,           # GPU index
    'batch_size': 16,          # Batch multiple images
    'pin_memory': True,        # Faster data transfer
    'num_workers': 4,          # CPU threads for data loading
}

engine = TransferEngine(**config)
```

### Batch Processing

```python
from color_transfer_framework import TransferEngine
import cv2

engine = TransferEngine(use_gpu=True)

# Load multiple images
sources = [cv2.imread(f'source_{i}.jpg') for i in range(10)]
targets = [cv2.imread(f'target_{i}.jpg') for i in range(10)]

# Batch transfer (much faster than individual)
results = engine.transfer_batch(sources, targets, algorithm='reinhard_lab')

# Save results
for i, result in enumerate(results):
    cv2.imwrite(f'result_{i}.jpg', result)
```

### Memory Management

```python
import torch

# Clear GPU cache between large operations
torch.cuda.empty_cache()

# Monitor GPU memory
print(f"Allocated: {torch.cuda.memory_allocated(0) / 1e9:.2f}GB")
print(f"Reserved: {torch.cuda.memory_reserved(0) / 1e9:.2f}GB")
```

---

## Monitoring GPU Usage

### nvidia-smi

```bash
# Watch GPU usage in real-time
watch -n 1 nvidia-smi

# Log GPU usage
nvidia-smi --query-gpu=timestamp,name,temperature.gpu,utilization.gpu,utilization.memory,memory.total,memory.free,memory.used \
  --format=csv -l 1 > gpu_usage.csv
```

### Python Monitoring

```python
import torch

def print_gpu_stats():
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"Memory Allocated: {torch.cuda.memory_allocated(0)/1e9:.2f}GB")
        print(f"Memory Reserved: {torch.cuda.memory_reserved(0)/1e9:.2f}GB")
        print(f"Max Memory: {torch.cuda.max_memory_allocated(0)/1e9:.2f}GB")

print_gpu_stats()
```

---

## Troubleshooting

### GPU Not Detected

**Check CUDA availability:**
```python
import torch
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"CUDA version: {torch.version.cuda}")
print(f"GPU count: {torch.cuda.device_count()}")
if torch.cuda.is_available():
    print(f"GPU name: {torch.cuda.get_device_name(0)}")
```

**Common issues:**
- NVIDIA driver not installed: `sudo apt-get install nvidia-driver-535`
- CUDA version mismatch: Install matching PyTorch version
- nvidia-container-toolkit missing: Follow installation steps above

### Out of Memory (OOM) Errors

**Solutions:**
1. Reduce batch size
2. Reduce worker count
3. Process smaller images
4. Clear cache: `torch.cuda.empty_cache()`
5. Use mixed precision: `torch.cuda.amp.autocast()`

### Slow Performance

**Check:**
1. GPU is actually being used: `nvidia-smi`
2. Data transfer overhead: Use `pin_memory=True`
3. Worker count: Should be 2-4 for GPU
4. Batch size: Increase for better GPU utilization

### Docker GPU Issues

```bash
# Test GPU access in Docker
docker run --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi

# Check nvidia-container-toolkit
dpkg -l | grep nvidia-container-toolkit

# Restart Docker daemon
sudo systemctl restart docker
```

---

## Benchmarking

### Run Performance Test

```bash
# CPU baseline
python -m color_transfer_framework.interface_layer.cli \
  benchmark --algorithm reinhard_lab --size 2048 --iterations 10

# GPU comparison
python -m color_transfer_framework.interface_layer.cli \
  benchmark --algorithm reinhard_lab --size 2048 --iterations 10 --use-gpu
```

### Custom Benchmark

```python
import time
import numpy as np
from color_transfer_framework import TransferEngine

def benchmark(use_gpu=False, size=1024, iterations=10):
    engine = TransferEngine(use_gpu=use_gpu)

    # Generate test images
    source = np.random.rand(size, size, 3).astype(np.float32)
    target = np.random.rand(size, size, 3).astype(np.float32)

    # Warmup
    engine.transfer(source, target, algorithm='reinhard_lab')

    # Benchmark
    start = time.time()
    for _ in range(iterations):
        engine.transfer(source, target, algorithm='reinhard_lab')
    elapsed = time.time() - start

    print(f"{'GPU' if use_gpu else 'CPU'}: {elapsed/iterations:.4f}s per image")
    return elapsed / iterations

cpu_time = benchmark(use_gpu=False)
gpu_time = benchmark(use_gpu=True)
print(f"Speedup: {cpu_time/gpu_time:.2f}x")
```

---

## Best Practices

### Development
1. Test on CPU first, then enable GPU
2. Use smaller images for development
3. Monitor GPU memory usage
4. Clear cache between experiments

### Production
1. Use GPU-optimized Docker images
2. Set appropriate resource limits
3. Monitor GPU utilization (should be > 80%)
4. Use batch processing when possible
5. Implement graceful fallback to CPU

### Cost Optimization
1. Use CPU for small images (< 512x512)
2. Batch multiple requests
3. Use GPU only during peak hours
4. Share GPU across multiple containers
5. Auto-scale GPU instances

---

## Cloud Deployment

### AWS (with GPU)

```bash
# EC2 instance types: p2, p3, g4dn, g5
# Example: g4dn.xlarge (1x NVIDIA T4 GPU)

# Launch instance with NVIDIA AMI
# Install framework
git clone https://github.com/mgdavisxvs/ColorTransfer.git
cd ColorTransfer
docker build -f Dockerfile.gpu -t color-transfer:gpu .
docker run --gpus all -p 8000:8000 color-transfer:gpu
```

### Google Cloud (with GPU)

```bash
# Compute Engine with GPU
gcloud compute instances create color-transfer-gpu \
  --zone=us-central1-a \
  --machine-type=n1-standard-4 \
  --accelerator=type=nvidia-tesla-t4,count=1 \
  --image-family=common-cu113 \
  --image-project=deeplearning-platform-release

# Deploy container
gcloud builds submit --tag gcr.io/PROJECT-ID/color-transfer:gpu -f Dockerfile.gpu
gcloud run deploy --image gcr.io/PROJECT-ID/color-transfer:gpu --gpu 1
```

### Azure (with GPU)

```bash
# Container Instances with GPU
az container create \
  --resource-group myResourceGroup \
  --name color-transfer-gpu \
  --image color-transfer:gpu \
  --gpu-count 1 \
  --gpu-sku V100 \
  --cpu 4 \
  --memory 16
```

---

## Additional Resources

- **NVIDIA CUDA**: https://developer.nvidia.com/cuda-toolkit
- **PyTorch GPU**: https://pytorch.org/get-started/locally/
- **Docker GPU**: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/
- **Kubernetes GPU**: https://kubernetes.io/docs/tasks/manage-gpus/scheduling-gpus/

---

**Knuth's GPU Philosophy**: "Premature optimization is the root of all evil. Measure first, then optimize with GPU where it matters."

**Graham's Practical GPU**: "Use CPU for development and small batches. Use GPU for production and large-scale processing."

---

*Color Transfer Framework v2.0 - GPU Acceleration Guide*
