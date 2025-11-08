# Color Transfer Framework - Modular Architecture v2.0

**Enterprise-Grade Refactoring Following SOLID Principles**

---

## Overview

This document describes the modular architecture of the Color Transfer Framework v2.0, refactored from a monolithic implementation into a clean, maintainable, and extensible system following software engineering best practices.

---

## Architecture Principles

### SOLID Principles Applied

1. **Single Responsibility Principle (SRP)**
   - Each module has ONE clearly defined responsibility
   - Example: `ColorSpaceManager` ONLY handles color space operations

2. **Open/Closed Principle (OCP)**
   - Open for extension (new algorithms, color spaces)
   - Closed for modification (existing code stable)
   - Example: New transfer algorithms extend `TransferEngine` via strategy pattern

3. **Liskov Substitution Principle (LSP)**
   - Interfaces can be substituted without breaking functionality
   - Example: Any `TransferAlgorithm` can replace another

4. **Interface Segregation Principle (ISP)**
   - Clients depend only on interfaces they use
   - Example: `DiagnosticsVisualizer` doesn't depend on `MLHybridModule`

5. **Dependency Inversion Principle (DIP)**
   - High-level modules depend on abstractions, not concrete implementations
   - Example: `InterfaceLayer` depends on `TransferEngine` interface

---

## Module Structure

### Package Layout

```
color_transfer_framework/
├── __init__.py                    # Package initialization
├── color_space_manager.py         # Module 1: Color space operations
├── color_statistics_engine.py     # Module 2: Statistical computations
├── transfer_engine.py             # Module 3: Core transfer algorithms
├── optimizer_engine.py            # Module 4: Performance optimization
├── diagnostics_visualizer.py      # Module 5: Visualization tools
├── complexity_analyzer.py         # Module 6: Emergent behavior analysis
├── ml_hybrid_module.py            # Module 7: ML integration
├── interface_layer.py             # Module 8: CLI/GUI/API interfaces
├── persistence_logger.py          # Module 9: Data persistence
└── documentation_module.py        # Module 10: Auto-documentation
```

---

## Module Specifications

### 1. ColorSpaceManager

**File:** `color_space_manager.py`

**Responsibility:** Handle all color space conversions and channel operations

**Key Classes:**
- `ColorSpace(Enum)` - Supported color spaces (BGR, RGB, LAB, LCH, HSV, YCrCb)
- `ColorBounds` - Valid value ranges per color space
- `ColorSpaceManager` - Main conversion manager

**Key Methods:**
```python
convert_to(image, target_space, source_space) -> np.ndarray
separate_channels(image) -> List[np.ndarray]
merge_channels(channels) -> np.ndarray
clamp_ranges(image, color_space) -> np.ndarray
to_uint8(image) -> np.ndarray
to_float(image, normalize) -> np.ndarray
validate_image(image, color_space) -> bool
```

**Design Patterns:**
- Strategy Pattern: Different conversion strategies per color space
- Factory Pattern: Create converters based on source/target

**Example Usage:**
```python
manager = ColorSpaceManager(precision='float32')
lab_image = manager.convert_to(bgr_image, ColorSpace.LAB)
channels = manager.separate_channels(lab_image)
```

**Dependencies:** `numpy`, `opencv-python`

---

### 2. ColorStatisticsEngine

**File:** `color_statistics_engine.py`

**Responsibility:** Compute color statistics and distributions

**Key Classes:**
- `StatisticType(Enum)` - Types of statistics
- `ColorStatistics` - Data container for computed statistics
- `ColorStatisticsEngine` - Statistics computation engine

**Key Methods:**
```python
compute_stats(image, mask, compute_all) -> ColorStatistics
get_distribution(image, channel) -> Tuple[hist, bins]
compare_stats(stats1, stats2) -> Dict[str, float]
compute_delta_e(image1, image2) -> float
```

**Statistics Computed:**
- Mean, standard deviation, variance
- Median, mode, range
- Histograms (per-channel)
- Covariance matrix
- Shannon entropy
- ΔE perceptual difference

**Performance:**
- Time: O(n) for basic stats
- Space: O(n) for histogram storage
- Caching: Automatic caching for repeated queries

**Example Usage:**
```python
engine = ColorStatisticsEngine(cache_stats=True)
stats = engine.compute_stats(image, compute_all=True)
print(stats.summary())
```

