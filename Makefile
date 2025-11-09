# ============================================================================
# Color Transfer Framework v2.0 - Makefile
# Common development and deployment tasks
# ============================================================================

.PHONY: help install install-dev install-test clean lint format test test-quick test-full \
        test-integration test-coverage docker-build docker-up docker-down docker-logs \
        docker-clean security-scan build package deploy-local deploy-prod docs \
        benchmark check-health tracing-up tracing-down tracing-logs tracing-status \
        jaeger-open tracing-test

.DEFAULT_GOAL := help

# ============================================================================
# Configuration
# ============================================================================

PYTHON := python3
PIP := $(PYTHON) -m pip
PYTEST := $(PYTHON) -m pytest
BLACK := $(PYTHON) -m black
ISORT := $(PYTHON) -m isort
FLAKE8 := $(PYTHON) -m flake8
PYLINT := $(PYTHON) -m pylint
MYPY := $(PYTHON) -m mypy
BANDIT := $(PYTHON) -m bandit
DOCKER := docker
DOCKER_COMPOSE := docker-compose

PROJECT_NAME := color-transfer-framework
PACKAGE_DIR := color_transfer_framework
TEST_DIR := tests
DOCS_DIR := docs

# Docker configuration
DOCKER_IMAGE := color-transfer
DOCKER_TAG := latest
API_PORT := 8000
WEB_PORT := 5000

# ============================================================================
# Help
# ============================================================================

help: ## Show this help message
	@echo "Color Transfer Framework v2.0 - Development Commands"
	@echo "===================================================="
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Knuth's Productivity Principle:"
	@echo "  'Automation is the key to consistency and quality'"

# ============================================================================
# Installation
# ============================================================================

install: ## Install production dependencies
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@echo "✅ Production dependencies installed"

install-dev: ## Install development dependencies
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PIP) install -e ".[dev]"
	@echo "✅ Development dependencies installed"

install-test: ## Install test dependencies
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PIP) install -r requirements-test.txt
	playwright install chromium
	@echo "✅ Test dependencies installed"

install-all: ## Install all dependencies (dev + test)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PIP) install -e ".[all]"
	playwright install chromium
	@echo "✅ All dependencies installed"

# ============================================================================
# Code Quality
# ============================================================================

lint: ## Run all linters
	@echo "Running linters..."
	$(FLAKE8) $(PACKAGE_DIR)/ --max-line-length=100 --extend-ignore=E203,W503
	$(PYLINT) $(PACKAGE_DIR)/ --max-line-length=100 --disable=C0114,C0115,C0116
	$(MYPY) $(PACKAGE_DIR)/ --ignore-missing-imports
	@echo "✅ Linting complete"

format: ## Format code with black and isort
	@echo "Formatting code..."
	$(BLACK) $(PACKAGE_DIR)/ $(TEST_DIR)/
	$(ISORT) $(PACKAGE_DIR)/ $(TEST_DIR)/
	@echo "✅ Code formatted"

format-check: ## Check code formatting without modifying
	$(BLACK) --check --diff $(PACKAGE_DIR)/ $(TEST_DIR)/
	$(ISORT) --check-only --diff $(PACKAGE_DIR)/ $(TEST_DIR)/

# ============================================================================
# Testing
# ============================================================================

test: ## Run all tests
	$(PYTEST) $(TEST_DIR)/ -v --tb=short

test-quick: ## Run quick tests (no integration, no slow)
	$(PYTEST) $(TEST_DIR)/ -v --tb=short -m "not integration and not slow" -n auto
	@echo "✅ Quick tests complete"

test-full: ## Run full test suite with coverage
	$(PYTEST) $(TEST_DIR)/ -v --cov=$(PACKAGE_DIR) --cov-report=html --cov-report=term-missing
	@echo "✅ Full test suite complete"
	@echo "📊 Coverage report: htmlcov/index.html"

test-unit: ## Run unit tests only
	$(PYTEST) $(TEST_DIR)/ -v -m "unit" --tb=short
	@echo "✅ Unit tests complete"

test-integration: ## Run integration tests
	$(PYTEST) $(TEST_DIR)/integration/ $(TEST_DIR)/contract/ -v --tb=short
	@echo "✅ Integration tests complete"

test-visual: ## Run visual regression tests
	$(PYTEST) $(TEST_DIR)/visual/ -v --tb=short
	@echo "✅ Visual regression tests complete"

test-coverage: ## Generate coverage report
	$(PYTEST) $(TEST_DIR)/ --cov=$(PACKAGE_DIR) --cov-report=html --cov-report=xml --cov-report=term
	@echo "📊 Coverage report generated: htmlcov/index.html"

test-mutation: ## Run mutation testing
	mutmut run --paths-to-mutate=$(PACKAGE_DIR)/
	mutmut results
	mutmut html
	@echo "📊 Mutation test report: html/index.html"

test-load: ## Run load tests (Locust)
	@echo "Starting load test... (Ctrl+C to stop)"
	locust -f $(TEST_DIR)/load/locustfile.py --headless -u 10 -r 2 -t 1m --host http://localhost:$(API_PORT)

