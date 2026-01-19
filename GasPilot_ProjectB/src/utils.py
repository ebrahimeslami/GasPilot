import os
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

import pandas as pd

def utc_now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

def read_csv_safe(path: Path, parse_dates=("date",)) -> Optional[pd.DataFrame]:
    if not path.exists():
        return None
    try:
        return pd.read_csv(path, parse_dates=list(parse_dates))
    except Exception:
        return pd.read_csv(path)

def ensure_date(df: pd.DataFrame, col: str = "date") -> pd.DataFrame:
    df = df.copy()
    df[col] = pd.to_datetime(df[col]).dt.tz_localize(None)
    return df

def save_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)

def try_json_load(s: str) -> Dict[str, Any]:
    # Accept either JSON string or @path/to/file.json
    s = (s or "").strip()
    if not s:
        return {}
    if s.startswith("@"):
        with open(s[1:], "r", encoding="utf-8") as f:
            return json.load(f)
    return json.loads(s)

def backfill_daily(df: pd.DataFrame, date_col="date") -> pd.DataFrame:
    df = df.sort_values(date_col)
    idx = pd.date_range(df[date_col].min(), df[date_col].max(), freq="D")
    out = df.set_index(date_col).reindex(idx).rename_axis(date_col).reset_index()
    # forward/back fill numeric
    num = out.select_dtypes("number").columns
    out[num] = out[num].ffill().bfill()
    return out

def numeric_only(df: pd.DataFrame, drop_cols=("date",)) -> pd.DataFrame:
    X = df.drop(columns=[c for c in drop_cols if c in df.columns], errors="ignore").copy()
    for c in X.columns:
        if str(X[c].dtype) == "object":
            X[c] = pd.to_numeric(X[c], errors="coerce")
    X = X.replace([float("inf"), float("-inf")], pd.NA)
    return X
