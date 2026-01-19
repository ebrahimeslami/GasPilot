
# CPC (6–10, 8–14 day) Anomalies, AGSI EU Storage, and Summary Plotter

## CPC anomalies
Option 1 (netCDF via env):
  - set CPC_URL_610 and CPC_URL_814 to CPC netCDF URLs (requires xarray)
Option 2 (CSV fallback):
  - place data/external/cpc_610_grid.csv and cpc_814_grid.csv with columns: date, lat, lon, t_anom
Optional population weighting:
  - data/external/pop_grid_conus.csv with columns: lat, lon, pop

Run:
  python -m src.cpc_anomalies --products 610 814

Outputs:
  data/cpc_610_us.csv, data/cpc_814_us.csv

## EU storage (AGSI+)
  $env:AGSI_API_KEY="YOUR_KEY"
  python -m src.agsi_eu_storage

Fallback:
  data/external/eu_storage.csv (date, level_pct)

## Rebuild features and walk-forward
  python -m src.eia_process --horizons 7 30
  python -m src.backtest_walkforward --source eia --horizon 7 --model rf --start_train_days 730 --step_days 7

## Quick plot
  python -m src.plot_summary --source eia --horizon 7 --model rf
  -> reports/summary_h7_eia_rf.png
