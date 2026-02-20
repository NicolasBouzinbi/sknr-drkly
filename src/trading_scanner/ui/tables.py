"""Rich table formatting for scan results display."""

from rich.console import Console
from rich.table import Table
from rich.text import Text

from trading_scanner.strategies.base import ScanResult

console = Console()

STRENGTH_COLORS = {
    "strong": "bold green",
    "moderate": "yellow",
    "weak": "dim white",
}

SIGNAL_EMOJIS = {
    "Oversold Bounce": "📈",
    "EMA Bullish Cross": "🔀",
    "VWAP Bounce": "⬆️",
    "Momentum Surge": "🚀",
}


def display_scan_results(
    results: list[ScanResult],
    strategy_name: str,
) -> None:
    """Display scan results as a formatted Rich table.

    Args:
        results: List of ScanResult from a strategy scan.
        strategy_name: Name of the strategy used.
    """
    if not results:
        console.print(f"\n[dim]No signals found for strategy: {strategy_name}[/dim]\n")
        return

    table = Table(
        title=f"🔍 Scan Results — {strategy_name}",
        title_style="bold cyan",
        show_lines=True,
        pad_edge=True,
    )

    table.add_column("Ticker", style="bold white", min_width=6)
    table.add_column("Signal", min_width=18)
    table.add_column("Strength", min_width=10, justify="center")
    table.add_column("Price", justify="right", min_width=10)
    table.add_column("RSI", justify="right", min_width=6)
    table.add_column("RVOL", justify="right", min_width=6)
    table.add_column("EMA Trend", justify="center", min_width=10)
    table.add_column("vs VWAP", justify="center", min_width=8)
    table.add_column("Details", min_width=20)

    # Sort by strength (strong first)
    strength_order = {"strong": 0, "moderate": 1, "weak": 2}
    sorted_results = sorted(results, key=lambda r: strength_order.get(r.strength, 3))

    for r in sorted_results:
        emoji = SIGNAL_EMOJIS.get(r.signal, "📊")
        color = STRENGTH_COLORS.get(r.strength, "white")

        strength_text = Text(r.strength.upper(), style=color)

        rsi_text = _format_rsi(r.rsi)
        rvol_text = _format_rvol(r.rvol)
        vwap_text = _format_vwap(r.vwap_position)
        ema_text = _format_ema_trend(r.ema_trend)

        table.add_row(
            r.ticker,
            f"{emoji} {r.signal}",
            strength_text,
            f"${r.price:,.2f}",
            rsi_text,
            rvol_text,
            ema_text,
            vwap_text,
            r.details,
        )

    console.print()
    console.print(table)
    console.print(f"\n[dim]{len(results)} signal(s) found[/dim]\n")


def display_watchlists(watchlists: dict[str, int]) -> None:
    """Display available watchlists as a Rich table.

    Args:
        watchlists: Dict mapping watchlist names to ticker counts.
    """
    table = Table(title="📋 Available Watchlists", show_lines=True)
    table.add_column("Name", style="bold")
    table.add_column("Tickers", justify="right")

    for name, count in watchlists.items():
        table.add_row(name, str(count))

    console.print()
    console.print(table)
    console.print()


def _format_rsi(rsi: float | None) -> str:
    if rsi is None:
        return "-"
    if rsi < 30:
        return f"[red]{rsi:.1f}[/red]"
    if rsi > 70:
        return f"[green]{rsi:.1f}[/green]"
    return f"{rsi:.1f}"


def _format_rvol(rvol: float | None) -> str:
    if rvol is None:
        return "-"
    if rvol >= 2.0:
        return f"[bold green]{rvol:.1f}x[/bold green]"
    if rvol >= 1.5:
        return f"[green]{rvol:.1f}x[/green]"
    return f"{rvol:.1f}x"


def _format_vwap(position: str | None) -> str:
    if position is None:
        return "-"
    if position == "above":
        return "[green]Above[/green]"
    return "[red]Below[/red]"


def _format_ema_trend(trend: str | None) -> str:
    if trend is None:
        return "-"
    if trend == "bullish":
        return "[green]Bullish[/green]"
    return "[red]Bearish[/red]"
