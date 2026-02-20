"""Real-time streaming quotes from IBKR.

Subscribes to live market data and displays updating quotes in the terminal.
Requires a running IB Gateway connection.
"""

import signal
import sys

import structlog
from ib_async import IB, Stock
from rich.console import Console
from rich.live import Live
from rich.table import Table

from trading_scanner.config import ScannerConfig, get_config

logger = structlog.get_logger(__name__)
console = Console()


def _build_quote_table(quotes: dict[str, dict]) -> Table:
    """Build a Rich table from current quote data.

    Args:
        quotes: Dict mapping tickers to their latest quote data.

    Returns:
        Formatted Rich Table.
    """
    table = Table(title="📡 Live Quotes (IBKR)", show_lines=True)
    table.add_column("Ticker", style="bold white", min_width=6)
    table.add_column("Last", justify="right", min_width=10)
    table.add_column("Bid", justify="right", min_width=10)
    table.add_column("Ask", justify="right", min_width=10)
    table.add_column("Volume", justify="right", min_width=12)
    table.add_column("High", justify="right", min_width=10)
    table.add_column("Low", justify="right", min_width=10)

    for ticker, data in sorted(quotes.items()):
        last = f"${data['last']:.2f}" if data.get("last") else "-"
        bid = f"${data['bid']:.2f}" if data.get("bid") else "-"
        ask = f"${data['ask']:.2f}" if data.get("ask") else "-"
        volume = f"{data['volume']:,.0f}" if data.get("volume") else "-"
        high = f"${data['high']:.2f}" if data.get("high") else "-"
        low = f"${data['low']:.2f}" if data.get("low") else "-"

        table.add_row(ticker, last, bid, ask, volume, high, low)

    return table


def stream_quotes(
    tickers: list[str],
    config: ScannerConfig | None = None,
) -> None:
    """Stream live quotes for a list of tickers in the terminal.

    Displays a continuously updating Rich table with bid/ask/last/volume.
    Press Ctrl+C to stop.

    Args:
        tickers: List of stock symbols to stream.
        config: Scanner configuration.

    Raises:
        ConnectionError: If IB Gateway is not available.
    """
    cfg = config or get_config()
    ib = IB()

    try:
        ib.connect(
            host=cfg.ibkr_host,
            port=cfg.ibkr_port,
            clientId=cfg.ibkr_client_id + 100,  # Offset to avoid conflicts with scanner
            timeout=cfg.ibkr_timeout,
            readonly=True,
        )
    except Exception as e:
        raise ConnectionError(
            f"Cannot stream: IB Gateway not available at {cfg.ibkr_host}:{cfg.ibkr_port}. "
            f"Error: {e}"
        ) from e

    # Subscribe to market data for all tickers
    contracts = {}
    for ticker in tickers:
        ticker = ticker.upper().strip()
        contract = Stock(ticker, "SMART", "USD")
        qualified = ib.qualifyContracts(contract)
        if qualified:
            ib.reqMktData(qualified[0], "", False, False)
            contracts[ticker] = qualified[0]
        else:
            logger.warning("Could not qualify contract", ticker=ticker)

    if not contracts:
        console.print("[red]No valid contracts to stream.[/red]")
        ib.disconnect()
        return

    console.print(f"[cyan]Streaming {len(contracts)} tickers. Press Ctrl+C to stop.[/cyan]\n")

    # Handle graceful shutdown
    def _shutdown(signum: int, frame: object) -> None:
        ib.disconnect()
        console.print("\n[dim]Stream stopped.[/dim]")
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)

    # Live-updating table
    try:
        with Live(console=console, refresh_per_second=2) as live:
            while ib.isConnected():
                quotes: dict[str, dict] = {}
                for ticker, contract in contracts.items():
                    ticker_data = ib.ticker(contract)
                    if ticker_data:
                        quotes[ticker] = {
                            "bid": ticker_data.bid if ticker_data.bid > 0 else None,
                            "ask": ticker_data.ask if ticker_data.ask > 0 else None,
                            "last": ticker_data.last if ticker_data.last > 0 else None,
                            "volume": ticker_data.volume if ticker_data.volume >= 0 else None,
                            "high": ticker_data.high if ticker_data.high > 0 else None,
                            "low": ticker_data.low if ticker_data.low > 0 else None,
                        }

                if quotes:
                    live.update(_build_quote_table(quotes))

                ib.sleep(0.5)
    finally:
        ib.disconnect()
        logger.info("Stream disconnected")