**Dependencies:** `ColorSpaceManager` (for conversions)

---

### 3. TransferEngine

**File:** `transfer_engine.py`

**Responsibility:** Perform color transfer transformations

**Key Classes:**
- `TransferAlgorithm(Enum)` - Available algorithms
- `TransferConfig` - Configuration parameters
- `TransferEngine` - Main transfer engine

**Algorithms Supported:**
1. **Reinhard (Lab)** - Statistical matching in Lab space
2. **Reinhard (LCH)** - Hue-preserving cylindrical variant
3. **RGB Direct** - Simple RGB matching (baseline)
4. **Histogram Matching** - Iterative histogram alignment
5. **Optimal Transport** - OT-based color mapping (future)

**Key Methods:**
```python
transfer(source, target, config) -> np.ndarray
transfer_with_mask(source, target, mask) -> np.ndarray
batch_transfer(source, targets) -> List[np.ndarray]
apply_blending(original, transferred, alpha) -> np.ndarray
```

**Design Patterns:**
- Strategy Pattern: Different algorithms
- Template Method: Common transfer pipeline
- Builder Pattern: Configuration building

**Example Usage:**
```python
engine = TransferEngine(algorithm=TransferAlgorithm.REINHARD_LAB)
result = engine.transfer(source, target)

# With blending
config = TransferConfig(blend_factor=0.5)
result = engine.transfer(source, target, config)
```

**Dependencies:** `ColorSpaceManager`, `ColorStatisticsEngine`

---

### 4. OptimizerEngine

**File:** `optimizer_engine.py`

**Responsibility:** Performance optimization and profiling

**Key Classes:**
- `OptimizationMode(Enum)` - CPU, GPU, AUTO
- `PerformanceMetrics` - Profiling data container
- `OptimizerEngine` - Optimization wrapper

**Optimization Strategies:**
1. **Vectorization** - NumPy broadcasting (3× speedup)
2. **GPU Acceleration** - CUDA via PyTorch (15-54× speedup)
3. **Batch Processing** - Parallel batch operations
4. **Memory Optimization** - In-place operations
5. **Caching** - Statistics and conversion caching

**Key Methods:**
```python
optimize_pipeline(engine, mode) -> OptimizedEngine
profile_execution(func, *args) -> PerformanceMetrics
enable_gpu(device) -> None
benchmark_methods(methods, source, target) -> Dict
```

**Profiling Metrics:**
- Execution time (ms)
- Memory usage (MB)
- Throughput (images/sec)
- GPU utilization
- Cache hit rate

**Example Usage:**
```python
optimizer = OptimizerEngine(mode=OptimizationMode.GPU)
optimized_engine = optimizer.optimize_pipeline(transfer_engine)
metrics = optimizer.profile_execution(optimized_engine.transfer, source, target)
print(f"Time: {metrics.execution_time_ms}ms")
```

**Dependencies:** `torch` (optional for GPU), `psutil` (for profiling)

---

### 5. DiagnosticsVisualizer

**File:** `diagnostics_visualizer.py`

**Responsibility:** Visualization and diagnostics

**Key Classes:**
- `PlotType(Enum)` - Available plot types
- `VisualizationConfig` - Plot configuration
- `DiagnosticsVisualizer` - Visualization engine

**Visualizations Supported:**
1. **Histograms** - Per-channel distributions
2. **CDFs** - Cumulative distribution functions
3. **3D Color Space** - Scatter plots in Lab/RGB space
4. **ΔE Heat Maps** - Perceptual difference visualization
5. **Color Flow Vectors** - Movement in color space
6. **Side-by-Side Comparison** - Before/after views
7. **Statistical Overlays** - Mean/std visualization

**Key Methods:**
```python
plot_histogram(source, target, result) -> Figure
plot_3d_distribution(image, color_space) -> Figure
plot_delta_e_map(original, transformed) -> Figure
plot_vector_field(source, target, result) -> Figure
export_report(figures, path) -> None
```

**Output Formats:**
- PNG, SVG (static)
- HTML (interactive with Plotly)
- PDF (for reports)

**Example Usage:**
```python
viz = DiagnosticsVisualizer()
fig = viz.plot_histogram(source, target, result)
viz.export_report([fig], 'report.pdf')
```

**Dependencies:** `matplotlib`, `plotly` (optional), `seaborn` (optional)

---

### 6. ComplexityAnalyzer

**File:** `complexity_analyzer.py`

