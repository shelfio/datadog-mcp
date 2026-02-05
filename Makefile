.PHONY: build run test test-verbose test-integration clean install lint help

# Default target
help:
	@echo "Available targets:"
	@echo "  build            - Install dependencies and build the package"
	@echo "  run              - Run the MCP server"
	@echo "  test             - Run all tests"
	@echo "  test-verbose     - Run all tests with verbose output"
	@echo "  test-integration - Run integration tests only"
	@echo "  install          - Install dependencies including test extras"
	@echo "  clean            - Remove build artifacts and caches"
	@echo "  lint             - Run Python syntax check"

# Build/install the package
build:
	uv sync

# Install with test dependencies
install:
	uv sync --extra test

# Run the MCP server
run:
	uv run datadog-mcp

# Run tests (requires DD_API_KEY, DD_APP_KEY, DD_SITE env vars)
test:
	DD_API_KEY=test DD_APP_KEY=test DD_SITE=datadoghq.com uv run pytest

# Run tests with verbose output
test-verbose:
	DD_API_KEY=test DD_APP_KEY=test DD_SITE=datadoghq.com uv run pytest -v

# Run integration tests only
test-integration:
	DD_API_KEY=test DD_APP_KEY=test DD_SITE=datadoghq.com uv run pytest tests/test_integration.py -v

# Clean build artifacts
clean:
	rm -rf .venv
	rm -rf __pycache__
	rm -rf .pytest_cache
	rm -rf *.egg-info
	rm -rf dist
	rm -rf build
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Lint check
lint:
	uv run python -m py_compile datadog_mcp/*.py datadog_mcp/**/*.py
