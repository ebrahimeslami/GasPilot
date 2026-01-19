"""Train LNG flow forecasting models with walk-forward backtest.

Reads: data/features_lng.csv
Writes:
  models/{model}_h{H}_lng_{timestamp}.joblib
  reports/backtest_h{H}_{model}.csv    (date_input, target_date, y_true, y_hat)
  reports/forecast_h{H}_{model}.csv    (date_input, target_date, y_hat)

Models:
  - rf: RandomForestRegressor
  - hgb: HistGradientBoostingRegressor (handles NaNs)
  - ridge: linear baseline

Method:
  - Walk-forward evaluation with expanding window.
  - Final fit on all available data for forecasting.
"""
import argparse, os
import numpy as np
import pandas as pd
import joblib
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor
from src.config import DATA_DIR, MODELS_DIR, REPORTS_DIR
from src.utils import utc_now_tag, numeric_only

def make_model(name: str):
    if name == "rf":
        return Pipeline([("impute", SimpleImputer(strategy="median")),
                         ("model", RandomForestRegressor(n_estimators=500, random_state=42, n_jobs=-1))])
    if name == "ridge":
        return Pipeline([("impute", SimpleImputer(strategy="median")),
                         ("model", Ridge(alpha=1.0))])
    if name == "hgb":
        # handles NaNs, but we keep imputer for safety
        return Pipeline([("impute", SimpleImputer(strategy="median")),
                         ("model", HistGradientBoostingRegressor(random_state=42))])
    raise ValueError("model must be one of: rf, ridge, hgb")

def walk_forward(df: pd.DataFrame, H: int, model_name: str, min_train_days: int = 365, step: int = 7):
    target = f"target_t+{H}"
    y = df[target].astype(float)
    X = numeric_only(df, drop_cols=("date",) + tuple([c for c in df.columns if c.startswith("target_t+")]))
    # align
    keep = y.notna()
    X = X.loc[keep].reset_index(drop=True)
    y = y.loc[keep].reset_index(drop=True)
    dates = df.loc[keep, "date"].reset_index(drop=True)

    preds = []
    model = make_model(model_name)

    n = len(df.loc[keep])
    for i in range(min_train_days, n - 1, step):
        X_train, y_train = X.iloc[:i], y.iloc[:i]
        X_test, y_test = X.iloc[i:i+step], y.iloc[i:i+step]
        if len(X_test) == 0:
            break
        model.fit(X_train, y_train)
        y_hat = model.predict(X_test)
        for j in range(len(X_test)):
            date_input = dates.iloc[i + j]
            preds.append({
                "date_input": date_input,
                "target_date": date_input + pd.to_timedelta(H, unit="D"),
                "y_true": float(y_test.iloc[j]),
                "y_hat": float(y_hat[j]),
            })

    bt = pd.DataFrame(preds)
    return bt

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=["hgb","rf","ridge"], choices=["hgb","rf","ridge"])
    ap.add_argument("--horizons", nargs="+", type=int, default=[7,30])
    ap.add_argument("--min_train_days", type=int, default=365)
    ap.add_argument("--step", type=int, default=7)
    ap.add_argument("--forecast_rows", type=int, default=30, help="How many last rows to forecast for QA.")
    args = ap.parse_args()

    df = pd.read_csv(DATA_DIR/"features_lng.csv", parse_dates=["date"]).sort_values("date").reset_index(drop=True)

    for H in args.horizons:
        target = f"target_t+{H}"
        y = df[target].astype(float)
        keep = y.notna()
        dfH = df.loc[keep].reset_index(drop=True)

        for m in args.models:
            bt = walk_forward(dfH, H, m, min_train_days=args.min_train_days, step=args.step)
            bt_path = REPORTS_DIR / f"backtest_h{H}_{m}.csv"
            bt.to_csv(bt_path, index=False)
            print(f"[OK] wrote {bt_path} rows={len(bt)}")

            # final fit on all for forecasting
            X_all = numeric_only(dfH, drop_cols=("date",) + tuple([c for c in dfH.columns if c.startswith('target_t+')]))
            y_all = dfH[target].astype(float)
            model = make_model(m)
            model.fit(X_all, y_all)

            tag = utc_now_tag()
            mpath = MODELS_DIR / f"{m}_h{H}_lng_{tag}.joblib"
            joblib.dump(model, mpath)
            print(f"[OK] saved {mpath}")

            # forecast last N rows (QA)
            last = dfH.tail(args.forecast_rows).reset_index(drop=True)
            Xp = numeric_only(last, drop_cols=("date",) + tuple([c for c in last.columns if c.startswith('target_t+')]))
            yhat = model.predict(Xp)
            out = pd.DataFrame({
                "date_input": last["date"],
                "target_date": last["date"] + pd.to_timedelta(H, unit="D"),
                "y_hat": yhat
            })
            fpath = REPORTS_DIR / f"forecast_h{H}_{m}.csv"
            out.to_csv(fpath, index=False)
            print(f"[OK] wrote {fpath} rows={len(out)}")

if __name__ == "__main__":
    main()
