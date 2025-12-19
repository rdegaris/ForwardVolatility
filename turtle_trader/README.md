# Turtle Trader (Futures) — Baseline

Educational baseline implementation of the classic Turtle Trading trend-following system, oriented around futures.

This project provides:
- Donchian-channel breakout entries/exits (System 1 + System 2)
- ATR (N) volatility, unit sizing, pyramiding, and stop-loss logic
- A simple single-instrument backtester over OHLCV CSV
- A CLI to run backtests and emit a trades ledger + summary stats

Baseline defaults are now System 2 (55/20), per your spec.

> Note: This is research/backtesting scaffolding, not financial advice.

## Quick start

From the calculator repo folder:

1) Install deps

- `python -m pip install -r turtle_trader/requirements.txt`

2) Run commands from the project folder (so the package imports resolve)

- `cd turtle_trader`

2) Generate synthetic sample data

- `python -m turtle_trader.scripts.make_synth_data --out data/SYNTH.csv --years 5`

3) Run a backtest

- `python -m turtle_trader.cli backtest --config config.example.json --csv data/SYNTH.csv`

## Interactive Brokers

An IB adapter (via `ib_insync`) is included for fetching daily futures history.

Execution model (your choice):
- Signals: computed from **continuous** futures history (stable series for backtests)
- Execution: trade the **front-month** contract and roll when it gets too close to expiry

Example (continuous future):

- Start TWS / IB Gateway
- From the `turtle_trader` folder:
	- `python -m turtle_trader.scripts.ib_fetch_daily --symbol ES --exchange CME --cont --duration "10 Y" --out data/ES_CONT.csv`

	Resolve current front-month contract (for live execution):

	- `python -m turtle_trader.scripts.ib_front_month --symbol ES --exchange CME --min-dte 10`

	## Live runner (signals on continuous, trade front month)

	This is a baseline daily runner that:
	- reads a continuous-series CSV (signals)
	- resolves the current front month in IB (execution)
	- prints the stop-entry + protective-stop orders it would place

	Dry run (recommended first):

	- `python -m turtle_trader.scripts.ib_live_runner --config config.example.json --signal-csv data/ES_CONT.csv --dry-run`

	Live placement (only when you're ready):

	- `python -m turtle_trader.scripts.ib_live_runner --config config.example.json --signal-csv data/ES_CONT.csv --live`

## CSV format

Expected columns:
- `date` (YYYY-MM-DD)
- `open`, `high`, `low`, `close` (floats)
- optional: `volume`

## Next steps (typical)

- Add continuous futures roll logic + multiple instruments portfolio
- Plug in a market data provider (IQFeed, Polygon, IB, etc.)
- Add a broker/execution adapter + paper trading mode
- Add persistence (SQLite) and daily scheduler
