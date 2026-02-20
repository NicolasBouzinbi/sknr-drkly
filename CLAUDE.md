# CLAUDE.md

## Project Overview

CLI stock scanner for US equities (NYSE/NASDAQ) targeting day trading and swing trading setups.
Uses Interactive Brokers (IBKR) as primary data source with yfinance as fallback.
Supports historical bars (daily + intraday), real-time streaming quotes, and technical indicator scanning.

## Tech Stack

- Python 3.12+ with type hints everywhere
- uv for dependency management (pyproject.toml)
- **ib_async** for IBKR Gateway API (replaces ib_insync, actively maintained)
- yfinance as fallback data source
- pandas + pandas-ta for indicators
- Rich for CLI display (including Live tables for streaming)
- Click for CLI framework
- Pydantic for config/validation
- structlog for logging

## Architecture

```
src/trading_scanner/
├── cli.py               # Click CLI entrypoint (scan, live, status, watchlist, strategies)
├── config.py            # Pydantic settings (IBKR connection + scanner params)
├── data/
│   ├── fetcher.py       # Provider orchestrator with fallback logic
│   ├── streaming.py     # Real-time quote streaming (IBKR only, Rich Live table)
│   ├── watchlists.py    # Watchlist management (JSON storage)
│   └── providers/
│       ├── __init__.py  # DataProvider ABC + DataSource enum
│       ├── ibkr.py      # IBKR provider (ib_async: historical + realtime)
│       └── yfinance_provider.py  # yfinance fallback provider
├── indicators/
│   ├── __init__.py      # apply_all() convenience function
│   ├── rsi.py           # RSI calculation
│   ├── ema.py           # EMA crossover detection
│   ├── volume.py        # Relative volume analysis
│   └── vwap.py          # VWAP calculation
├── strategies/
│   ├── base.py          # Abstract base strategy + ScanResult model
│   └── presets.py       # Built-in scan strategies (4 presets)
├── ui/
│   └── tables.py        # Rich table formatting & display
└── utils/
    └── market.py        # Market hours, trading day checks
```

## IBKR Configuration

- Default connection: IB Gateway on 127.0.0.1:4001 (headless)
- IB Gateway ports: 4001 (live), 4002 (paper)
- TWS ports: 7496 (live), 7497 (paper)
- ib_async handles the IBKR binary protocol directly (no ibapi needed)
- Rate limit: ~60 historical requests per 10 minutes, 0.5s delay between requests

## Data Flow

```
CLI → fetcher.py (orchestrator)
        ├── IBKRProvider (primary) → IB Gateway → IBKR servers
        └── YFinanceProvider (fallback) → Yahoo Finance API
```

If IBKR connection fails, fetcher automatically falls back to yfinance.

## Development Commands

- `uv run pytest` — run tests
- `uv run pytest --cov=trading_scanner` — run tests with coverage
- `uv run ruff check .` — lint
- `uv run ruff format .` — format
- `uv run mypy src/` — type check
- `uv run scan --help` — run the CLI
- `uv run scan status` — check IBKR connection + config

## Code Standards

- PEP 8 enforced by ruff (line length 99)
- Type hints on ALL function signatures
- Google-style docstrings on all public functions
- KISS and DRY — no premature abstraction
- Prefer composition over inheritance
- Use `match/case` for provider dispatch
- All DataFrames use lowercase columns: open, high, low, close, volume
