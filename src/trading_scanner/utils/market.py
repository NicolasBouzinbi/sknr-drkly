"""Market hours and trading day utilities."""

from datetime import datetime, time
from zoneinfo import ZoneInfo

US_EASTERN = ZoneInfo("America/New_York")

MARKET_OPEN = time(9, 30)
MARKET_CLOSE = time(16, 0)
PRE_MARKET_OPEN = time(4, 0)
AFTER_HOURS_CLOSE = time(20, 0)


def is_market_open() -> bool:
    """Check if the US stock market is currently in regular trading hours.

    Returns:
        True if currently within regular NYSE/NASDAQ trading hours (9:30-16:00 ET),
        on a weekday.
    """
    now = datetime.now(US_EASTERN)
    if now.weekday() >= 5:  # Saturday or Sunday
        return False
    return MARKET_OPEN <= now.time() <= MARKET_CLOSE


def is_trading_day() -> bool:
    """Check if today is a trading day (weekday).

    Note: Does not account for market holidays.

    Returns:
        True if today is Monday-Friday.
    """
    now = datetime.now(US_EASTERN)
    return now.weekday() < 5


def get_market_status() -> str:
    """Get a human-readable market status string.

    Returns:
        Status string: "Open", "Pre-Market", "After-Hours", or "Closed".
    """
    now = datetime.now(US_EASTERN)

    if now.weekday() >= 5:
        return "Closed (Weekend)"

    current_time = now.time()

    if MARKET_OPEN <= current_time <= MARKET_CLOSE:
        return "Open"
    if PRE_MARKET_OPEN <= current_time < MARKET_OPEN:
        return "Pre-Market"
    if MARKET_CLOSE < current_time <= AFTER_HOURS_CLOSE:
        return "After-Hours"
    return "Closed"
