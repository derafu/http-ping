# Default target: do all.
all: lint test dist lambda

# Lint and auto-fix with ruff.
lint: install-dev
	.venv/bin/ruff check .

# Run tests with coverage.
test: install-dev
	mkdir -p var
	.venv/bin/pytest

# Build HTML documentation with Sphinx.
docs: install-dev
	.venv/bin/sphinx-build -b html docs/ build/docs

# Build and upload.
dist: install-dev
	.venv/bin/python -m build

upload: dist
	.venv/bin/twine upload dist/*

# Lambda package for AWS.
lambda: install-dev
	.venv/bin/pip install . -t function/
	chmod -R 755 function/
	cd function/ && zip -r ../http-ping-function.zip *

# Install development dependencies (ruff, etc.).
install-dev:
	python3 -m venv .venv
	.venv/bin/pip install -e ".[dev]"

# Clean up: lambda package and other dev and build/dist directories.
clean:
	rm -rf http-ping-function.zip build/ dist/
	cd function/ && ls | grep -v lambda_function.py | xargs rm -rf
	rm -rf .venv/ var/ .ruff_cache .pytest_cache .coverage htmlcov/ http_ping.egg-info

.PHONY: all install-dev lint test docs clean lambda dist upload
