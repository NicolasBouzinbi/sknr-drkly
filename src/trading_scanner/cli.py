"""CLI entrypoint for the trading scanner."""

import csv
import sys
from pathlib import Path

import click
import structlog
from rich.console import Console

from trading_scanner.config import DataSourceEnum, get_config
from trading_scanner.data.fetcher import fetch_tickers
from trading_scanner.data.providers import DataSource
from trading_scanner.data.watchlists import (
    add_to_watchlist,
    get_watchlist,
    list_watchlists,
    remove_from_watchlist,
)
from trading_scanner.indicators import apply_all
from trading_scanner.strategies.presets import STRATEGIES, get_strategy
from trading_scanner.ui.tables import display_scan_results, display_watchlists
from trading_scanner.utils.market import get_market_status

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

console = Console()


@click.group()
@click.version_option(package_name="trading-scanner")
def main() -> None:
    """🔍 Trading Scanner — CLI stock scanner for day/swing trading setups.

    Uses Interactive Brokers (IBKR) as primary data source with yfinance fallback.
    """


@main.command()
@click.option(
    "--strategy", "-s",
    type=click.Choice(list(STRATEGIES.keys())),
    required=True,
    help="Scanning strategy to use.",
)
@click.option(
    "--watchlist", "-w",
    type=str,
    default=None,
    help="Watchlist name to scan (e.g., mega_cap, tech_50).",
)
@click.option(
    "--tickers", "-t",
    type=str,
    default=None,
    help="Comma-separated ticker symbols (e.g., AAPL,MSFT,NVDA).",
)
@click.option(
    "--period", "-p",
    type=str,
    default=None,
    help="Data period (e.g., 1mo, 3mo, 6mo, 1y). Defaults to config.",
)
@click.option(
    "--interval", "-i",
    type=str,
    default=None,
    help="Bar size (e.g., 1d, 1h, 15m, 5m). Defaults to config.",
)
@click.option(
    "--source",
    type=click.Choice(["ibkr", "yfinance"]),
    default=None,
    help="Data source: 'ibkr' (default) or 'yfinance'. Falls back to yfinance if IBKR unavailable.",
)
@click.option(
    "--export",
    type=click.Path(),
    default=None,
    help="Export results to CSV file.",
)
@click.option(
    "--no-rth",
    is_flag=True,
    default=False,
    help="Include pre/post-market data (IBKR only).",
)
def scan(
    strategy: str,
    watchlist: str | None,
    tickers: str | None,
    period: str | None,
    interval: str | None,
    source: str | None,
    export: str | None,
    no_rth: bool,
) -> None:
    """Run a scan with the specified strategy."""
    if not watchlist and not tickers:
        console.print("[red]Error: Provide --watchlist or --tickers[/red]")
        sys.exit(1)

    # Resolve ticker list
    if tickers:
        ticker_list = [t.strip().upper() for t in tickers.split(",")]
    else:
        try:
            ticker_list = get_watchlist(watchlist)  # type: ignore[arg-type]
        except KeyError as e:
            console.print(f"[red]Error: {e}[/red]")
            sys.exit(1)

    # Resolve data source
    data_source = DataSource(source) if source else None

    # Display market status
    config = get_config()
    effective_source = source or config.data_source
    status = get_market_status()
    console.print(f"\n[dim]Market status: {status}[/dim]")
    console.print(f"[dim]Data source: {effective_source} (fallback: yfinance)[/dim]")
    console.print(f"[dim]Scanning {len(ticker_list)} tickers with strategy: {strategy}[/dim]\n")

    # Fetch data
    with console.status("[bold cyan]Fetching market data..."):
        data = fetch_tickers(
            ticker_list,
            duration=period,
            bar_size=interval,
            source=data_source,
            use_rth=not no_rth,
            config=config,
        )

    if not data:
        console.print("[red]No data retrieved. Check your connection and tickers.[/red]")
        sys.exit(1)

    # Apply indicators
    with console.status("[bold cyan]Computing indicators..."):
        enriched_data = {
            ticker: apply_all(
                df,
                rsi_period=config.rsi_period,
                ema_fast=config.ema_fast,
                ema_slow=config.ema_slow,
                volume_sma_period=config.volume_sma_period,
            )
            for ticker, df in data.items()
        }

    # Run strategy
    strat = get_strategy(strategy)
    results = strat.scan_multiple(enriched_data)

    # Display
    display_scan_results(results, strategy_name=strategy)

    # Export if requested
    if export and results:
        _export_csv(results, Path(export))
        console.print(f"[green]Results exported to {export}[/green]\n")


