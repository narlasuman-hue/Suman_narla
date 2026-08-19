# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Suman_narla** is a Python project licensed under Mozilla Public License 2.0. This is an early-stage repository where code patterns and structures are still being established.

## Repository Structure

The project currently has a minimal structure:

- `README.md` - Project overview
- `LICENSE` - MPL 2.0 license
- `.gitignore` - Python standard ignores (pip, venv, pytest, mypy, Jupyter, Streamlit, etc.)

As the project grows, anticipated directory structure:
- `src/` or module root - Main Python package code
- `tests/` - Test files using pytest
- `docs/` - Documentation
- `scripts/` - Utility scripts and automation

## Development Setup

### Environment Setup

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install development dependencies (once a requirements file exists):
   ```bash
   pip install -r requirements-dev.txt
   ```

### Common Commands

These commands should be available once the project is structured with appropriate tooling:

- **Run tests**: `pytest` or `pytest tests/test_*.py`
- **Run a single test**: `pytest tests/test_file.py::test_function`
- **Run tests with coverage**: `pytest --cov=src tests/`
- **Lint code**: `ruff check .` (or `pylint`, `flake8` if using those)
- **Format code**: `ruff format .` (or `black` if using that)
- **Type check**: `mypy src/` (once type hints are added)
- **Run all checks**: Create a `Makefile` or use a script to run lint, format, and test in sequence

### Code Style

- Follow PEP 8 conventions
- Use type hints where practical
- Aim for maximum line length of 100 characters (configurable in tool settings)
- Docstrings for public functions and classes (can use Google or Numpy style, but be consistent)
- Tests should be clear and isolated; use descriptive test names like `test_<function>_<scenario>`

## Git Workflow

### Branch Strategy

- **main**: Production-ready code (protected)
- **Feature branches**: `feature/<name>`, `fix/<name>`, or `docs/<name>` for specific work
- **Development branch**: `claude/<description>` for AI-assisted development work

### Commit Guidelines

- Use clear, descriptive commit messages
- Start with a verb: "Add", "Fix", "Update", "Refactor", "Remove", "Docs"
- Keep commits focused on a single concern
- Reference issue numbers when relevant: "Fixes #123" or "Relates to #456"

### Pull Requests

- All changes should go through PRs (even from Claude)
- Include a summary of changes in the PR description
- Link to related issues
- Ensure tests pass and coverage doesn't decrease before merging

## When Adding New Features

1. **Create a test first** - Start with a failing test that defines desired behavior
2. **Implement the feature** - Write code to make the test pass
3. **Refactor if needed** - Clean up code while keeping tests green
4. **Document public APIs** - Add docstrings and type hints
5. **Run the full test suite** - Ensure no regressions: `pytest`
6. **Commit and push** - Follow commit guidelines above

## Key Conventions for Claude

- **Ask before major changes**: Large refactors, architectural changes, or dependency additions should prompt for user confirmation
- **Keep PRs focused**: Avoid mixing concerns in a single PR
- **Test-driven**: Write tests alongside features
- **Documentation**: Update docs when APIs change
- **Performance**: No unnecessary complexity; measure before optimizing
- **Security**: Follow OWASP principles; avoid hardcoding secrets; validate external input

## Dependencies Management

When adding dependencies:

1. Check if they're essential (don't add "just in case" dependencies)
2. Prefer well-maintained, popular packages
3. Keep dependency count minimal
4. Use `pip-audit` or similar to check for known vulnerabilities
5. Document in `requirements.txt` or `pyproject.toml` (with pinned or loose versions as appropriate)

## File Organization

- Keep Python files under 300-400 lines when possible (split into modules if growing larger)
- One class per file unless they're tightly coupled helpers
- Use `__init__.py` to define module interfaces
- Private functions/classes start with underscore: `_helper_function()`

## Testing Strategy

- Aim for 70%+ code coverage for critical paths
- Use pytest fixtures for common test setup
- Mock external dependencies (APIs, file I/O, etc.)
- Name test files `test_*.py` or `*_test.py` (pytest auto-discovers)
- Organize tests to mirror source structure: `tests/test_module.py` for `src/module.py`

## Performance and Monitoring

- Profile before optimizing (use `cProfile` or similar)
- Log important operations and errors
- Consider adding metrics collection for long-running processes
- Document performance characteristics of algorithms

## Common Issues and Gotchas

- **Import paths**: Be consistent with absolute vs. relative imports
- **Circular imports**: Refactor to resolve if they occur
- **Missing dependencies**: Always add to requirements files
- **Type hints**: Can catch bugs early; use `mypy` in CI if possible
- **Stale cache**: Clear `__pycache__` and `.pytest_cache` if tests behave unexpectedly

## Questions or Uncertainties?

When encountering unclear patterns or design decisions:
1. Check existing similar code for consistency
2. Prefer simple, readable code over clever optimizations
3. Ask the repository owner when significant decisions need to be made
4. Document non-obvious choices with inline comments

---

Last updated: 2026-08-19  
License: Mozilla Public License 2.0
