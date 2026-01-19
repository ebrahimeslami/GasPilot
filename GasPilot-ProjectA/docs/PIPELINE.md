# Pipeline overview

This repository includes two layers:

1. **Full pipeline** (in `src/`) — end-to-end modular Project A workflow.
2. **Lite/QA pipeline** (in `tools/`) — minimal, robust path that always outputs CSVs for training QA.

Most users should start with the **Lite/QA pipeline** and then graduate to the full modules.

## Data contracts

### Core inputs

- `data/eia_henryhub.csv`
  - Columns: `date` (YYYY-MM-DD), `henry_hub` (float)
  - Produced by: `tools/eia_smoketest.py`

- `data/pjm_fuel_daily.csv`
  - Columns: `date`, `pjm_wind_mwh`, `pjm_solar_mwh`, `pjm_gas_mwh`
  - Produced by: `tools/get_pjm_gen_by_fuel.py` (reads manual PJM downloads)

### Optional inputs

- `data/eu_storage.csv`
  - Columns: `date`, `level_pct`
  - Produced by: `tools/get_agsi_eu.py` (AGSI API) or fallback CSV

- `data/cpc_610_us.csv`, `data/cpc_814_us.csv`
  - Columns: `date`, `index`
  - Produced by: `src/cpc_anomalies.py` after `src/cpc_raster.py`

## Lite workflow (recommended)

1. EIA Henry Hub
   - `python tools/eia_smoketest.py`

2. PJM fuel mix
   - Place your PJM yearly/monthly CSVs in `tools/external/`
   - Run: `python tools/get_pjm_gen_by_fuel.py --start 2017-01-01 --end 2025-12-01 --input_glob "tools/external/*.csv"`

3. EU storage (optional)
   - Set `AGSI_API_KEY` and run: `python tools/get_agsi_eu.py`

4. Build features
   - `python tools/build_features_lite.py`
   - Output: `data/features_eia.csv`

5. Train + forecast
   - `python tools/train_predict_lite.py --horizons 7 30 --models gbm rf`
   - Outputs:
     - `models/*_eia_lite.joblib`
     - `reports/forecast_h*_eia_*_lite.csv`

## Full pipeline

See module docstrings under `src/`. A typical sequence is:

- `python -m src.eia_process --horizons 7 30`
- `python -m src.train --source eia --horizon 7 --models rf gbm`
- `python -m src.predict --source eia --horizons 7 30 --model gbm`
- `python -m src.backtest_walkforward --source eia --horizon 7 --model gbm`
- `python -m src.scenario --source eia --horizon 7 --model gbm --shocks "{\"HDD\":-10}"`