@main.command()
@click.option(
    "--watchlist", "-w",
    type=str,
    default=None,
    help="Watchlist to stream.",
)
@click.option(
    "--tickers", "-t",
    type=str,
    default=None,
    help="Comma-separated tickers to stream.",
)
def live(watchlist: str | None, tickers: str | None) -> None:
    """Stream live quotes from IBKR (requires IB Gateway)."""
    from trading_scanner.data.streaming import stream_quotes

    if not watchlist and not tickers:
        console.print("[red]Error: Provide --watchlist or --tickers[/red]")
        sys.exit(1)

    if tickers:
        ticker_list = [t.strip().upper() for t in tickers.split(",")]
    else:
        try:
            ticker_list = get_watchlist(watchlist)  # type: ignore[arg-type]
        except KeyError as e:
            console.print(f"[red]Error: {e}[/red]")
            sys.exit(1)

    try:
        stream_quotes(ticker_list)
    except ConnectionError as e:
        console.print(f"[red]{e}[/red]")
        console.print("[dim]Hint: Make sure IB Gateway is running with API enabled on port 4001.[/dim]")
        sys.exit(1)


@main.command()
def status() -> None:
    """Show connection status and configuration."""
    config = get_config()
    market = get_market_status()

    console.print("\n[bold cyan]Scanner Configuration[/bold cyan]\n")
    console.print(f"  Market status:   {market}")
    console.print(f"  Data source:     {config.data_source}")
    console.print(f"  IBKR host:       {config.ibkr_host}:{config.ibkr_port}")
    console.print(f"  IBKR client ID:  {config.ibkr_client_id}")
    console.print(f"  Default period:  {config.default_period}")
    console.print(f"  Default bar:     {config.default_interval}")
    console.print(f"  RSI period:      {config.rsi_period}")
    console.print(f"  EMA fast/slow:   {config.ema_fast}/{config.ema_slow}")
    console.print(f"  Volume SMA:      {config.volume_sma_period}")

    # Test IBKR connection
    console.print("\n[bold cyan]IBKR Connection Test[/bold cyan]\n")
    try:
        from ib_async import IB
        ib = IB()
        ib.connect(
            host=config.ibkr_host,
            port=config.ibkr_port,
            clientId=config.ibkr_client_id + 200,
            timeout=5,
            readonly=True,
        )
        console.print("  [green]✓ IB Gateway connected[/green]")
        accounts = ib.managedAccounts()
        if accounts:
            console.print(f"  [green]✓ Account(s): {', '.join(accounts)}[/green]")
        ib.disconnect()
    except Exception as e:
        console.print(f"  [red]✗ IB Gateway not available: {e}[/red]")
        console.print("  [dim]Hint: Start IB Gateway and enable API on port 4001[/dim]")

    console.print()


@main.group()
def watchlist() -> None:
    """Manage watchlists."""


@watchlist.command("list")
def watchlist_list() -> None:
    """List all available watchlists."""
    wl = list_watchlists()
    display_watchlists(wl)


@watchlist.command("show")
@click.argument("name")
def watchlist_show(name: str) -> None:
    """Show tickers in a watchlist."""
    try:
        tickers = get_watchlist(name)
        console.print(f"\n[bold]{name}[/bold]: {', '.join(tickers)}\n")
    except KeyError as e:
        console.print(f"[red]Error: {e}[/red]")


@watchlist.command("add")
@click.argument("name")
@click.argument("tickers", nargs=-1, required=True)
def watchlist_add(name: str, tickers: tuple[str, ...]) -> None:
    """Add tickers to a custom watchlist."""
    updated = add_to_watchlist(name, list(tickers))
    console.print(f"[green]Updated '{name}': {', '.join(updated)}[/green]")


@watchlist.command("remove")
@click.argument("name")
@click.argument("tickers", nargs=-1, required=True)
def watchlist_remove(name: str, tickers: tuple[str, ...]) -> None:
    """Remove tickers from a custom watchlist."""
    try:
        updated = remove_from_watchlist(name, list(tickers))
        console.print(f"[green]Updated '{name}': {', '.join(updated)}[/green]")
    except KeyError as e:
        console.print(f"[red]Error: {e}[/red]")


@main.command()
def strategies() -> None:
    """List all available scanning strategies."""
    console.print("\n[bold cyan]Available Strategies[/bold cyan]\n")
    for name, cls in STRATEGIES.items():
        strat = cls()
        console.print(f"  [bold]{name}[/bold] — {strat.description}")
    console.print()


def _export_csv(results: list, filepath: Path) -> None:
    """Export scan results to a CSV file."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with filepath.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "ticker", "signal", "strength", "price",
                "rsi", "rvol", "ema_trend", "vwap_position", "details",
            ],
        )
        writer.writeheader()
        for r in results:
            writer.writerow(r.model_dump())


if __name__ == "__main__":
    main()
