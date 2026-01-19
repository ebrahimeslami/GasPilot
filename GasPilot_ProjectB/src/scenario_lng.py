"""Scenario shocks for LNG flow model outputs.

Applies additive/multiplicative shocks to selected feature columns and re-predicts.

Example (PowerShell):
  python -m src.scenario_lng --model_path models/hgb_h7_lng_*.joblib --horizon 7 --shocks '{"hdd": 5, "outage_flag": 1}'
"""
import argparse, json
import pandas as pd
import joblib
from pathlib import Path
from src.config import DATA_DIR, REPORTS_DIR
from src.utils import numeric_only, utc_now_tag

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model_path", required=True, help="Path to joblib model (Pipeline).")
    ap.add_argument("--horizon", type=int, default=7)
    ap.add_argument("--shocks", required=True, help="JSON dict: {col: shock}. If value is float, adds to column.")
    ap.add_argument("--rows", type=int, default=60, help="Use last N rows.")
    args = ap.parse_args()

    shocks = json.loads(args.shocks)
    df = pd.read_csv(DATA_DIR/"features_lng.csv", parse_dates=["date"]).sort_values("date").reset_index(drop=True)
    last = df.tail(args.rows).copy()

    for col, val in shocks.items():
        if col not in last.columns:
            print(f"[WARN] shock col not found: {col}")
            continue
        last[col] = last[col] + float(val)

    model = joblib.load(args.model_path)
    Xp = numeric_only(last, drop_cols=("date",) + tuple([c for c in last.columns if c.startswith("target_t+")]))
    yhat = model.predict(Xp)

    out = pd.DataFrame({
        "date_input": last["date"],
        "target_date": last["date"] + pd.to_timedelta(args.horizon, unit="D"),
        "y_hat_scn": yhat
    })

    tag = utc_now_tag()
    out_path = REPORTS_DIR / f"scenario_h{args.horizon}_{tag}.csv"
    out.to_csv(out_path, index=False)
    print(f"[OK] wrote {out_path} rows={len(out)}")

if __name__ == "__main__":
    main()
