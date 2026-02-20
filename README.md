# 🔍 Trading Scanner

CLI stock scanner for day trading and swing trading setups on US equities (NYSE/NASDAQ).

## Features

- **IBKR primary + yfinance fallback** — seamless data source switching
- **Real-time streaming** — live bid/ask/last quotes from IBKR
- **Intraday + daily bars** — 1m, 5m, 15m, 1h, 1d from IBKR
- **4 built-in strategies** — Oversold Bounce, EMA Crossover, VWAP Bounce, Momentum Surge
- **Technical indicators** — RSI, EMA (configurable), VWAP, Relative Volume
- **Watchlist management** — built-in + custom watchlists with JSON persistence
- **Rich CLI output** — color-coded tables with signal strength indicators
- **CSV export** — save scan results for further analysis

## Prerequisites

- **IB Gateway** (recommended) or TWS with API enabled
  - Download: https://www.interactivebrokers.com/en/trading/ibgateway-stable.php
  - Enable API: Configure → Settings → API → Enable and allow connections
  - Default port: 4001 (Gateway), 7497 (TWS paper)
- **Python 3.12+**
- **uv** package manager

## Quick Start

```bash
# Install dependencies
uv sync

# Check IBKR connection + configuration
uv run scan status

# Scan with IBKR data (primary)
uv run scan scan --strategy momentum_surge --watchlist mega_cap

# Scan with explicit yfinance (no IBKR needed)
uv run scan scan --strategy oversold_bounce --tickers AAPL,NVDA,AMD --source yfinance

# Intraday scan (5-minute bars, last 5 days)
uv run scan scan --strategy ema_crossover --tickers TSLA,NVDA -i 5m -p 5d

# Include pre/post-market data (IBKR only)
uv run scan scan --strategy momentum_surge --watchlist volatile_movers --no-rth

# Stream live quotes
uv run scan live --tickers AAPL,MSFT,NVDA,TSLA,AMD

# List strategies
uv run scan strategies

# Manage watchlists
uv run scan watchlist list
uv run scan watchlist add my_picks AAPL MSFT NVDA
uv run scan watchlist show my_picks

# Export to CSV
uv run scan scan --strategy ema_crossover --watchlist tech_50 --export results.csv
```

## Configuration

Set environment variables with `SCANNER_` prefix, or create `~/.trading_scanner/config.env`:

```env
# Data source: ibkr (default) or yfinance
SCANNER_DATA_SOURCE=ibkr

# IBKR Gateway connection
SCANNER_IBKR_HOST=127.0.0.1
SCANNER_IBKR_PORT=4001
SCANNER_IBKR_CLIENT_ID=1

# Scanner defaults
SCANNER_RSI_PERIOD=14
SCANNER_EMA_FAST=9
SCANNER_EMA_SLOW=21
SCANNER_VOLUME_SPIKE_THRESHOLD=1.5
SCANNER_DEFAULT_PERIOD=6mo
SCANNER_DEFAULT_INTERVAL=1d
```

## Data Source Behavior

| Scenario | What happens |
|----------|-------------|
| IBKR Gateway running | Uses IBKR for all data |
| IBKR Gateway down | Auto-falls back to yfinance with a warning |
| `--source yfinance` | Forces yfinance, skips IBKR entirely |
| `live` command | IBKR only (no fallback — requires live connection) |

## Development

```bash
uv run pytest                            # Run tests
uv run pytest --cov=trading_scanner      # With coverage
uv run ruff check .                      # Lint
uv run ruff format .                     # Format
uv run mypy src/                         # Type check
```
