"""NiceGUI dashboard for the trading scanner."""

import pandas as pd
import plotly.graph_objects as go
import structlog
from nicegui import run, ui
from plotly.subplots import make_subplots

from trading_scanner.config import get_config
from trading_scanner.data.fetcher import fetch_tickers
from trading_scanner.data.providers import DataSource
from trading_scanner.data.watchlists import (
    add_to_watchlist,
    get_watchlist,
    list_watchlists,
    remove_from_watchlist,
)
from trading_scanner.indicators import apply_all
from trading_scanner.strategies import STRATEGIES, get_strategy
from trading_scanner.utils.market import get_market_status

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_watchlist_options() -> dict[str, str]:
    """Build {raw_key: display_name} mapping for watchlist selector."""
    wl_info = list_watchlists()
    options: dict[str, str] = {}
    for display_name in wl_info:
        raw_name = display_name.removesuffix(" (built-in)")
        options[raw_name] = display_name
    return options


def _build_strategy_options() -> dict[str, str]:
    """Build {key: label} mapping for strategy selector."""
    return {k: f"{k} — {cls().description[:60]}" for k, cls in STRATEGIES.items()}


def _fmt(val: object, digits: int = 2) -> str:
    """Format a numeric value, returning '\u2014' for NaN."""
    try:
        if pd.isna(val):  # type: ignore[arg-type]
            return "\u2014"
        return f"{float(val):.{digits}f}"  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return "\u2014"


def _build_chart(df: pd.DataFrame) -> go.Figure:
    """Build a candlestick + volume + RSI plotly figure."""
    # Convert Timestamp index to ISO strings so orjson can serialize them.
    x = df.index.astype(str).tolist()

    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.6, 0.2, 0.2],
        subplot_titles=("Price", "Volume", "RSI"),
    )

    fig.add_trace(
        go.Candlestick(
            x=x,
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="OHLC",
        ),
        row=1,
        col=1,
    )

    overlay_lines = [
        ("vwap", "VWAP", "#FFD700"),
        ("ema_fast", "EMA 9", "#00BFFF"),
        ("ema_slow", "EMA 21", "#FF6347"),
        ("ema_50", "EMA 50", "#9370DB"),
    ]
    for col_name, label, color in overlay_lines:
        if col_name in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=x, y=df[col_name], name=label,
                    line=dict(width=1.5, color=color),
                ),
                row=1, col=1,
            )

    colors = [
        "#26a69a" if c >= o else "#ef5350"
        for c, o in zip(df["close"], df["open"], strict=True)
    ]
    fig.add_trace(
        go.Bar(x=x, y=df["volume"], name="Volume", marker_color=colors),
        row=2, col=1,
    )

    if "rsi" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=x, y=df["rsi"], name="RSI",
                line=dict(width=1.5, color="#AB47BC"),
            ),
            row=3, col=1,
        )
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)

    fig.update_layout(
        height=650,
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=20, t=40, b=20),
    )
    return fig


