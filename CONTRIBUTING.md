# Contributing to SOC Copilot

Thank you for your interest in contributing to SOC Copilot! This document provides guidelines for contributing to this project.

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Git
- 4GB+ RAM

### Development Setup

```bash
# 1. Fork and clone the repository
git clone https://github.com/BunnyPraneeth5/SOC-Copilot.git
cd SOC-Copilot

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate      # Linux/macOS
.\venv\Scripts\activate       # Windows

# 3. Install with dev dependencies
pip install -e ".[dev]"
# OR
pip install -r requirements-dev.txt

# 4. Train ML models
python scripts/train_models.py
python scripts/train_text_log_model.py

# 5. Run tests to verify
python -m pytest tests/ -v
```

## Development Workflow

### Branch Naming

- `feature/short-description` — New features
- `fix/short-description` — Bug fixes
- `docs/short-description` — Documentation updates
- `refactor/short-description` — Code refactoring

### Code Style

We use the following tools for code quality:

```bash
# Format code
black src/ tests/ --line-length 100

# Lint code
ruff src/ tests/

# Type checking
mypy src/
```

**Guidelines:**
- Line length: 100 characters
- Use type hints for all public functions
- Write docstrings for all public classes and methods
- Follow PEP 8 naming conventions

### Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=soc_copilot --cov-report=html

# Run specific test categories
python -m pytest tests/unit/ -v
python -m pytest tests/integration/ -v
```

**Test requirements:**
- All new features must include unit tests
- Maintain test coverage above 80%
- Tests must pass before submitting a pull request

## Project Structure

```
src/soc_copilot/
├── core/           # Base classes, config, logging
├── data/           # Log ingestion, preprocessing, feature engineering
├── models/         # ML models (isolation forest, random forest, ensemble)
├── intelligence/   # Threat intelligence (extensible)
├── security/       # OS permissions
├── phase2/         # Calibration, drift, explainability, feedback
├── phase3/         # Governance
├── phase4/         # Real-time pipeline (controller, ingestion, UI)
└── ui/             # Legacy UI components
```

## Submitting Changes

1. Create a feature branch from `main`
2. Make your changes with clear commit messages
3. Run the full test suite
4. Update documentation if needed
5. Submit a pull request with a description of your changes

### Commit Message Format

```
type: short description

Longer description if needed.

Types: feat, fix, docs, style, refactor, test, chore
```

**Examples:**
```
feat: add PCAP log parser
fix: resolve dashboard refresh on empty state
docs: update deployment guide for Docker
```

## Reporting Issues

When reporting issues, include:
- Python version (`python --version`)
- OS and version
- Steps to reproduce
- Expected vs actual behavior
- Relevant log output from `logs/`

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
