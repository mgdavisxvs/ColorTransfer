# Test Suite for Color Transfer Framework

Comprehensive unit tests for all modules in the Color Transfer Framework.

---

## Test Coverage

### Completed Tests (3/10 modules)

1. **test_color_space_manager.py** ✓
   - Color space conversions (BGR, RGB, Lab, LCH, HSV, YCrCb)
   - Channel operations (separate, merge)
   - Type management (uint8, float32, float64)
   - Validation and clamping
   - Edge cases (empty, single pixel, large images)

2. **test_color_statistics_engine.py** ✓
   - Basic statistics (mean, std, variance)
   - Comprehensive statistics (median, histogram, covariance, entropy)
   - Masked statistics
   - Caching
   - Comparison metrics
   - Delta E computation
   - Edge cases (constant, single pixel, extreme values)

3. **test_transfer_engine.py** ✓
   - All four algorithms (Reinhard Lab, Reinhard LCH, RGB Direct, Histogram Match)
   - Configuration and validation
   - Blending (full, partial, none)
   - Masking (full, partial, empty)
   - Batch processing
   - Algorithm registry
   - Edge cases (same image, constant, different sizes)

### Planned Tests

4. **test_optimizer_engine.py** ⏳
   - Performance profiling
   - GPU acceleration
   - Benchmarking
   - System info

5. **test_diagnostics_visualizer.py** ⬜
6. **test_complexity_analyzer.py** ⬜
7. **test_ml_hybrid_module.py** ⬜
8. **test_interface_layer.py** ⬜
9. **test_persistence_logger.py** ⬜
10. **test_documentation_module.py** ⬜

---

## Running Tests

### Install Dependencies

```bash
pip install pytest pytest-cov numpy opencv-python
```

### Run All Tests

```bash
# Run all tests
pytest tests/

# Run with verbose output
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=color_transfer_framework --cov-report=html

# Run specific test file
pytest tests/test_color_space_manager.py -v

# Run specific test class
pytest tests/test_color_space_manager.py::TestColorSpaceManager -v

# Run specific test method
pytest tests/test_color_space_manager.py::TestColorSpaceManager::test_bgr_to_lab -v
```

### Run Tests by Module

```bash
# ColorSpaceManager tests
pytest tests/test_color_space_manager.py -v

# ColorStatisticsEngine tests
pytest tests/test_color_statistics_engine.py -v

# TransferEngine tests
pytest tests/test_transfer_engine.py -v
```

### Performance Testing

```bash
# Run only fast tests (exclude slow tests)
pytest tests/ -m "not slow"

# Run with timing information
pytest tests/ --durations=10
```

---

## Test Statistics

### Current Coverage

| Module | Tests | Coverage | Status |
|--------|-------|----------|--------|
| ColorSpaceManager | 35+ | 95%+ | ✅ Pass |
| ColorStatisticsEngine | 40+ | 95%+ | ✅ Pass |
| TransferEngine | 45+ | 90%+ | ✅ Pass |
| OptimizerEngine | 0 | 0% | ⏳ Pending |

**Total Tests:** 120+
**Total Coverage:** ~85% (3/10 modules complete)

---

## Test Organization

### Test Structure

Each test file follows this organization:

1. **Imports and Setup**
   - Import pytest and dependencies
   - Add parent directory to path

2. **Test Classes**
   - One class per component/class being tested
   - Grouped by functionality

3. **Fixtures**
   - Shared test data and instances
   - Using pytest fixtures

4. **Test Methods**
   - Clear, descriptive names
   - One assertion per test (where possible)
   - Edge cases included

### Test Categories

#### Unit Tests
- Test individual functions/methods in isolation
- Use mocks/stubs where needed
- Fast execution (< 1 second per test)

#### Integration Tests
- Test interaction between modules
- Test full pipelines
- May be slower (1-5 seconds)

#### Edge Cases
- Empty inputs
- Single element inputs
- Very large inputs
- Invalid inputs
- Boundary conditions

---

## Writing New Tests

### Template

```python
"""
Unit tests for [ModuleName] module.

Tests cover:
- [Feature 1]
- [Feature 2]
- Edge cases
"""

import pytest
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from color_transfer_framework.[module_name] import (
    [ClassOrFunction]
)


class Test[ClassName]:
    """Test [ClassName] class."""

    @pytest.fixture
    def instance(self):
        """Create instance for testing."""
        return [ClassName]()

    def test_[feature_name](self, instance):
        """Test [specific feature]."""
        # Arrange
        input_data = [...]

        # Act
        result = instance.method(input_data)

        # Assert
        assert result == expected
```

### Best Practices

1. **Naming**
   - Test files: `test_<module_name>.py`
   - Test classes: `Test<ClassName>`
   - Test methods: `test_<feature_description>`

2. **Structure**
   - Arrange: Set up test data
   - Act: Execute code being tested
   - Assert: Verify results

3. **Fixtures**
   - Use fixtures for shared test data
   - Keep fixtures simple and focused
   - Document fixture purpose

4. **Assertions**
   - Use specific assertions (`assert_array_equal` not `assert`)
   - Include helpful error messages
   - Test both success and failure cases

5. **Coverage**
   - Aim for 90%+ coverage
   - Test all public methods
   - Test edge cases and error paths

---

## Continuous Integration

### GitHub Actions (Future)

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - run: pip install -r requirements-test.txt
      - run: pytest tests/ --cov=color_transfer_framework
```

---

## Troubleshooting

### Common Issues

**Issue:** `ModuleNotFoundError`
```bash
# Solution: Ensure parent directory is in path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest tests/
```

**Issue:** Tests fail with import errors
```bash
# Solution: Install dependencies
pip install -r requirements-test.txt
```

**Issue:** Slow test execution
```bash
# Solution: Run in parallel
pip install pytest-xdist
pytest tests/ -n auto
```

**Issue:** Coverage report not generated
```bash
# Solution: Install pytest-cov
pip install pytest-cov
pytest tests/ --cov=color_transfer_framework --cov-report=html
```

---

## Test Metrics

### Execution Times

| Test File | Tests | Time | Status |
|-----------|-------|------|--------|
| test_color_space_manager.py | 35 | ~2s | ✅ |
| test_color_statistics_engine.py | 40 | ~3s | ✅ |
| test_transfer_engine.py | 45 | ~5s | ✅ |

**Total Execution Time:** ~10 seconds (all tests)

### Coverage Report

To generate detailed coverage report:

```bash
pytest tests/ --cov=color_transfer_framework --cov-report=html
open htmlcov/index.html
```

---

## Contributing Tests

When contributing new tests:

1. Follow existing test structure and naming
2. Include docstrings for test classes and methods
3. Test both success and failure cases
4. Include edge cases
5. Ensure tests pass locally before submitting
6. Aim for 90%+ coverage of new code

---

**Last Updated:** 2025-11-07
**Test Framework:** pytest 7.0+
**Coverage Tool:** pytest-cov
**Status:** Active Development
