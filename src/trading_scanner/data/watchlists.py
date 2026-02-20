"""Watchlist management with JSON file persistence."""

import json
from pathlib import Path

import structlog

from trading_scanner.config import get_config

logger = structlog.get_logger(__name__)

# Built-in watchlists
BUILTIN_WATCHLISTS: dict[str, list[str]] = {
    "mega_cap": [
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B", "JPM", "V",
    ],
    "tech_50": [
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AMD", "INTC", "CRM",
        "ADBE", "NFLX", "ORCL", "CSCO", "AVGO", "TXN", "QCOM", "NOW", "INTU", "AMAT",
        "MU", "LRCX", "KLAC", "SNPS", "CDNS", "MRVL", "FTNT", "PANW", "CRWD", "ZS",
        "DDOG", "SNOW", "NET", "SHOP", "SQ", "PYPL", "COIN", "PLTR", "U", "RBLX",
        "UBER", "ABNB", "DASH", "PINS", "SNAP", "TTD", "ZM", "OKTA", "TWLO", "ESTC",
    ],
    "volatile_movers": [
        "TSLA", "NVDA", "AMD", "COIN", "PLTR", "SOFI", "RIVN", "LCID", "NIO", "MARA",
        "RIOT", "SMCI", "ARM", "IONQ", "RGTI", "QUBT", "MSTR", "GME", "AMC", "BBBY",
    ],
}


def _load_custom_watchlists(filepath: Path) -> dict[str, list[str]]:
    """Load custom watchlists from JSON file."""
    if not filepath.exists():
        return {}
    try:
        return json.loads(filepath.read_text())
    except (json.JSONDecodeError, OSError):
        logger.warning("Failed to load watchlists file", path=str(filepath))
        return {}


def _save_custom_watchlists(watchlists: dict[str, list[str]], filepath: Path) -> None:
    """Save custom watchlists to JSON file."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(json.dumps(watchlists, indent=2))


def get_watchlist(name: str) -> list[str]:
    """Get a watchlist by name (checks built-in first, then custom).

    Args:
        name: Watchlist name.

    Returns:
        List of ticker symbols.

    Raises:
        KeyError: If watchlist name is not found.
    """
    if name in BUILTIN_WATCHLISTS:
        return BUILTIN_WATCHLISTS[name]

    cfg = get_config()
    custom = _load_custom_watchlists(cfg.watchlists_file)
    if name in custom:
        return custom[name]

    available = list(BUILTIN_WATCHLISTS.keys()) + list(custom.keys())
    raise KeyError(f"Watchlist '{name}' not found. Available: {', '.join(available)}")


def list_watchlists() -> dict[str, int]:
    """List all available watchlists with their ticker counts.

    Returns:
        Dict mapping watchlist names to number of tickers.
    """
    cfg = get_config()
    custom = _load_custom_watchlists(cfg.watchlists_file)
    result: dict[str, int] = {}

    for name, tickers in BUILTIN_WATCHLISTS.items():
        result[f"{name} (built-in)"] = len(tickers)

    for name, tickers in custom.items():
        result[name] = len(tickers)

    return result


def add_to_watchlist(name: str, tickers: list[str]) -> list[str]:
    """Add tickers to a custom watchlist (creates if not exists).

    Args:
        name: Watchlist name.
        tickers: Ticker symbols to add.

    Returns:
        Updated list of tickers in the watchlist.
    """
    cfg = get_config()
    custom = _load_custom_watchlists(cfg.watchlists_file)
    existing = custom.get(name, [])
    updated = list(dict.fromkeys(existing + [t.upper().strip() for t in tickers]))
    custom[name] = updated
    _save_custom_watchlists(custom, cfg.watchlists_file)
    logger.info("Tickers added", watchlist=name, count=len(tickers))
    return updated


def remove_from_watchlist(name: str, tickers: list[str]) -> list[str]:
    """Remove tickers from a custom watchlist.

    Args:
        name: Watchlist name.
        tickers: Ticker symbols to remove.

    Returns:
        Updated list of tickers in the watchlist.

    Raises:
        KeyError: If the watchlist doesn't exist.
    """
    cfg = get_config()
    custom = _load_custom_watchlists(cfg.watchlists_file)
    if name not in custom:
        raise KeyError(f"Custom watchlist '{name}' not found")

    tickers_upper = {t.upper().strip() for t in tickers}
    custom[name] = [t for t in custom[name] if t not in tickers_upper]
    _save_custom_watchlists(custom, cfg.watchlists_file)
    logger.info("Tickers removed", watchlist=name, count=len(tickers))
    return custom[name]
