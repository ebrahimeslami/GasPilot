
# CPC GeoTIFF Raster → Grid CSV (no API)

Use CPC’s official FTP rasters (GeoTIFF) — easiest and most reliable.

Run:
```powershell
# Download latest 6–10 and 8–14 day rasters and convert to grid CSVs
python -m src.cpc_raster --products 610 814

# Aggregate to national/pop-weighted indices
python -m src.cpc_anomalies --products 610 814

# Rebuild features
python -m src.eia_process --horizons 7 30
```
This writes:
- `data/external/cpc_610_grid.csv`
- `data/external/cpc_814_grid.csv`
- `data/cpc_610_us.csv`
- `data/cpc_814_us.csv`