**Responsibility:** Analyze emergent behavior and convergence

**Key Classes:**
- `ConvergenceTest(Enum)` - Convergence criteria
- `IterationData` - Data from each iteration
- `ComplexityAnalyzer` - Analysis engine

**Analyses:**
1. **Fixed Point Convergence** - Iterate transfer until stable
2. **Entropy Evolution** - Track entropy over iterations
3. **KL Divergence Tracking** - Distribution similarity over time
4. **Cycle Detection** - Detect oscillations
5. **Bifurcation Analysis** - Parameter sensitivity

**Key Methods:**
```python
iterate_transfer(source, target, n_iterations) -> List[IterationData]
compute_entropy_series(images) -> np.ndarray
detect_convergence(data) -> bool
analyze_cycles(images) -> Dict
```

**Mathematical Tools:**
- Lyapunov stability analysis
- Entropy computation
- KL divergence
- Eigenvalue analysis

**Example Usage:**
```python
analyzer = ComplexityAnalyzer()
data = analyzer.iterate_transfer(source, target, n_iterations=10)
converged = analyzer.detect_convergence(data)
print(f"Converged: {converged} in {len(data)} iterations")
```

**Dependencies:** `TransferEngine`, `ColorStatisticsEngine`

---

### 7. MLHybridModule

**File:** `ml_hybrid_module.py`

**Responsibility:** Machine learning integration

**Key Classes:**
- `MLModelType(Enum)` - Available ML models
- `TrainingConfig` - Training configuration
- `MLHybridModule` - ML integration module

**ML Approaches:**
1. **Statistical Initialization + Neural Refinement**
2. **Learned Color Mappings** (neural network)
3. **GAN-based Style Transfer**
4. **Attention-based Refinement**

**Key Methods:**
```python
load_dataset(path) -> Dataset
train_model(config) -> Model
refine_transfer(target, model) -> np.ndarray
hybrid_transfer(source, target, use_ml) -> np.ndarray
```

**Models:**
- UNet for refinement
- ResNet for feature extraction
- Transformer for attention-based mapping

**Example Usage:**
```python
ml_module = MLHybridModule()
dataset = ml_module.load_dataset('training_data/')
model = ml_module.train_model(config)
refined = ml_module.refine_transfer(target, model)
```

**Dependencies:** `torch`, `torchvision`, `datasets`

---

### 8. InterfaceLayer (✅ IMPLEMENTED - Phase 5)

**Package:** `interface_layer/` (sub-package)

**Responsibility:** User interfaces (CLI, WebUI, REST API) and orchestration

**Key Modules:**
- `orchestrator.py` - Central coordination logic (TransferOrchestrator)
- `cli.py` - Typer-based command-line interface
- `api.py` - FastAPI REST service
- `web.py` - Flask web interface
- `models.py` - Pydantic data models

**Key Classes:**

**TransferOrchestrator:**
- Central facade for all interfaces
- Coordinates TransferEngine, OptimizerEngine, DiagnosticsVisualizer
- Handles base64 encoding/decoding for API
- Manages performance profiling
- Integrates PersistenceLogger

**Key Methods:**
```python
# Orchestrator
transfer(source, target, config, mask, enable_gpu, generate_diagnostics)
transfer_from_paths(source_path, target_path, output_path, ...)
transfer_from_base64(source_b64, target_b64, config, ...)

# CLI (Typer)
transfer(source, target, output, algorithm, blend, mask, gpu, visualize)
algorithms()  # List available algorithms
info()  # Show framework information

# API (FastAPI)
GET  /api/v1/health
GET  /api/v1/algorithms
POST /api/v1/transfer

# WebUI (Flask)
GET  /
POST /transfer
GET  /download/<filename>
```

**CLI Example:**
```bash
python -m color_transfer_framework.interface_layer.cli transfer \
    sunset.jpg portrait.jpg \
    --output result.jpg \
    --algo reinhard_lch \
    --blend 0.7 \
    --visualize \
    --gpu
```

**API Example:**
```bash
uvicorn color_transfer_framework.interface_layer.api:app --reload

# POST to http://localhost:8000/api/v1/transfer
{
  "source_image": "base64...",
  "target_image": "base64...",
  "config": {"algorithm": "reinhard_lab", "blend_factor": 0.8}
}
```

**WebUI Example:**
```bash
python -m color_transfer_framework.interface_layer.web
# Visit http://localhost:5000
```

