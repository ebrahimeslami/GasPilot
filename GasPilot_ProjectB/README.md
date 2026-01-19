# GasPilot — Project B (LNG Export Flow Forecasting)

A GitHub-ready, modular Python pipeline to forecast U.S. LNG export terminal activity using **LNG feedgas / exports**, **weather**, **outage indicators**, and optional **AIS vessel departures**.

This repo is designed as an MVP with QA-friendly outputs: **train/backtest forecasts and final forecasts are written as CSV with date_input and target_date**.

## What this project does

1. Ingest time series
   - EIA v2 (generic fetch tool; configure your LNG series/route)
   - Manual AIS CSVs (merge to daily counts)
   - Optional weather and outage CSVs

2. Build features (`src/features_lng.py`)
   - Daily alignment, lags, rolling stats, calendar features
   - Targets for 7- and 30-day horizons

3. Train + walk-forward backtest (`src/train_lng.py`)
   - Expanding-window backtest outputs (CSV)
   - Saves fitted models (joblib)
   - Produces QA forecast CSVs

4. Scenario analysis (`src/scenario_lng.py`)
   - Apply shocks to features and re-predict

## Quickstart (PowerShell)

```powershell
cd GasPilot-ProjectB_LNGFlow
python -m venv .venv
.\.venv\Scripts\Activate
pip install -r requirements.txt

# 1) Fetch a target series from EIA v2 (configure route/series)
$env:EIA_API_KEY="<YOUR_KEY>"
python tools/eia_fetch_generic.py --route "natural-gas/pri/fut/data" --series RNGWHHD --start 2017-01-01 --out data/external/lng_feedgas.csv

# Rename/format lng_feedgas.csv to have columns: date, feedgas_bcf_d
# 2) (Optional) AIS daily
python tools/ais_merge.py --input_glob "data/external/ais_*.csv" --time_col timestamp --out data/external/ais_daily.csv

# 3) Build features
python -m src.features_lng --target lng_feedgas.csv --target_col feedgas_bcf_d --horizons 7 30

# 4) Train + backtest + forecast
python -m src.train_lng --models hgb rf ridge --horizons 7 30

# 5) Scenario shock
python -m src.scenario_lng --model_path models/hgb_h7_lng_*.joblib --horizon 7 --shocks '{"dep_7d": 5, "outage_flag": 1}'
```

## Data notes

EIA v2 LNG feedgas and exports series vary by dataset and may require facets. Use EIA's Series ID Search to locate LNG-related series and then use `tools/eia_fetch_generic.py` to retrieve them.

## License

MIT
