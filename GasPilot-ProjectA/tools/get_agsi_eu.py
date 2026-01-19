#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Fetch aggregated EU gas storage from AGSI API into data/eu_storage.csv.

- Uses AGSI API if $AGSI_API_KEY is set.
- Otherwise, tries a CSV fallback at data/external/eu_storage_fallback.csv
  (columns: date, level_pct)

Notes
- AGSI paging: the API returns paging metadata; you must iterate ?page=1..last_page.
- Output is daily with columns: date, level_pct (0-100).

Env vars
- AGSI_API_KEY: required for API mode
- AGSI_BASE_URL (optional): default https://agsi.gie.eu/api
"""

import os
import sys
import pandas as pd
import requests
from datetime import datetime, UTC

OUT = "data/eu_storage.csv"
FALLBACK = "data/external/eu_storage_fallback.csv"

def write_csv(df: pd.DataFrame, path: str = OUT):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=False)
    print(f"[OK] Wrote {path} rows={len(df)}")


def use_fallback():
    if not os.path.exists(FALLBACK):
        print(f"[ERR] No AGSI key and no fallback file at {FALLBACK}")
        sys.exit(2)
    df = pd.read_csv(FALLBACK, parse_dates=["date"])
    need = {"date", "level_pct"}
    if not need.issubset(df.columns):
        print(f"[ERR] Fallback must contain columns {need}")
        sys.exit(2)
    df = df.sort_values("date").reset_index(drop=True)
    write_csv(df)


def fetch_all_pages(base_url: str, headers: dict, params: dict) -> list:
    """AGSI returns paging metadata; iterate page=1..last_page."""
    items = []

    p0 = dict(params)
    p0["page"] = 1
    r = requests.get(base_url, headers=headers, params=p0, timeout=90)
    r.raise_for_status()
    js = r.json()
    last_page = int(js.get("last_page", 1))

    d0 = js.get("data", [])
    if d0:
        items.extend(d0)

    for page in range(2, last_page + 1):
        p = dict(params)
        p["page"] = page
        r = requests.get(base_url, headers=headers, params=p, timeout=90)
        r.raise_for_status()
        j = r.json()
        d = j.get("data", [])
        if d:
            items.extend(d)

    return items


def normalize_df(raw: pd.DataFrame) -> pd.DataFrame:
    # Date column variants
    date_col = None
    for c in ["gasDayStart", "gasDay", "date", "day", "period", "time"]:
        if c in raw.columns:
            date_col = c
            break
    if date_col is None:
        raise ValueError(f"No date-like column found. Columns: {list(raw.columns)}")

    out = pd.DataFrame()
    out["date"] = pd.to_datetime(raw[date_col], errors="coerce").dt.tz_localize(None)

    # Storage fullness percent
    level = None
    if "full" in raw.columns:
        level = pd.to_numeric(raw["full"], errors="coerce")
        if level.dropna().max() <= 1.5:
            level = level * 100.0
    elif "level" in raw.columns:
        level = pd.to_numeric(raw["level"], errors="coerce")
    elif {"gasInStorage", "workingGasVolume"}.issubset(raw.columns):
        g = pd.to_numeric(raw["gasInStorage"], errors="coerce")
        cap = pd.to_numeric(raw["workingGasVolume"], errors="coerce")
        level = (g / cap) * 100.0

    if level is None:
        raise ValueError("Could not derive level_pct from AGSI payload.")

    out["level_pct"] = level
    out = out.dropna(subset=["date", "level_pct"]).sort_values("date").reset_index(drop=True)
    return out


def fetch_agsi():
    key = os.environ.get("AGSI_API_KEY", "").strip()
    if not key:
        print("[INFO] $AGSI_API_KEY not set; using fallback if present")
        use_fallback()
        return

    base = os.environ.get("AGSI_BASE_URL", "https://agsi.gie.eu/api")
    headers = {"x-key": key, "Accept": "application/json"}
    params = {
        "country": "EU",
        "type": "aggregated",
        "from": "2017-01-01",
        "to": datetime.now(UTC).strftime("%Y-%m-%d"),
    }

    print(f"[INFO] GET {base} params={params} + paging")
    items = fetch_all_pages(base, headers, params)

    if not items:
        # Try capitalization variant if required by tenant
        params2 = dict(params)
        params2["type"] = "Aggregated"
        print("[INFO] Retrying with type=Aggregated")
        items = fetch_all_pages(base, headers, params2)

    if not items:
        raise RuntimeError("AGSI returned no items across pages. Check API key, base URL, or query params.")

    raw = pd.DataFrame(items)
    out = normalize_df(raw)
    write_csv(out)


if __name__ == "__main__":
    try:
        fetch_agsi()
    except KeyboardInterrupt:
        print("[INTERRUPTED]")
        sys.exit(1)
    except Exception as e:
        print(f"[ERR] {e}")
        sys.exit(2)
