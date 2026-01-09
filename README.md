# {{PROJECT_NAME}}

[![Python](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

{{PROJECT_DESCRIPTION}}

## Installation

**Prérequis** : Python 3.13+, [uv](https://github.com/astral-sh/uv) (`pip install uv`)

```bash
uv venv && .venv\Scripts\activate  # Windows
# uv venv && source .venv/bin/activate  # Linux/Mac
uv sync --group dev
pre-commit install
cp .env.example .env  # Puis renseigner les valeurs
```

## Structure

```
├── scripts/          # CLI / production scripts
├── src/              # Source code
├── notebooks/        # Exploration & analysis
├── data/
│   ├── raw/          # Raw data (not versioned)
│   └── processed/    # Processed data (not versioned)
├── tests/            # Tests
└── docs/             # Documentation
```

## Usage

```bash
# Run tests
pytest

# Lint & format
ruff check . --fix
ruff format .
```
