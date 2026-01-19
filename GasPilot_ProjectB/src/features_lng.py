"""Build features for Project B (LNG export flow forecasting).

Inputs (CSV):
  data/external/lng_feedgas.csv        (date, feedgas_bcf_d) OR use tools/eia_fetch_generic.py to pull series
  data/external/lng_exports.csv        (date, exports_bcf_d) optional target alternative
  data/external/ais_daily.csv          (date, departures/arrivals/unique_vessels) optional
  data/external/outages.csv            (date, outage_flag or outage_pct) optional
  data/external/weather_us.csv         (date, hdd, cdd, temp) optional

Outputs:
  data/features_lng.csv  (date + engineered features + targets for horizons)

Design:
  - Anchors on target series (feedgas_bcf_d by default)
  - Daily reindexing with ffill/bfill for slowly varying features
  - QA columns: date_input and target_date are created in forecast step.
"""
import argparse
import pandas as pd
import numpy as np
from pathlib import Path
from src.config import DATA_DIR, EXTERNAL_DIR
from src.utils import backfill_daily, save_csv

def load_csv(name: str, required: bool = False) -> pd.DataFrame | None:
    p = EXTERNAL_DIR / name
    if not p.exists():
        if required:
            raise FileNotFoundError(f"Missing {p}")
        return None
    df = pd.read_csv(p, parse_dates=["date"])
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
    return df

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default="lng_feedgas.csv", help="Target series CSV in data/external/")
    ap.add_argument("--target_col", default="feedgas_bcf_d")
    ap.add_argument("--horizons", nargs="+", type=int, default=[7,30])
    args = ap.parse_args()

    tgt = load_csv(args.target, required=True)
    if args.target_col not in tgt.columns:
        # allow single value col named differently
        val_cols = [c for c in tgt.columns if c != "date"]
        if len(val_cols) != 1:
            raise ValueError(f"Target col {args.target_col} not found and can't infer single value column.")
        tgt = tgt.rename(columns={val_cols[0]: args.target_col})

    df = backfill_daily(tgt[["date", args.target_col]])
    df = df.rename(columns={args.target_col: "y"})

    # Optional merges
    for name in ["ais_daily.csv","outages.csv","weather_us.csv","lng_exports.csv"]:
        other = load_csv(name, required=False)
        if other is not None:
            df = df.merge(other, on="date", how="left")

    # Fill numeric gaps
    num = df.select_dtypes("number").columns
    df[num] = df[num].ffill().bfill().fillna(0.0)

    # Feature engineering
    df["dow"] = df["date"].dt.dayofweek
    df["month"] = df["date"].dt.month
    df["is_wknd"] = (df["dow"]>=5).astype(int)

    for lag in [1,2,7,14]:
        df[f"y_lag{lag}"] = df["y"].shift(lag)
    df["y_ma7"] = df["y"].rolling(7, min_periods=1).mean()
    df["y_ma30"] = df["y"].rolling(30, min_periods=1).mean()

    # If AIS exists, add rolling sums
    if "departures" in df.columns:
        df["dep_7d"] = df["departures"].rolling(7, min_periods=1).sum()
        df["dep_14d"] = df["departures"].rolling(14, min_periods=1).sum()

    # Targets
    for H in args.horizons:
        df[f"target_t+{H}"] = df["y"].shift(-H)

    # Keep rows where targets exist
    keep = df["y"].notna()
    for H in args.horizons:
        keep &= df[f"target_t+{H}"].notna()
    out = df.loc[keep].reset_index(drop=True)

    save_csv(out, DATA_DIR / "features_lng.csv")
    print(f"[OK] wrote {DATA_DIR/'features_lng.csv'} rows={len(out)}")

if __name__ == "__main__":
    main()
