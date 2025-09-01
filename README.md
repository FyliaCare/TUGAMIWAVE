# TUGAMIWAVE — FX Routing & Arbitrage Dashboard

A full-featured Streamlit app to run your Malawi–India–Ghana corridor operations.
It models bank charges, corridor fees, live routes, and arbitrage scans.

## Quick start
```bash
# 1) (optional) create and activate a virtualenv
python -m venv .venv && . .venv/Scripts/activate  # on Windows
# or: source .venv/bin/activate                    # on macOS/Linux

# 2) install dependencies
pip install -r requirements.txt

# 3) run the app
streamlit run app.py
```

## What’s inside
- **Dashboard**: KPIs, balances, P&L, route win/loss, corridor health.
- **Rates**: manage MWK/INR/GHS rates, spreads, and counterparties.
- **Routes Simulator**: simulate flows like GHS→INR→MWK→GHS with fees & slippage.
- **Arbitrage Scanner**: graph search for profitable cycles across currencies.
- **Fees Calculator**: configure per-bank fixed/percent fees, FX spreads, network costs.
- **Ledger**: journal of transfers, settlements, counterparties, and reconciliation.
- **Risk & Compliance**: limits, exposure, counterparty scorecards, alerts.
- **Settings**: company profile (TUGAMIWAVE), corridors, currencies, and defaults.

Data is persisted in a local SQLite DB (`tugamiwave.db`) created on first run and
seeded from CSVs in `data/`. You can also work only from CSVs if you prefer.

## Environment
Copy `.env.example` to `.env` and adjust values. The app works without `.env` too.

## Notes
This is an offline-ready starter. Plug in real rate feeds or bank APIs later by
implementing providers in `src/fx.py` and `src/db.py`.