def _enrich(data: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Apply all indicators to fetched data."""
    config = get_config()
    return {
        t: apply_all(
            df,
            rsi_period=config.rsi_period,
            ema_fast=config.ema_fast,
            ema_slow=config.ema_slow,
            volume_sma_period=config.volume_sma_period,
            ema_trend_period=50,
            atr_period=14,
        )
        for t, df in data.items()
    }


# ---------------------------------------------------------------------------
# Page layout
# ---------------------------------------------------------------------------


@ui.page("/")
def index() -> None:
    """Main dashboard page."""
    config = get_config()
    wl_options = _build_watchlist_options()
    strat_options = _build_strategy_options()

    # --- Header with market status ---
    with ui.header().classes("items-center justify-between bg-blue-grey-10"):
        ui.label("Trading Scanner").classes("text-h5 text-bold")
        with ui.row().classes("items-center gap-4"):
            status = get_market_status()
            status_color = {
                "Open": "text-green",
                "Pre-Market": "text-orange",
                "After-Hours": "text-orange",
            }.get(status, "text-grey")
            ui.label(f"Market: {status}").classes(f"text-caption {status_color}")
            ui.label(f"Source: {config.data_source}").classes("text-caption text-grey")

    # --- Tabs ---
    with ui.tabs().classes("w-full") as tabs:
        scan_tab = ui.tab("Scan")
        analyze_tab = ui.tab("Analyze")
        watchlist_tab = ui.tab("Watchlists")

    with ui.tab_panels(tabs, value=scan_tab).classes("w-full"):
        # ==============================================================
        # SCAN PANEL
        # ==============================================================
        with ui.tab_panel(scan_tab):
            with ui.row().classes("w-full items-end gap-4"):
                wl_select = ui.select(
                    options=wl_options, label="Watchlist", value=next(iter(wl_options)),
                ).classes("w-64")
                strat_select = ui.select(
                    options=strat_options, label="Strategy", value=next(iter(strat_options)),
                ).classes("w-80")
                source_select = ui.select(
                    options=["yfinance", "ibkr"], label="Data source", value="yfinance",
                ).classes("w-40")
                scan_btn = ui.button("Run Scan", icon="search")

            scan_results_container = ui.column().classes("w-full mt-4")

            async def run_scan() -> None:
                scan_results_container.clear()
                wl_key = wl_select.value
                strat_key = strat_select.value
                data_source = DataSource(source_select.value)

                with scan_results_container:
                    ui.spinner("dots", size="xl")

                try:
                    tickers = get_watchlist(wl_key)
                    data = await run.io_bound(
                        fetch_tickers,
                        tickers, duration="1d", bar_size="5m",
                        source=data_source, config=config,
                    )
                except Exception as e:
                    scan_results_container.clear()
                    with scan_results_container:
                        ui.label(f"Error: {e}").classes("text-red")
                    return

                if not data:
                    scan_results_container.clear()
                    with scan_results_container:
                        ui.label("No data retrieved.").classes("text-red")
                    return

                enriched = _enrich(data)
                strat = get_strategy(strat_key)
                results = strat.scan_multiple(enriched)
                results.sort(
                    key=lambda r: {"strong": 0, "moderate": 1, "weak": 2}[r.strength]
                )

                scan_results_container.clear()
                with scan_results_container:
                    if not results:
                        ui.label("No matches found.").classes("text-yellow")
                    else:
                        ui.label(f"{len(results)} match(es) found").classes(
                            "text-green text-bold"
                        )
                        columns = [
                            {"name": "ticker", "label": "Ticker", "field": "ticker",
                             "sortable": True},
                            {"name": "signal", "label": "Signal", "field": "signal"},
                            {"name": "strength", "label": "Strength", "field": "strength",
                             "sortable": True},
                            {"name": "price", "label": "Price", "field": "price",
                             "sortable": True},
                            {"name": "rsi", "label": "RSI", "field": "rsi", "sortable": True},
                            {"name": "rvol", "label": "RVOL", "field": "rvol",
                             "sortable": True},
                            {"name": "ema_trend", "label": "EMA Trend",
                             "field": "ema_trend"},
                            {"name": "vwap_position", "label": "vs VWAP",
                             "field": "vwap_position"},
                            {"name": "details", "label": "Details", "field": "details"},
                        ]
                        rows = [r.model_dump() for r in results]
                        ui.table(
                            columns=columns, rows=rows, row_key="ticker",
                        ).classes("w-full")

            scan_btn.on_click(run_scan)

        # ==============================================================
        # ANALYZE PANEL
        # ==============================================================
        with ui.tab_panel(analyze_tab):
            with ui.row().classes("w-full items-end gap-4"):
                ticker_input = ui.input(
                    label="Ticker symbol", placeholder="e.g. AAPL",
                ).classes("w-48")
                analyze_source = ui.select(
                    options=["yfinance", "ibkr"], label="Data source", value="yfinance",
                ).classes("w-40")
                analyze_btn = ui.button("Analyze", icon="analytics")

            analyze_container = ui.column().classes("w-full mt-4")

            async def run_analyze() -> None:
                analyze_container.clear()
                ticker = (ticker_input.value or "").upper().strip()
                if not ticker:
                    with analyze_container:
                        ui.label("Enter a ticker symbol.").classes("text-yellow")
                    return

                data_source = DataSource(analyze_source.value)

                with analyze_container:
                    ui.spinner("dots", size="xl")

                try:
                    data = await run.io_bound(
                        fetch_tickers,
                        [ticker], duration="1d", bar_size="5m",
                        source=data_source, config=config,
                    )
                except Exception as e:
                    analyze_container.clear()
                    with analyze_container:
                        ui.label(f"Error: {e}").classes("text-red")
                    return

                if ticker not in data or data[ticker].empty:
                    analyze_container.clear()
                    with analyze_container:
                        ui.label(f"No data found for {ticker}.").classes("text-red")
                    return

                df = _enrich({ticker: data[ticker]})[ticker]
                last = df.iloc[-1]

                analyze_container.clear()
                with analyze_container:
                    # --- Strategy cards ---
                    ui.label("Strategy Signals").classes("text-h6 mt-2")
                    with ui.row().classes("w-full gap-4"):
                        for _key, strat_cls in STRATEGIES.items():
                            strat = strat_cls()
                            result = strat.scan_ticker(ticker, df)
                            with ui.card().classes("flex-1"):
                                ui.label(strat.name).classes("text-bold")
                                if result:
                                    ui.label(
                                        f"Match — {result.signal}"
                                    ).classes("text-green")
                                    ui.label(f"Strength: {result.strength}")
                                else:
                                    ui.label("No match").classes("text-red")
                                    ui.label(strat.description).classes(
                                        "text-caption text-grey"
                                    )

                    # --- Indicator snapshot ---
                    ui.label("Indicator Snapshot").classes("text-h6 mt-4")
                    with ui.row().classes("w-full gap-6 flex-wrap"):
                        for label, value in [
                            ("Price", _fmt(last.get("close"))),
                            ("RSI", _fmt(last.get("rsi"), 1)),
                            ("RVOL", _fmt(last.get("rvol"))),
                            ("ATR", _fmt(last.get("atr"))),
                            ("VWAP", _fmt(last.get("vwap"))),
                            ("EMA 9", _fmt(last.get("ema_fast"))),
                            ("EMA 21", _fmt(last.get("ema_slow"))),
                            ("EMA 50", _fmt(last.get("ema_50"))),
                            ("vs VWAP", str(last.get("price_vs_vwap") or "\u2014")),
                            ("EMA Trend", str(last.get("ema_trend") or "\u2014")),
                        ]:
                            with ui.column().classes("items-center"):
                                ui.label(label).classes("text-caption text-grey")
                                ui.label(value).classes("text-bold text-lg")

                    # --- Chart ---
                    ui.label("Chart").classes("text-h6 mt-4")
                    fig = _build_chart(df)
                    ui.plotly(fig).classes("w-full")

            analyze_btn.on_click(run_analyze)

        # ==============================================================
        # WATCHLISTS PANEL
        # ==============================================================
        with ui.tab_panel(watchlist_tab):
            wl_container = ui.column().classes("w-full")

            def refresh_watchlists() -> None:
                """Rebuild the watchlist view."""
                wl_container.clear()
                wl_data = list_watchlists()

                with wl_container:
                    # --- Watchlist table ---
                    ui.label("All Watchlists").classes("text-h6")
                    wl_columns = [
                        {"name": "name", "label": "Name", "field": "name", "sortable": True},
                        {"name": "count", "label": "Tickers", "field": "count",
                         "sortable": True},
                        {"name": "type", "label": "Type", "field": "type"},
                    ]
                    wl_rows = []
                    for display_name, count in wl_data.items():
                        is_builtin = display_name.endswith(" (built-in)")
                        raw_name = display_name.removesuffix(" (built-in)")
                        wl_rows.append({
                            "name": raw_name,
                            "count": count,
                            "type": "built-in" if is_builtin else "custom",
                        })
                    ui.table(
                        columns=wl_columns, rows=wl_rows, row_key="name",
                    ).classes("w-full")

                    ui.separator().classes("my-4")

                    # --- Add / edit watchlist ---
                    ui.label("Create or Update Watchlist").classes("text-h6")
                    with ui.row().classes("w-full items-end gap-4"):
                        wl_name_input = ui.input(
                            label="Watchlist name", placeholder="my_watchlist",
                        ).classes("w-48")
                        wl_tickers_input = ui.input(
                            label="Tickers (comma-separated)",
                            placeholder="AAPL, MSFT, NVDA",
                        ).classes("flex-1")
                        save_btn = ui.button("Save", icon="save")

                    wl_feedback = ui.column().classes("w-full mt-2")

                    def save_watchlist() -> None:
                        name = (wl_name_input.value or "").strip()
                        raw_tickers = (wl_tickers_input.value or "").strip()
                        wl_feedback.clear()

                        if not name or not raw_tickers:
                            with wl_feedback:
                                ui.label("Provide a name and tickers.").classes("text-yellow")
                            return

                        ticker_list = [
                            t.strip().upper() for t in raw_tickers.split(",") if t.strip()
                        ]
                        updated = add_to_watchlist(name, ticker_list)

                        with wl_feedback:
                            ui.label(
                                f"Saved '{name}' with {len(updated)} tickers."
                            ).classes("text-green")

                        # Refresh the table and scan tab's dropdown
                        refresh_watchlists()
                        wl_select.options = _build_watchlist_options()
                        wl_select.update()

                    save_btn.on_click(save_watchlist)

                    ui.separator().classes("my-4")

                    # --- Remove tickers from custom watchlist ---
                    ui.label("Remove Tickers from Custom Watchlist").classes("text-h6")
                    custom_names = [
                        r["name"] for r in wl_rows if r["type"] == "custom"
                    ]
                    if not custom_names:
                        ui.label("No custom watchlists yet.").classes("text-grey")
                    else:
                        with ui.row().classes("w-full items-end gap-4"):
                            rm_wl_select = ui.select(
                                options=custom_names, label="Watchlist",
                                value=custom_names[0],
                            ).classes("w-48")
                            rm_tickers_input = ui.input(
                                label="Tickers to remove",
                                placeholder="AAPL, MSFT",
                            ).classes("flex-1")
                            rm_btn = ui.button("Remove", icon="delete", color="red")

                        rm_feedback = ui.column().classes("w-full mt-2")

                        def remove_tickers() -> None:
                            name = rm_wl_select.value
                            raw = (rm_tickers_input.value or "").strip()
                            rm_feedback.clear()

                            if not name or not raw:
                                with rm_feedback:
                                    ui.label("Select a watchlist and tickers.").classes(
                                        "text-yellow"
                                    )
                                return

                            to_remove = [t.strip().upper() for t in raw.split(",") if t.strip()]
                            try:
                                remaining = remove_from_watchlist(name, to_remove)
                                with rm_feedback:
                                    ui.label(
                                        f"Updated '{name}': {len(remaining)} tickers remaining."
                                    ).classes("text-green")
                                refresh_watchlists()
                                wl_select.options = _build_watchlist_options()
                                wl_select.update()
                            except KeyError as e:
                                with rm_feedback:
                                    ui.label(str(e)).classes("text-red")

                        rm_btn.on_click(remove_tickers)

                    ui.separator().classes("my-4")

                    # --- Auto-generate watchlist ---
                    ui.label("Auto-Generate Watchlist").classes("text-h6")
                    ui.label(
                        "Scans day_trading_100 with all strategies and saves the top N scorers."
                    ).classes("text-caption text-grey")

                    with ui.row().classes("w-full items-end gap-4"):
                        gen_name_input = ui.input(
                            label="Watchlist name", placeholder="generated",
                        ).classes("w-48")
                        gen_top_input = ui.number(
                            label="Top N", value=10, min=1, max=100,
                        ).classes("w-24")
                        gen_source_select = ui.select(
                            options=["yfinance", "ibkr"], label="Source", value="yfinance",
                        ).classes("w-40")
                        gen_btn = ui.button("Generate", icon="auto_fix_high")

                    gen_container = ui.column().classes("w-full mt-2")

                    async def generate_watchlist() -> None:
                        name = (gen_name_input.value or "").strip()
                        top_n = int(gen_top_input.value or 10)
                        gen_container.clear()

                        if not name:
                            with gen_container:
                                ui.label("Provide a watchlist name.").classes("text-yellow")
                            return

                        with gen_container:
                            ui.spinner("dots", size="xl")

                        data_source = DataSource(gen_source_select.value)
                        strength_score = {"strong": 3, "moderate": 2, "weak": 1}

                        try:
                            pool = get_watchlist("day_trading_100")
                            data = await run.io_bound(
                                fetch_tickers,
                                pool, duration="1d", bar_size="5m",
                                source=data_source, config=config,
                            )
                        except Exception as e:
                            gen_container.clear()
                            with gen_container:
                                ui.label(f"Error: {e}").classes("text-red")
                            return

                        if not data:
                            gen_container.clear()
                            with gen_container:
                                ui.label("No data retrieved.").classes("text-red")
                            return

                        enriched = _enrich(data)
                        scores: dict[str, int] = {}
                        signals: dict[str, list[str]] = {}
                        for strat_cls in STRATEGIES.values():
                            strat = strat_cls()
                            for result in strat.scan_multiple(enriched):
                                scores[result.ticker] = (
                                    scores.get(result.ticker, 0)
                                    + strength_score.get(result.strength, 1)
                                )
                                signals.setdefault(result.ticker, []).append(
                                    f"{strat.name}:{result.strength}"
                                )

                        gen_container.clear()
                        if not scores:
                            with gen_container:
                                ui.label("No tickers matched any strategy.").classes(
                                    "text-yellow"
                                )
                            return

                        ranked = sorted(scores, key=lambda t: scores[t], reverse=True)[:top_n]
                        add_to_watchlist(name, ranked)

                        with gen_container:
                            ui.label(
                                f"Saved {len(ranked)} tickers to '{name}'."
                            ).classes("text-green text-bold")

                            gen_columns = [
                                {"name": "rank", "label": "#", "field": "rank"},
                                {"name": "ticker", "label": "Ticker", "field": "ticker"},
                                {"name": "score", "label": "Score", "field": "score",
                                 "sortable": True},
                                {"name": "signals", "label": "Signals", "field": "signals"},
                            ]
                            gen_rows = [
                                {
                                    "rank": i,
                                    "ticker": t,
                                    "score": scores[t],
                                    "signals": ", ".join(signals.get(t, [])),
                                }
                                for i, t in enumerate(ranked, 1)
                            ]
                            ui.table(
                                columns=gen_columns, rows=gen_rows, row_key="ticker",
                            ).classes("w-full")

                        refresh_watchlists()
                        wl_select.options = _build_watchlist_options()
                        wl_select.update()

                    gen_btn.on_click(generate_watchlist)

            # Initial render
            refresh_watchlists()


def start(host: str = "127.0.0.1", port: int = 8080) -> None:
    """Start the NiceGUI dashboard server."""
    ui.run(host=host, port=port, title="Trading Scanner", dark=True, reload=False)
