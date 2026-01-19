# Pipeline details (Project B)

## Inputs

All raw files go in `data/external/`.

Required for training:
- `lng_feedgas.csv` with columns: `date`, `feedgas_bcf_d` (daily)

Optional:
- `ais_daily.csv` with columns: `date`, `departures`, optional `arrivals`, `unique_vessels`
- `outages.csv` with columns: `date`, `outage_flag` or `outage_pct`
- `weather_us.csv` with columns: `date` and any numeric weather fields (e.g., hdd, cdd, temp)
- `lng_exports.csv` with columns: `date`, `exports_bcf_d` (can be used as an extra feature or alternative target)

## Feature engineering

`src/features_lng.py`:
- Daily date index alignment
- ffill/bfill on numeric features (slowly varying indicators)
- Lag and rolling mean features on the target
- Optional rolling sums on AIS departures
- Targets: `target_t+7`, `target_t+30`

## Modeling

`src/train_lng.py`:
- Walk-forward backtest (expanding window), step size default 7 days
- Models:
  - `hgb` HistGradientBoostingRegressor (robust to missing values)
  - `rf` RandomForestRegressor (nonlinear baseline)
  - `ridge` linear baseline
- Outputs CSV:
  - Backtest: `reports/backtest_h{H}_{model}.csv`
  - Forecast: `reports/forecast_h{H}_{model}.csv`
Both include `date_input`, `target_date`.

## Scenarios

`src/scenario_lng.py`:
- Applies additive shocks to specified feature columns on the most recent N rows
- Writes scenario forecast to CSV in `reports/`.
