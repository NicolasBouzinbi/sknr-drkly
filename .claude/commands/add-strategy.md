Add a new scanning strategy called "$ARGUMENTS" to `src/trading_scanner/strategies/presets.py`.

Follow the same pattern as existing strategies:
1. Create a new class inheriting from `BaseStrategy`
2. Define `name` and `description` class attributes
3. Implement `scan_ticker` method with clear conditions
4. Register it in the `STRATEGIES` dict
5. Add tests in `tests/test_strategies/test_presets.py`

Ask me about the specific conditions/indicators this strategy should use before implementing.
