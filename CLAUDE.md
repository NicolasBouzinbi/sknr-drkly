# CLAUDE.md

## Project Overview
Day trading / swing trading stock scanner built with Python.
Uses the interactive brokers API for market data and technical analysis indicators.

## Tech Stack
- Python 3.12+
- uv for dependency management (pyproject.toml)
- yfinance for market data
- pandas / numpy for data manipulation
- ta-lib or pandas-ta for technical indicators
- Rich for CLI output (or Streamlit/Dash for web UI)

## Architecture
- `src/scanner/` — Core scanning logic
- `src/indicators/` — Technical indicator calculations
- `src/filters/` — Stock filtering criteria
- `src/ui/` — User interface (CLI or web)
- `tests/` — pytest test suite

## Development Commands
- `uv run pytest` — Run tests
- `uv run python -m scanner` — Run the scanner
- `uv run ruff check .` — Lint
- `uv run ruff format .` — Format

## Code Standards
- PEP 8 compliant (enforced by ruff)
- Type hints on all function signatures
- Docstrings on all public functions (Google style)
- KISS and DRY principles
- Modern Python (3.12+ features: match/case, f-strings, etc.)