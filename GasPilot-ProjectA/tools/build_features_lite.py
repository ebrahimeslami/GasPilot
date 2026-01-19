#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Builds a real-data feature table for Project A.

Anchors to a daily calendar over Henry Hub availability, then merges:
- data/eia_henryhub.csv (required)
- data/pjm_fuel_daily.csv (required)
- data/eu_storage.csv (optional; level_pct)
- data/cpc_610_us.csv, data/cpc_814_us.csv (optional; index)

Outputs:
- data/features_eia.csv (includes date, feature columns, and targets target_t+7 / target_t+30)
"""

import os
import sys
import numpy as np
import pandas as pd

REQUIRED = [
    "data/eia_henryhub.csv",
    "data/pjm_fuel_daily.csv",
]

OPTIONAL = [
    "data/eu_storage.csv",
    "data/cpc_610_us.csv",
    "data/cpc_814_us.csv",
]


def rd(path: str, must: bool = True):
    if not os.path.exists(path):
        if must:
            print(f"[ERR] Missing required file: {path}")
        return None
    return pd.read_csv(path, parse_dates=["date"])


def main():
    os.makedirs("data", exist_ok=True)

    hh = rd(REQUIRED[0], must=True)
    pjm = rd(REQUIRED[1], must=True)
    if hh is None or pjm is None:
        sys.exit(2)

    eu = rd(OPTIONAL[0], must=False)
    c610 = rd(OPTIONAL[1], must=False)
    c814 = rd(OPTIONAL[2], must=False)

    # Continuous daily grid on Henry Hub window
    hh = hh.sort_values("date").reset_index(drop=True)
    full_dates = pd.date_range(hh["date"].min(), hh["date"].max(), freq="D")
    hh = hh.set_index("date").reindex(full_dates).rename_axis("date").reset_index()

    # Merge all features LEFT onto HH calendar
    df = hh.merge(pjm, on="date", how="left")
    if eu is not None:
        df = df.merge(eu, on="date", how="left")
    if c610 is not None:
        if "index" in c610.columns:
            c610 = c610.rename(columns={"index": "cpc_610_idx"})
        df = df.merge(c610, on="date", how="left")
    if c814 is not None:
        if "index" in c814.columns:
            c814 = c814.rename(columns={"index": "cpc_814_idx"})
        df = df.merge(c814, on="date", how="left")

    # Fill feature gaps (not target)
    fill_cols = [c for c in df.columns if c not in ["date", "henry_hub"]]
    if fill_cols:
        df[fill_cols] = df[fill_cols].ffill().bfill()

    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if num_cols:
        df[num_cols] = df[num_cols].fillna(0.0)

    # Calendar + lag features
    df["dow"] = df["date"].dt.dayofweek
    df["month"] = df["date"].dt.month
    df["is_wknd"] = (df["dow"] >= 5).astype(int)

    for lag in (1, 7, 14):
        df[f"henry_hub_lag{lag}"] = df["henry_hub"].shift(lag)

    df["henry_hub_ma7"] = df["henry_hub"].rolling(7, min_periods=1).mean()
    df["henry_hub_ma30"] = df["henry_hub"].rolling(30, min_periods=1).mean()

    # Targets
    for H in (7, 30):
        df[f"target_t+{H}"] = df["henry_hub"].shift(-H)

    # Keep only rows where HH and targets exist
    keep = df["henry_hub"].notna()
    for H in (7, 30):
        keep &= df[f"target_t+{H}"].notna()
    df = df[keep].reset_index(drop=True)

    out = "data/features_eia.csv"
    df.to_csv(out, index=False)

    print(f"[OK] Wrote {out} rows={len(df)} cols={len(df.columns)}")


if __name__ == "__main__":
    main()
