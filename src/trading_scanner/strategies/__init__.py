"""Scanning strategies with auto-discovery.

Any module in this package that defines a ``BaseStrategy`` subclass is
automatically registered at import time via ``__init_subclass__``.  To add
a new strategy, create a ``.py`` file in this directory with a class that
inherits from ``BaseStrategy`` — no manual registration required.
"""

import importlib
import pkgutil

from trading_scanner.strategies.base import BaseStrategy, ScanResult

# Auto-import every sibling module so their BaseStrategy subclasses register.
for _importer, _modname, _ispkg in pkgutil.iter_modules(__path__):
    if _modname != "base":
        importlib.import_module(f"{__name__}.{_modname}")

STRATEGIES: dict[str, type[BaseStrategy]] = BaseStrategy._registry


def get_strategy(name: str) -> BaseStrategy:
    """Get a strategy instance by name.

    Args:
        name: Strategy key (e.g. ``'abcd_pattern'``).

    Returns:
        Instantiated strategy.

    Raises:
        KeyError: If strategy name is not found.
    """
    if name not in STRATEGIES:
        available = ", ".join(STRATEGIES.keys())
        raise KeyError(f"Strategy '{name}' not found. Available: {available}")
    return STRATEGIES[name]()


__all__ = ["STRATEGIES", "BaseStrategy", "ScanResult", "get_strategy"]
