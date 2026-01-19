# GasPilot Project A — US Gas Fundamentals → Henry Hub Forecast (MVP)

This repo is a **GitHub-ready MVP** for a natural gas analytics workflow:

1) Ingest fundamentals (EIA v2) + power/gas proxy (PJM fuel mix CSVs)
2) Optional: EU storage (AGSI) and CPC weather indices
3) Build a time-aligned feature table with explicit **date_input** and **target_date**
4) Train lightweight ML baselines (GBM, RF)
5) Generate QA-friendly forecast CSVs

The project is intentionally modular: each Python file can be run and improved independently.

---

## Repo structure

- `tools/`
  - `eia_smoketest.py` — downloads Henry Hub (RNGWHHD) via EIA v2 and writes `data/eia_henryhub.csv`
  - `get_pjm_gen_by_fuel.py` — merges your PJM exported CSVs and writes `data/pjm_fuel_daily.csv`
  - `get_agsi_eu.py` — downloads EU storage level percent and writes `data/eu_storage.csv` (optional)
  - `build_features_lite.py` — creates `data/features_eia.csv` from real inputs (QA-first)
  - `train_predict_lite.py` — trains and writes forecast CSVs with date columns
- `src/`
  - Full pipeline modules (walk-forward backtest, scenarios, plotting, etc.)
- `data/`
  - Generated datasets (CSV) and external downloads
- `models/`
  - Serialized scikit-learn models (`.joblib`)
- `reports/`
  - Forecast CSVs and diagnostic outputs

---

## Quickstart (real data)

### 1) Create and activate a venv

Windows PowerShell:

```powershell
cd D:\Business\GasPilot\GasPilot-ProjectA
python -m venv .venv
.\.venv\Scripts\Activate
pip install -r requirements.txt
```

### 2) Provide keys (EIA is required)

```powershell
$env:EIA_API_KEY = "<YOUR_EIA_KEY>"
# Optional
$env:AGSI_API_KEY = "<YOUR_AGSI_KEY>"
```

### 3) PJM: export & merge

Download PJM "Gen by Fuel" history as CSVs (yearly or monthly) and place them in:

- `tools/external/` (recommended)

Then:

```powershell
python tools/get_pjm_gen_by_fuel.py --start 2017-01-01 --end 2025-12-01 --input_glob "D:\Business\GasPilot\GasPilot-ProjectA\tools\external\*.csv"
```

### 4) EIA Henry Hub

```powershell
python tools/eia_smoketest.py
```

### 5) Optional EU storage (AGSI)

```powershell
python tools/get_agsi_eu.py
```

### 6) Build features

```powershell
python tools/build_features_lite.py
```

### 7) Train + forecast

```powershell
python tools/train_predict_lite.py --horizons 7 30 --models gbm rf
```

Forecasts:

- `reports/forecast_h7_eia_gbm_lite.csv`
- `reports/forecast_h30_eia_gbm_lite.csv`
- `reports/forecast_h7_eia_rf_lite.csv`
- `reports/forecast_h30_eia_rf_lite.csv`

Each includes:

- `date_input` — the date the model sees
- `target_date` — date being forecast
- `y_hat` — forecasted Henry Hub value

---

## Notes

- This MVP uses simple baseline models. The `src/` directory contains a richer pipeline (walk-forward backtesting, scenarios, plotting). The `tools/` scripts are the "known-good" path for reproducible real-data runs.
- If you prefer **no AGSI API**, create a fallback file at `data/external/eu_storage_fallback.csv` with columns `date,level_pct`.

---

## License

MIT (see `LICENSE`).
