#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Simple EIA v2 Henry Hub (RNGWHHD) fetcher.

Writes: data/eia_henryhub.csv (date, henry_hub)
Requires: env var EIA_API_KEY
"""

import os
import sys
import requests
import pandas as pd

API = os.environ.get("EIA_API_KEY", "").strip()
if not API:
    print("[ERR] EIA_API_KEY not set")
    sys.exit(2)

URL = "https://api.eia.gov/v2/natural-gas/pri/fut/data/"
PARAMS = {
    "frequency": "daily",
    "data[0]": "value",
    "facets[series][]": "RNGWHHD",
    "start": "2017-01-01",
    "sort[0][column]": "period",
    "sort[0][direction]": "asc",
    "api_key": API,
}

r = requests.get(URL, params=PARAMS, timeout=90)
r.raise_for_status()
js = r.json()
rows = js.get("response", {}).get("data", [])
if not rows:
    print("[ERR] No rows returned from EIA v2 endpoint")
    sys.exit(3)

df = pd.DataFrame(rows).rename(columns={"period": "date", "value": "henry_hub"})
df["date"] = pd.to_datetime(df["date"], errors="coerce")
df = df[["date", "henry_hub"]].dropna().sort_values("date").reset_index(drop=True)

os.makedirs("data", exist_ok=True)
out = "data/eia_henryhub.csv"
df.to_csv(out, index=False)
print(f"[OK] Wrote {out} rows={len(df)}")
