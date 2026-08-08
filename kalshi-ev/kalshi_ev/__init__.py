"""kalshi_ev — a fee-aware expected-value modeling toolkit for Kalshi markets.

Modules:
    fees        Kalshi taker-fee math.
    ev          Expected value, Kelly sizing, and trade decisions.
    client      Public (unauthenticated) Kalshi API client + orderbook views.
    calibration Favorite-longshot calibration fitted on settled markets.
    weather     NWS-forecast-based probabilities for high-temperature markets.
    arbitrage   Structural (risk-free-ish) mispricing scanner within events.
    data        Historical snapshot collection for calibration/backtesting.
    backtest    Walk-forward simulation of the calibrated strategy.
    cli         Command-line interface (`python -m kalshi_ev`).
"""

__version__ = "0.1.0"
