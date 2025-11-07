# Color Transfer Framework v2.0

**Enterprise-Grade Modular Architecture**

---

## Quick Start

```python
from color_transfer_framework import (
    ColorSpaceManager,
    ColorStatisticsEngine,
    TransferEngine  # Coming soon
)

# Color space conversion
manager = ColorSpaceManager(precision='float32')
lab_image = manager.convert_to(bgr_image, ColorSpace.LAB)

# Statistics computation
stats_engine = ColorStatisticsEngine()
stats = stats_engine.compute_stats(lab_image, compute_all=True)
print(stats.summary())

# Color transfer (v2.0 - in development)
# transfer_engine = TransferEngine()
# result = transfer_engine.transfer(source, target)
```

---

## Architecture Overview

This framework follows SOLID principles with 10 specialized modules:

### Core Modules (Implemented)

1. **ColorSpaceManager** ✓
   - Color space conversions (BGR ↔ Lab ↔ LCH ↔ HSV ↔ YCrCb)
   - Channel operations (separate, merge)
   - Type management (uint8, float32, float64)

2. **ColorStatisticsEngine** ✓
   - Statistical computations (mean, std, variance)
   - Histogram and entropy analysis
   - Perceptual metrics (ΔE)

### Core Modules (Planned)

3. **TransferEngine** (In Development)
   - Core color transfer algorithms
   - Multiple algorithm support (Reinhard, LCH, RGB, Histogram Matching)
   - Blending and masking

4. **OptimizerEngine** (Planned)
   - GPU acceleration (PyTorch/CUDA)
   - Performance profiling
   - Batch processing

5. **DiagnosticsVisualizer** (Planned)
   - Histogram plots
   - 3D color space visualization
   - ΔE heat maps

### Advanced Modules (Planned)

6. **ComplexityAnalyzer** - Emergent behavior analysis
7. **MLHybridModule** - Machine learning integration
8. **InterfaceLayer** - CLI/GUI/API interfaces
9. **PersistenceLogger** - Data persistence and logging
10. **DocumentationModule** - Auto-documentation generation

---

## Design Principles

- **Single Responsibility**: Each module has ONE clearly defined purpose
- **Dependency Inversion**: Depend on abstractions, not implementations
- **Open/Closed**: Open for extension, closed for modification
- **Separation of Concerns**: Clear boundaries between modules
- **Performance**: Vectorized operations, GPU support, caching

---

## Module Dependencies

```
Level 0: ColorSpaceManager (no dependencies)
Level 1: ColorStatisticsEngine (uses ColorSpaceManager)
Level 2: TransferEngine, DiagnosticsVisualizer (use Level 1)
Level 3: OptimizerEngine, MLHybridModule (use Level 2)
Level 4: InterfaceLayer, PersistenceLogger (use all)
```

---

## Documentation

See `../ARCHITECTURE.md` for complete specification including:
- Detailed module responsibilities
- API documentation
- Design patterns used
- Extension points
- Performance characteristics
- Migration guide from v1.0

---

## Current Status

**Version:** 2.0.0-alpha
**Status:** Active Development

**Completed:**
- ✓ Architecture specification (ARCHITECTURE.md)
- ✓ ColorSpaceManager (100%)
- ✓ ColorStatisticsEngine (100%)
- ✓ Package structure

**In Progress:**
- ⏳ TransferEngine
- ⏳ OptimizerEngine

**Planned:**
- ⬜ DiagnosticsVisualizer
- ⬜ ComplexityAnalyzer
- ⬜ MLHybridModule
- ⬜ InterfaceLayer
- ⬜ PersistenceLogger
- ⬜ DocumentationModule

---

## Examples

### Color Space Conversion

```python
from color_transfer_framework.color_space_manager import (
    ColorSpaceManager,
    ColorSpace
)

manager = ColorSpaceManager()

# Convert BGR to Lab
lab = manager.convert_to(bgr_img, ColorSpace.LAB)

# Convert Lab to LCH (cylindrical)
lch = manager.convert_to(lab, ColorSpace.LCH, source_space=ColorSpace.LAB)

# Separate channels
L, C, H = manager.separate_channels(lch)

# Merge back
lch_reconstructed = manager.merge_channels([L, C, H])
```

### Statistical Analysis

```python
from color_transfer_framework.color_statistics_engine import (
    ColorStatisticsEngine,
    compute_image_stats
)

# Quick stats
stats = compute_image_stats(image)
print(f"Mean: {stats.mean}")
print(f"Std: {stats.std}")

# Comprehensive analysis
engine = ColorStatisticsEngine()
full_stats = engine.compute_stats(image, compute_all=True)
print(full_stats.summary())

# Compare two images
stats1 = engine.compute_stats(image1)
stats2 = engine.compute_stats(image2)
comparison = engine.compare_stats(stats1, stats2)
print(f"Mean error: {comparison['mean_error']}")
print(f"KL divergence: {comparison.get('kl_divergence', 'N/A')}")
```

---

## Testing

```bash
# Run unit tests
pytest tests/test_color_space_manager.py
pytest tests/test_color_statistics_engine.py

# Run all tests
pytest tests/

# With coverage
pytest --cov=color_transfer_framework tests/
```

---

## Contributing

This is an active refactoring project. Contributions welcome!

**Priority Areas:**
1. TransferEngine implementation
2. Unit tests for existing modules
3. Performance benchmarks
4. Documentation improvements

---

## License

MIT License - See LICENSE file

---

## Authors

- **AI Research Agent** - Initial architecture and implementation
- **Contributors** - See CONTRIBUTORS.md

---

## Changelog

### v2.0.0-alpha (2025-11-07)
- Initial modular architecture
- Implemented ColorSpaceManager
- Implemented ColorStatisticsEngine
- Created comprehensive ARCHITECTURE.md specification

### v1.0.0 (2025-11-07)
- Original monolithic implementation
- See `../COMPREHENSIVE_ANALYSIS.md` for v1.0 documentation

---

**For complete documentation, see:**
- `../ARCHITECTURE.md` - Complete architectural specification
- `../COMPREHENSIVE_ANALYSIS.md` - Theoretical foundations (v1.0)
- `../README_ANALYSIS.md` - Quick start guide (v1.0)