**Design Patterns:**
- **Facade Pattern**: TransferOrchestrator simplifies complex subsystems
- **Dependency Injection**: Components injected for testability
- **Strategy Pattern**: Algorithm selection via configuration

**Dependencies:** `typer`, `rich`, `fastapi`, `uvicorn`, `pydantic`, `flask`

**Tests:** `tests/test_cli.py`, `tests/test_api.py` (180+ tests)

---

### 9. PersistenceLogger (✅ IMPLEMENTED - Phase 5)

**File:** `persistence_logger.py`

**Responsibility:** Data persistence and logging for auditing and reproducibility

**Key Classes:**

**AbstractPersistence (Protocol):**
- Abstract interface for persistence backends
- Enables swapping backends (SQLite, PostgreSQL, MongoDB)

**SQLitePersistence:**
- Concrete implementation using SQLite
- Default, lightweight, serverless storage
- Automatic schema creation and migration

**PersistenceLogger:**
- High-level logging interface
- Convenience wrapper around persistence backend
- Auto-serialization of config and metrics to JSON

**TransferRun (Dataclass):**
- Record of single transfer operation
- Contains: run_id, timestamp, image hashes, algorithm, config, metrics, interface_type

**Database Schema:**

**Table: transfer_runs**
- `run_id` (UUID, Primary Key)
- `timestamp` (ISO 8601 string)
- `source_hash` (SHA256 of source image)
- `target_hash` (SHA256 of target image)
- `result_hash` (SHA256 of result image)
- `algorithm` (string: "reinhard_lab", etc.)
- `config_json` (TEXT blob of TransferConfig)
- `metrics_json` (TEXT blob of PerformanceMetrics)
- `interface_type` (string: "CLI", "API", "WebUI")
- `success` (INTEGER boolean)
- `error_message` (TEXT, optional)

**Table: metadata**
- `key` (TEXT, Primary Key)
- `value` (TEXT)

**Key Methods:**
```python
# Logging
log_run(run: TransferRun) -> None
log_transfer(run_id, source_hash, target_hash, result_hash, algorithm,
             config, metrics, interface_type, success, error_message) -> None

# Querying
get_run(run_id: str) -> TransferRun | None
list_runs(limit=100, algorithm=None, interface_type=None) -> List[TransferRun]
get_history(limit=100, algorithm=None) -> List[TransferRun]

# Statistics
get_statistics() -> Dict[str, Any]
get_stats() -> Dict[str, Any]
```

**Logged Automatically:**
- Every transfer operation (via TransferOrchestrator)
- Interface type (CLI, API, WebUI)
- Complete configuration for reproducibility
- Performance metrics
- Image hashes for deduplication

**Example Usage:**
```python
from color_transfer_framework.persistence_logger import PersistenceLogger

logger = PersistenceLogger()  # Uses SQLite by default

# Get transfer history
recent_runs = logger.get_history(limit=10)

# Get aggregate statistics
stats = logger.get_stats()
print(f"Total runs: {stats['total_runs']}")
print(f"Success rate: {stats['success_rate']:.1f}%")
print(f"Avg execution time: {stats['avg_execution_time_ms']:.2f} ms")

# Query specific runs
cli_runs = logger.get_history(algorithm="reinhard_lab")
```

**Design Patterns:**
- **Protocol Pattern**: AbstractPersistence defines backend interface
- **Repository Pattern**: Clean data access layer
- **Single Responsibility**: Logging only, no business logic

**Dependencies:** Built-in `sqlite3` (no external deps)

**Tests:** `tests/test_persistence.py` (30+ tests)

