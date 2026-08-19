.PHONY: help install test lint format check clean

help:
	@echo "Available commands:"
	@echo "  make install   - Install development dependencies"
	@echo "  make test      - Run tests with coverage"
	@echo "  make lint      - Run ruff linter"
	@echo "  make format    - Format code with ruff and black"
	@echo "  make check     - Run lint, type check, and test"
	@echo "  make clean     - Remove build artifacts and cache files"

install:
	pip install -e ".[dev]"

test:
	pytest

lint:
	ruff check .

format:
	ruff format .
	black .

typecheck:
	mypy src/

check: lint typecheck test

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache/ .mypy_cache/ .ruff_cache/ htmlcov/ dist/ build/ *.egg-info/
