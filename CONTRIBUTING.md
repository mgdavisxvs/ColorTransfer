# Contributing to Color Transfer Framework

Thank you for your interest in contributing to the Color Transfer Framework! This document provides guidelines and instructions for contributing.

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Setup](#development-setup)
4. [How to Contribute](#how-to-contribute)
5. [Coding Standards](#coding-standards)
6. [Testing Requirements](#testing-requirements)
7. [Pull Request Process](#pull-request-process)
8. [Reporting Issues](#reporting-issues)
9. [Community](#community)

---

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inclusive environment for all contributors, regardless of age, body size, disability, ethnicity, gender identity and expression, level of experience, nationality, personal appearance, race, religion, or sexual identity and orientation.

### Expected Behavior

- Be respectful and considerate
- Use welcoming and inclusive language
- Accept constructive criticism gracefully
- Focus on what is best for the community
- Show empathy towards other community members

### Unacceptable Behavior

- Harassment, trolling, or discriminatory comments
- Publishing others' private information
- Personal attacks or insults
- Spam or off-topic comments
- Other unprofessional conduct

---

## Getting Started

### Prerequisites

- Python 3.9+ (3.11 recommended)
- Docker and Docker Compose (for testing deployment)
- Git
- Basic knowledge of color transfer algorithms (helpful but not required)

### Quick Start for Contributors

```bash
# 1. Fork the repository
# Click "Fork" on GitHub

# 2. Clone your fork
git clone https://github.com/YOUR_USERNAME/ColorTransfer.git
cd ColorTransfer

# 3. Add upstream remote
git remote add upstream https://github.com/mgdavisxvs/ColorTransfer.git

# 4. Create development environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 5. Install development dependencies
make install-dev
# Or: pip install -e ".[dev,test]"

# 6. Run tests to verify setup
make test-quick

# 7. Create a feature branch
git checkout -b feature/your-feature-name
```

---

## Development Setup

### Full Development Environment

```bash
# Install all dependencies (development, testing, documentation)
make install-all

# Or manually
pip install -r requirements.txt
pip install -r requirements-test.txt
pip install -e ".[dev,test,docs]"

# Install pre-commit hooks (recommended)
pip install pre-commit
pre-commit install

# Install Playwright browsers (for integration tests)
playwright install chromium

# Set up environment variables
cp .env.example .env
# Edit .env as needed
```

### Using Docker for Development

```bash
# Start all services
make docker-up

# View logs
make docker-logs

# Access containers
make docker-shell-api  # Enter API container
make docker-shell-web  # Enter Web container

# Run tests in Docker
docker-compose exec api pytest tests/ -v
```

### IDE Setup

#### VSCode (Recommended)

Install recommended extensions:
- Python (ms-python.python)
- Pylance (ms-python.vscode-pylance)
- Black Formatter (ms-python.black-formatter)
- isort (ms-python.isort)
- Docker (ms-azuretools.vscode-docker)

#### PyCharm

1. Open project in PyCharm
2. Configure Python interpreter (select venv)
3. Enable pytest as test runner
4. Configure code style to use Black

---

## How to Contribute

### Types of Contributions

We welcome various types of contributions:

1. **Bug Fixes**: Fix existing issues
2. **New Features**: Add new algorithms or functionality
3. **Documentation**: Improve docs, guides, examples
4. **Tests**: Add or improve test coverage
5. **Performance**: Optimize existing code
6. **Refactoring**: Improve code structure
7. **DevOps**: Enhance CI/CD, deployment, monitoring

### Finding Something to Work On

1. **Good First Issues**: Look for issues labeled `good first issue`
2. **Help Wanted**: Check issues labeled `help wanted`
3. **Roadmap**: See planned features in [CHANGELOG.md](CHANGELOG.md)
4. **Bugs**: Fix reported bugs in GitHub Issues

### Before You Start

1. **Check existing issues**: Avoid duplicate work
2. **Open an issue**: Discuss significant changes first
3. **Get feedback**: Comment on the issue to claim it
4. **Small PRs**: Keep changes focused and manageable

---

## Coding Standards

### Code Style

We follow **PEP 8** with some modifications:

- **Line length**: 100 characters (not 79)
- **Indentation**: 4 spaces (no tabs)
- **String quotes**: Prefer double quotes `"` over single `'`
- **Imports**: Sorted with isort

### Code Formatting

We use automated formatters:

```bash
# Format code with Black
make format

# Or manually
black color_transfer_framework/ tests/
isort color_transfer_framework/ tests/
```

### Linting

All code must pass linting:

```bash
# Run all linters
make lint

# Individual linters
flake8 color_transfer_framework/
pylint color_transfer_framework/
mypy color_transfer_framework/
```

### Type Hints

**Required** for all public functions:

```python
# Good
def transfer_color(
    source: np.ndarray,
    target: np.ndarray,
    algorithm: str = "reinhard_lab"
) -> np.ndarray:
    """Transfer color from target to source."""
    ...

# Bad
def transfer_color(source, target, algorithm="reinhard_lab"):
    ...
```

### Documentation

**All public functions, classes, and modules** must have docstrings:

```python
def calculate_statistics(image: np.ndarray) -> dict:
    """
    Calculate statistical properties of an image.

    Args:
        image: Input image as numpy array (H, W, C)

    Returns:
        Dictionary containing:
            - mean: Mean value per channel
            - std: Standard deviation per channel
            - min: Minimum value per channel
            - max: Maximum value per channel

    Raises:
        ValueError: If image has invalid shape

    Example:
        >>> image = np.random.rand(100, 100, 3)
        >>> stats = calculate_statistics(image)
        >>> print(stats['mean'])
        [0.5, 0.5, 0.5]
    """
    if len(image.shape) != 3:
        raise ValueError(f"Expected 3D image, got shape {image.shape}")
    ...
```

### Naming Conventions

```python
# Classes: PascalCase
class ColorTransferEngine:
    ...

# Functions and variables: snake_case
def calculate_mean_std(image):
    ...

# Constants: UPPER_SNAKE_CASE
MAX_IMAGE_SIZE = 4096

# Private: Leading underscore
def _internal_helper():
    ...
```

### File Organization

```
color_transfer_framework/
├── __init__.py           # Package initialization
├── transfer_engine.py    # Main transfer logic
├── color_space_manager.py
├── interface_layer/      # Interfaces
│   ├── __init__.py
│   ├── api.py           # FastAPI
│   ├── web.py           # Flask Web UI
│   └── cli.py           # CLI
└── tests/               # Tests mirror source structure
    ├── test_transfer_engine.py
    └── test_color_space_manager.py
```

---

## Testing Requirements

### Test Coverage Requirements

- **Minimum coverage**: 80%
- **New code**: Must include tests
- **Bug fixes**: Include regression test

### Running Tests

```bash
# Quick tests (2-3 minutes)
make test-quick

# Full test suite with coverage
make test-full

# Specific test types
make test-unit           # Unit tests only
make test-integration    # Integration tests
make test-contract       # API contract tests

# Watch mode (re-run on file changes)
pytest-watch tests/
```

### Writing Tests

Use pytest conventions:

```python
import pytest
from color_transfer_framework import TransferEngine

class TestTransferEngine:
    """Tests for TransferEngine class."""

    def test_reinhard_lab_transfer(self):
        """Test Reinhard LAB algorithm produces valid output."""
        # Arrange
        engine = TransferEngine()
        source = np.random.rand(100, 100, 3)
        target = np.random.rand(100, 100, 3)

        # Act
        result = engine.transfer(source, target, algorithm='reinhard_lab')

        # Assert
        assert result.shape == source.shape
        assert result.dtype == np.float64
        assert 0 <= result.min() <= 1
        assert 0 <= result.max() <= 1

    def test_invalid_algorithm_raises_error(self):
        """Test invalid algorithm name raises ValueError."""
        engine = TransferEngine()
        source = np.random.rand(100, 100, 3)
        target = np.random.rand(100, 100, 3)

        with pytest.raises(ValueError, match="Unknown algorithm"):
            engine.transfer(source, target, algorithm='invalid')
```

### Test Fixtures

Use fixtures for reusable test data:

```python
@pytest.fixture
def sample_image():
    """Provide a sample test image."""
    return np.random.rand(100, 100, 3).astype(np.float64)

@pytest.fixture
def transfer_engine():
    """Provide a configured TransferEngine."""
    return TransferEngine(config={'clip_output': True})

def test_with_fixtures(sample_image, transfer_engine):
    result = transfer_engine.transfer(sample_image, sample_image)
    assert result is not None
```

---

## Pull Request Process

### Before Submitting

1. **Update your branch**:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Run all checks**:
   ```bash
   make ci-local  # Simulates CI pipeline
   ```

3. **Update documentation**:
   - Update docstrings
   - Update README if needed
   - Add entry to CHANGELOG.md

4. **Commit messages**:
   Follow conventional commits format:
   ```
   type(scope): brief description

   Longer description if needed.

   Fixes #123
   ```

   Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

   Examples:
   ```
   feat(api): add new histogram matching endpoint
   fix(transfer): correct LAB color space conversion
   docs(readme): update installation instructions
   test(engine): add tests for blend factor validation
   ```

### Submitting Pull Request

1. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Open Pull Request** on GitHub:
   - Use a clear, descriptive title
   - Reference related issues (`Fixes #123`, `Closes #456`)
   - Describe what changed and why
   - Include screenshots/examples if applicable

3. **PR Template**:
   ```markdown
   ## Description
   Brief description of changes

   ## Type of Change
   - [ ] Bug fix
   - [ ] New feature
   - [ ] Documentation update
   - [ ] Performance improvement
   - [ ] Code refactoring

   ## Checklist
   - [ ] Code follows style guidelines
   - [ ] Self-review completed
   - [ ] Comments added for complex code
   - [ ] Documentation updated
   - [ ] Tests added/updated
   - [ ] All tests passing
   - [ ] No new warnings

   ## Related Issues
   Fixes #123

   ## Testing
   Describe testing performed

   ## Screenshots (if applicable)
   ```

### Review Process

1. **Automated checks**: CI must pass
2. **Code review**: Maintainer review required
3. **Feedback**: Address review comments
4. **Approval**: Needs 1 approval to merge
5. **Merge**: Squash and merge (usually)

### After Merge

1. **Delete branch**: Clean up after merge
2. **Update local**:
   ```bash
   git checkout main
   git pull upstream main
   ```

---

## Reporting Issues

### Bug Reports

Use the bug report template:

```markdown
**Describe the bug**
Clear description of the issue

**To Reproduce**
Steps to reproduce:
1. Call function X with parameters Y
2. Observe result Z

**Expected behavior**
What you expected to happen

**Actual behavior**
What actually happened

**Environment**
- OS: [e.g., Ubuntu 22.04]
- Python version: [e.g., 3.11.5]
- Framework version: [e.g., 2.0.0]

**Additional context**
- Error messages
- Stack traces
- Screenshots
```

### Feature Requests

```markdown
**Is your feature request related to a problem?**
Description of the problem

**Describe the solution you'd like**
What you want to happen

**Describe alternatives considered**
Other approaches you've thought about

**Additional context**
Use cases, examples, mockups
```

---

## Community

### Communication Channels

- **GitHub Issues**: Bug reports, feature requests
- **GitHub Discussions**: Questions, ideas, showcase
- **Pull Requests**: Code contributions

### Recognition

Contributors will be recognized in:
- README.md contributors section
- Release notes
- CHANGELOG.md

### Getting Help

- **Documentation**: Check README.md, DEPLOYMENT.md, OPERATIONS.md
- **Examples**: See tests/ for usage examples
- **Issues**: Search existing issues first
- **Discussions**: Ask questions in GitHub Discussions

---

## Additional Resources

- **Architecture**: See [ARCHITECTURE.md](ARCHITECTURE.md)
- **Deployment**: See [DEPLOYMENT.md](DEPLOYMENT.md)
- **Operations**: See [OPERATIONS.md](OPERATIONS.md)
- **Testing**: See [tests/TESTING_GUIDE.md](tests/TESTING_GUIDE.md)
- **Changelog**: See [CHANGELOG.md](CHANGELOG.md)

---

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (MIT License).

---

## Knuth's Contribution Philosophy

> "The best way to contribute is to make the code so clear that it needs no comments,
> but write excellent comments anyway." - Adapted from Donald Knuth

Focus on:
1. **Clarity**: Write code that's easy to understand
2. **Correctness**: Ensure mathematical/algorithmic accuracy
3. **Performance**: Profile before optimizing
4. **Documentation**: Document the "why", not just the "what"

## Graham's Practical Approach

> "A good contribution solves a real problem, is well-tested, and makes the project better."

Remember:
1. **Start small**: Small, focused PRs are easier to review
2. **Test thoroughly**: Tests give confidence in changes
3. **Document clearly**: Help others understand your work
4. **Be patient**: Reviews take time, be responsive to feedback
5. **Have fun**: Enjoy the process of contributing!

---

**Thank you for contributing to the Color Transfer Framework!** 🎨