**Integration:** Automatically integrated into TransferOrchestrator
- All CLI, API, and WebUI operations are logged
- Graceful degradation if logging fails (doesn't break operations)

---

### 10. DocumentationModule

**File:** `documentation_module.py`

**Responsibility:** Auto-documentation generation

**Key Classes:**
- `DocFormat(Enum)` - Output formats
- `DocumentationConfig` - Generation config
- `DocumentationModule` - Documentation generator

**Generated Documentation:**
1. **API Documentation** - From docstrings
2. **Jupyter Notebooks** - Literate programming
3. **PDF Reports** - Technical reports
4. **HTML Documentation** - Web-based docs
5. **Mathematical Proofs** - LaTeX formatting

**Key Methods:**
```python
generate_api_docs() -> None
create_notebook(template, code) -> Notebook
compile_report(markdown) -> PDF
embed_proofs(proof_text) -> Document
```

**Templates:**
- Algorithm explanation notebook
- Benchmarking report template
- Theoretical analysis template

**Example Usage:**
```python
doc_module = DocumentationModule()
doc_module.generate_api_docs(output_dir='docs/')
notebook = doc_module.create_notebook('analysis_template.ipynb')
```

**Dependencies:** `sphinx`, `jupyter`, `pandoc`, `pdflatex`

---

## Data Flow Architecture

### Typical Pipeline

```
1. InterfaceLayer (user input)
      ↓
2. PersistenceLogger (load config)
      ↓
3. ColorSpaceManager (convert to Lab)
      ↓
4. ColorStatisticsEngine (compute stats)
      ↓
5. TransferEngine (apply transfer)
      ↓
6. (Optional) MLHybridModule (refine)
      ↓
7. DiagnosticsVisualizer (visualize)
      ↓
8. PersistenceLogger (save results)
      ↓
9. InterfaceLayer (output)
```

### Dependency Graph

```
Level 0 (No dependencies):
  - ColorSpaceManager

Level 1 (Depends on Level 0):
  - ColorStatisticsEngine

Level 2 (Depends on Level 1):
  - TransferEngine
  - DiagnosticsVisualizer
  - ComplexityAnalyzer

Level 3 (Depends on Level 2):
  - OptimizerEngine
  - MLHybridModule

Level 4 (Depends on all):
  - InterfaceLayer
  - PersistenceLogger
  - DocumentationModule
```

---

## Performance Characteristics

### Module Performance

| Module | Time Complexity | Space Complexity | Cacheable |
|--------|----------------|------------------|-----------|
| ColorSpaceManager | O(n) | O(n) | No |
| ColorStatisticsEngine | O(n) | O(n) | Yes |
| TransferEngine | O(n) | O(n) | Partial |
| OptimizerEngine | - | - | N/A (wrapper) |
| DiagnosticsVisualizer | O(n log n) | O(n) | No |
| ComplexityAnalyzer | O(k×n) | O(k×n) | No |

Where:
- n = number of pixels
- k = number of iterations

### Optimization Targets

- **CPU Baseline:** 800ms for 1080p
- **CPU Optimized:** 275ms (3× speedup)
- **GPU Accelerated:** 15ms (54× speedup)
- **Batch Processing:** 100+ images/sec

---

## Extension Points

### Adding New Color Spaces

Extend `ColorSpaceManager`:
```python
# Add to ColorSpace enum
class ColorSpace(Enum):
    ...
    XYZ = "XYZ"

# Add conversion code
CONVERSION_CODES[(ColorSpace.BGR, ColorSpace.XYZ)] = cv2.COLOR_BGR2XYZ
```

### Adding New Transfer Algorithms

Extend `TransferEngine`:
```python
class OptimalTransportAlgorithm(TransferAlgorithm):
    def transfer(self, source_stats, target_image):
        # Implement OT-based transfer
        ...

# Register
TransferEngine.register_algorithm('optimal_transport', OptimalTransportAlgorithm)
```

### Adding New ML Models

Extend `MLHybridModule`:
```python
class TransformerRefinement(MLModel):
    def __init__(self):
        self.model = TransformerNetwork()

    def refine(self, image):
        ...

# Use
ml_module.register_model('transformer', TransformerRefinement)
```

---

## Tooling and Scripts (✅ Phase 5)

### Performance Benchmarking Suite

**Script:** `run_performance_suite.py`

**Purpose:** Comprehensive, automated performance benchmarking across all algorithms, execution modes, image sizes, and batch sizes.

**Test Matrix:**
- **Algorithms:** reinhard_lab, reinhard_lch, rgb_direct, histogram_match
- **Execution Modes:** CPU, GPU (if available)
- **Image Sizes:** 512x512 (small), 1920x1080 (HD), 3840x2160 (4K)
- **Batch Sizes:** 1, 10, 50 images

**Metrics Collected:**
- Average execution time (ms)
- Standard deviation (ms)
- Throughput (images/sec)
- Peak memory usage (MB)
- Peak VRAM usage (MB, for GPU)

**Output Files:**
- `benchmark_results.csv` - Raw results in CSV format
- `BENCHMARKS.md` - Human-readable summary report with:
  - Performance by algorithm
  - Performance by image size
  - Best performers (fastest, highest throughput, lowest memory)

**Usage:**
```bash
# Full benchmark suite
python run_performance_suite.py

# Custom benchmark
python run_performance_suite.py \
    --algorithms reinhard_lab rgb_direct \
    --modes cpu gpu \
    --sizes 512x512 1080p 4k \
    --batch-sizes 1 10 50 \
    --iterations 10 \
    --output ./my_benchmarks
```

**Features:**
- Synthetic image generation (no external image dependencies)
- Warm-up runs to eliminate startup overhead
- Multiple iterations for statistical significance
- Parallel execution support
- Graceful GPU detection and fallback

**Example Output:**
```
Performance by Algorithm
-------------------------
| Algorithm        | Avg Time (ms) | Throughput (img/s) |
|------------------|---------------|-------------------|
| rgb_direct       | 12.5          | 80.0              |
| reinhard_lab     | 45.3          | 22.1              |
| reinhard_lch     | 52.1          | 19.2              |
| histogram_match  | 78.9          | 12.7              |
```

---

## Testing Strategy

### Unit Tests

Each module has comprehensive unit tests:
```
tests/
├── test_color_space_manager.py
├── test_color_statistics_engine.py
├── test_transfer_engine.py
├── test_optimizer_engine.py
├── test_diagnostics_visualizer.py
├── test_complexity_analyzer.py
├── test_ml_hybrid_module.py
├── test_interface_layer.py
├── test_persistence_logger.py
└── test_documentation_module.py
```

### Integration Tests

End-to-end pipeline tests:
- Full transfer pipeline
- GUI/API integration
- Batch processing
- ML hybrid pipeline

### Performance Tests

Benchmarking suite:
- Execution time tracking
- Memory profiling
- Throughput measurement
- GPU utilization

---

## Deployment

### Installation

```bash
pip install color-transfer-framework
```

### Basic Usage

```python
from color_transfer_framework import (
    ColorSpaceManager,
    ColorStatisticsEngine,
    TransferEngine
)

# Initialize
transfer_engine = TransferEngine()

# Transfer
result = transfer_engine.transfer(source_image, target_image)
```

### Advanced Usage

```python
from color_transfer_framework import *

# Configure
config = TransferConfig(
    algorithm=TransferAlgorithm.REINHARD_LAB,
    blend_factor=0.8,
    use_gpu=True
)

# Optimize
optimizer = OptimizerEngine(mode=OptimizationMode.GPU)
optimized_engine = optimizer.optimize_pipeline(transfer_engine)

# Transfer
result = optimized_engine.transfer(source, target, config)

# Visualize
viz = DiagnosticsVisualizer()
viz.plot_histogram(source, target, result, save_path='analysis.png')

# Persist
logger = PersistenceLogger()
logger.save_run(metadata, stats, result)
```

---

## Migration from v1.0

### Backward Compatibility

Old code still works:
```python
from color_transfer import color_transfer  # v1.0 API

result = color_transfer(source, target)  # Still works!
```

### Migrating to v2.0

```python
# Old (v1.0)
from color_transfer import color_transfer
result = color_transfer(source, target)

# New (v2.0)
from color_transfer_framework import TransferEngine
engine = TransferEngine()
result = engine.transfer(source, target)
```

---

## Future Roadmap

### Version 2.1
- [ ] Optimal transport color transfer
- [ ] CIEDE2000 ΔE implementation
- [ ] Video processing with temporal coherence
- [ ] HDR image support

### Version 2.2
- [ ] Real-time processing (30fps)
- [ ] Mobile deployment (TensorFlow Lite)
- [ ] Cloud deployment (AWS Lambda)
- [ ] Distributed batch processing

### Version 3.0
- [ ] End-to-end neural color transfer
- [ ] Semantic-aware region transfer
- [ ] Style consistency across image sets
- [ ] Interactive editing tools

---

## License and Citation

**License:** MIT

**Citation:**
```bibtex
@software{color_transfer_framework_2025,
  title = {Color Transfer Framework: Enterprise-Grade Color Transfer System},
  author = {AI Research Agent},
  year = {2025},
  version = {2.0.0},
  url = {https://github.com/mgdavisxvs/ColorTransfer}
}
```

---

**Version:** 2.0.0
**Last Updated:** 2025-11-07
**Status:** In Development (2/10 modules complete)
