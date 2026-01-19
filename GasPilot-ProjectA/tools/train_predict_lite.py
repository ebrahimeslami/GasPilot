#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Train + forecast (lite) using data/features_eia.csv.

Minimal, reliable QA path:
- numeric-only features
- NaN/inf sanitization
- median imputation (Pipeline)
- saves models and forecast CSVs with date_input + target_date

Outputs:
- models/{gbm|rf}_h{H}_eia_lite.joblib
- reports/forecast_h{H}_eia_{gbm|rf}_lite.csv
"""

import os
import argparse
import joblib
import numpy as np
import pandas as pd

from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor

MODELS_DIR = "models"
REPORTS_DIR = "reports"
FEATURES_PATH = "data/features_eia.csv"


def ensure_dirs():
    os.makedirs(MODELS_DIR, exist_ok=True)
    os.makedirs(REPORTS_DIR, exist_ok=True)


def load_features(path: str = FEATURES_PATH) -> pd.DataFrame:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing {path}")
    df = pd.read_csv(path, parse_dates=["date"]).sort_values("date").reset_index(drop=True)
    return df


def build_Xy(df: pd.DataFrame, H: int):
    y_col = f"target_t+{H}"
    if y_col not in df.columns:
        raise KeyError(f"Missing {y_col} in features file")

    y = df[y_col].astype(float)

    drop_cols = ["date"] + [c for c in df.columns if c.startswith("target_t+")]
    X = df.drop(columns=drop_cols, errors="ignore").copy()

    # coerce any non-numeric columns
    for c in X.columns:
        if not np.issubdtype(X[c].dtype, np.number):
            X[c] = pd.to_numeric(X[c], errors="coerce")

    # infinities -> NaN
    X = X.replace([np.inf, -np.inf], np.nan)

    # keep only rows where y exists
    keep = y.notna()
    X = X.loc[keep].reset_index(drop=True)
    y = y.loc[keep].reset_index(drop=True)

    return X, y, keep


def make_model(name: str) -> Pipeline:
    if name == "gbm":
        base = GradientBoostingRegressor(random_state=42)
    elif name == "rf":
        base = RandomForestRegressor(n_estimators=400, random_state=42, n_jobs=-1)
    else:
        raise ValueError("model name must be 'gbm' or 'rf'")

    return Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("model", base),
    ])


def make_forecast(df: pd.DataFrame, pipe: Pipeline, H: int, keep_mask: pd.Series) -> pd.DataFrame:
    date_input = df.loc[keep_mask, "date"].reset_index(drop=True)
    target_date = date_input + pd.to_timedelta(H, unit="D")

    drop_cols = ["date"] + [c for c in df.columns if c.startswith("target_t+")]
    Xfull = df.drop(columns=drop_cols, errors="ignore").copy()

    for c in Xfull.columns:
        if not np.issubdtype(Xfull[c].dtype, np.number):
            Xfull[c] = pd.to_numeric(Xfull[c], errors="coerce")
    Xfull = Xfull.replace([np.inf, -np.inf], np.nan)

    Xpred = Xfull.loc[keep_mask].reset_index(drop=True)
    y_hat = pipe.predict(Xpred)

    return pd.DataFrame({
        "date_input": date_input,
        "target_date": target_date,
        "y_hat": y_hat,
    })


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--horizons", nargs="+", type=int, default=[7, 30])
    ap.add_argument("--models", nargs="+", default=["gbm", "rf"], choices=["gbm", "rf"])
    args = ap.parse_args()

    ensure_dirs()
    df = load_features()

    for H in args.horizons:
        X, y, keep_mask = build_Xy(df, H)
        if len(X) == 0:
            raise RuntimeError(f"No training rows for horizon {H}. Check features_eia.csv and targets.")

        for m in args.models:
            pipe = make_model(m)
            pipe.fit(X, y)

            mpath = os.path.join(MODELS_DIR, f"{m}_h{H}_eia_lite.joblib")
            joblib.dump(pipe, mpath)
            print(f"[OK] saved {mpath} | rows={len(X)} cols={X.shape[1]}")

            fc = make_forecast(df, pipe, H, keep_mask)
            fpath = os.path.join(REPORTS_DIR, f"forecast_h{H}_eia_{m}_lite.csv")
            fc.to_csv(fpath, index=False)
            print(f"[OK] wrote {fpath} rows={len(fc)}")


if __name__ == "__main__":
    main()