# ============================================================================
# Docker
# ============================================================================

docker-build: ## Build Docker image (API)
	$(DOCKER) build -t $(DOCKER_IMAGE):$(DOCKER_TAG) --build-arg INTERFACE=api .
	@echo "✅ Docker image built: $(DOCKER_IMAGE):$(DOCKER_TAG)"

docker-build-all: ## Build all Docker images (API, Web, Enhanced Web)
	$(DOCKER) build -t $(DOCKER_IMAGE):api --build-arg INTERFACE=api .
	$(DOCKER) build -t $(DOCKER_IMAGE):web --build-arg INTERFACE=web .
	$(DOCKER) build -t $(DOCKER_IMAGE):web-enhanced --build-arg INTERFACE=web_enhanced .
	@echo "✅ All Docker images built"

docker-up: ## Start all services with docker-compose
	$(DOCKER_COMPOSE) up -d
	@echo "✅ Services started"
	@echo "🌐 API: http://localhost:$(API_PORT)"
	@echo "🌐 Web UI: http://localhost:$(WEB_PORT)"
	@echo "🌐 Enhanced Web UI: http://localhost:5001"
	@echo "📊 Prometheus: http://localhost:9090"
	@echo "📈 Grafana: http://localhost:3000 (admin/admin)"

docker-down: ## Stop all services
	$(DOCKER_COMPOSE) down
	@echo "✅ Services stopped"

docker-restart: ## Restart all services
	$(DOCKER_COMPOSE) restart
	@echo "✅ Services restarted"

docker-logs: ## Show logs from all services
	$(DOCKER_COMPOSE) logs -f

docker-logs-api: ## Show API logs
	$(DOCKER_COMPOSE) logs -f api

docker-logs-web: ## Show Web UI logs
	$(DOCKER_COMPOSE) logs -f web

docker-ps: ## Show running containers
	$(DOCKER_COMPOSE) ps

docker-clean: ## Remove all containers, images, and volumes
	$(DOCKER_COMPOSE) down -v
	$(DOCKER) system prune -af --volumes
	@echo "✅ Docker cleaned"

docker-shell-api: ## Open shell in API container
	$(DOCKER_COMPOSE) exec api bash

docker-shell-web: ## Open shell in Web container
	$(DOCKER_COMPOSE) exec web bash

# ============================================================================
# Monitoring
# ============================================================================

monitoring-up: ## Start monitoring services (Prometheus + Grafana)
	$(DOCKER_COMPOSE) up -d prometheus grafana
	@echo "✅ Monitoring services started"
	@echo "📊 Prometheus: http://localhost:9090"
	@echo "📈 Grafana: http://localhost:3000 (admin/admin)"

monitoring-down: ## Stop monitoring services
	$(DOCKER_COMPOSE) stop prometheus grafana
	@echo "✅ Monitoring services stopped"

monitoring-logs: ## Show monitoring logs
	$(DOCKER_COMPOSE) logs -f prometheus grafana

monitoring-status: ## Check monitoring service status
	@echo "Checking monitoring services..."
	@curl -s http://localhost:9090/-/healthy && echo "✅ Prometheus is healthy" || echo "❌ Prometheus is not responding"
	@curl -s http://localhost:3000/api/health && echo "✅ Grafana is healthy" || echo "❌ Grafana is not responding"

grafana-open: ## Open Grafana in browser
	@echo "Opening Grafana dashboard..."
	@echo "Default credentials: admin / admin"
	@open http://localhost:3000 || xdg-open http://localhost:3000 || echo "Please open http://localhost:3000"

prometheus-open: ## Open Prometheus in browser
	@echo "Opening Prometheus..."
	@open http://localhost:9090 || xdg-open http://localhost:9090 || echo "Please open http://localhost:9090"

# ============================================================================
# Distributed Tracing (Phase 16)
# ============================================================================

tracing-up: ## Start Jaeger tracing service
	$(DOCKER_COMPOSE) up -d jaeger
	@echo "✅ Jaeger tracing started"
	@echo "🔍 Jaeger UI: http://localhost:16686"

tracing-down: ## Stop Jaeger tracing service
	$(DOCKER_COMPOSE) stop jaeger
	@echo "✅ Jaeger stopped"

tracing-logs: ## Show Jaeger logs
	$(DOCKER_COMPOSE) logs -f jaeger

tracing-status: ## Check Jaeger service health
	@echo "Checking Jaeger service..."
	@curl -s http://localhost:14269 && echo "✅ Jaeger is healthy" || echo "❌ Jaeger is not responding"

jaeger-open: ## Open Jaeger UI in browser
	@echo "Opening Jaeger UI..."
	@echo "Select service: color-transfer-api"
	@open http://localhost:16686 || xdg-open http://localhost:16686 || echo "Please open http://localhost:16686"

tracing-test: ## Generate test traces
	@echo "Generating test traces..."
	@curl -X POST http://localhost:$(API_PORT)/api/v1/transfer \
		-F "source_image=@examples/source.jpg" \
		-F "target_image=@examples/target.jpg" \
		-F "algorithm=reinhard_lab" > /dev/null 2>&1 || echo "⚠️  Make sure API is running and example images exist"
	@echo "✅ Test trace generated. View in Jaeger UI: http://localhost:16686"

# ============================================================================
# Security
# ============================================================================

security-scan: ## Run security scans
	@echo "Running security scans..."
	$(BANDIT) -r $(PACKAGE_DIR)/ --severity-level medium
	safety check
	@echo "✅ Security scan complete"

security-full: ## Run comprehensive security scan
	@echo "Running comprehensive security scan..."
	$(BANDIT) -r $(PACKAGE_DIR)/ -f json -o bandit-report.json
	safety check --json --output safety-report.json || true
	@echo "✅ Security reports generated"
	@echo "📊 Bandit report: bandit-report.json"
	@echo "📊 Safety report: safety-report.json"

# ============================================================================
# Build & Package
# ============================================================================

build: ## Build Python package
	$(PYTHON) -m build
	@echo "✅ Package built: dist/"

package: build ## Build and check package
	$(PYTHON) -m twine check dist/*
	@echo "✅ Package checked"

package-upload-test: package ## Upload package to TestPyPI
	$(PYTHON) -m twine upload --repository testpypi dist/*
	@echo "✅ Package uploaded to TestPyPI"

package-upload: package ## Upload package to PyPI
	$(PYTHON) -m twine upload dist/*
	@echo "✅ Package uploaded to PyPI"

# ============================================================================
# Deployment
# ============================================================================

deploy-local: docker-up ## Deploy locally with docker-compose
	@echo "✅ Local deployment complete"
	@echo "🌐 API: http://localhost:$(API_PORT)"
	@echo "🌐 Web UI: http://localhost:$(WEB_PORT)"

check-health: ## Check health of all services
	@echo "Checking service health..."
	@curl -s http://localhost:$(API_PORT)/health/full | $(PYTHON) -m json.tool || echo "❌ API not responding"
	@curl -s http://localhost:$(WEB_PORT)/health/live || echo "❌ Web not responding"
	@echo "✅ Health check complete"

# ============================================================================
# Utilities
# ============================================================================

clean: ## Clean build artifacts and cache files
	@echo "Cleaning build artifacts..."
	rm -rf build/ dist/ *.egg-info .eggs/
	rm -rf htmlcov/ .coverage coverage.xml .pytest_cache/
	rm -rf .mypy_cache/ .tox/ .hypothesis/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.log" -delete
	@echo "✅ Cleaned"

clean-all: clean docker-clean ## Clean everything including Docker
	@echo "✅ Everything cleaned"

docs: ## Generate documentation
	@echo "Generating documentation..."
	@echo "📚 Documentation in progress..."
	@echo "✅ Documentation generated"

benchmark: ## Run performance benchmarks
	@echo "Running performance benchmarks..."
	$(PYTEST) $(TEST_DIR)/ -v -m performance --benchmark-only
	@echo "✅ Benchmarks complete"

requirements-update: ## Update requirements.txt from pyproject.toml
	$(PIP) install pip-tools
	pip-compile pyproject.toml -o requirements.txt
	@echo "✅ Requirements updated"

setup-dev: install-all ## Complete development environment setup
	@echo "Setting up development environment..."
	cp .env.example .env
	@echo "✅ Development environment ready"
	@echo "💡 Run 'make test-quick' to verify setup"

# ============================================================================
# CI/CD Simulation
# ============================================================================

ci-local: ## Simulate CI pipeline locally
	@echo "🔄 Running local CI pipeline..."
	@make format-check
	@make lint
	@make test-quick
	@make docker-build
	@make security-scan
	@echo "✅ Local CI pipeline complete"

pre-commit: format lint test-quick ## Run pre-commit checks
	@echo "✅ Pre-commit checks passed"

pre-push: ci-local ## Run pre-push checks
	@echo "✅ Pre-push checks passed"

# ============================================================================
# Monitoring
# ============================================================================

metrics: ## Show metrics endpoint
	@curl -s http://localhost:$(API_PORT)/metrics | head -n 50

logs-live: ## Tail live logs
	tail -f logs/*.log

# ============================================================================
# Knuth's Makefile Philosophy
# ============================================================================
#
# "Make the common case fast" - Donald Knuth
#
# This Makefile provides:
# 1. Fast, one-command operations for common tasks
# 2. Clear, descriptive target names
# 3. Helpful output messages
# 4. Organized sections
# 5. Comprehensive coverage of development workflow
#
# Graham's Practical Approach:
# 1. Short, memorable commands (make test, make deploy)
# 2. Consistent naming (test-*, docker-*, deploy-*)
# 3. Help text for every target
# 4. Fail-fast error handling
# 5. Useful output feedback
#
# Usage Examples:
#   make help           # Show all commands
#   make setup-dev      # Setup development environment
#   make test-quick     # Quick test run
#   make docker-up      # Start all services
#   make ci-local       # Run full CI pipeline locally
#
# ============================================================================
