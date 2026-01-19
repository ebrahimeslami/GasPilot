"""EIA v2 helper (configurable).

Project B focuses on LNG export terminal flows. EIA endpoints/series vary by dataset and may use facets.
Rather than hard-coding potentially-changing routes, this tool lets you pull any EIA v2 route and facet set.

Usage examples (PowerShell):
  $env:EIA_API_KEY="<key>"
  python tools/eia_fetch_generic.py --route "natural-gas/pri/fut/data" --series RNGWHHD --start 2017-01-01 --out data/external/eia_henryhub.csv

For LNG feedgas/exports, first discover valid route/series via EIA Open Data "Series ID Search" tool.
See docs/PIPELINE.md.
"""
import os, argparse, requests
import pandas as pd
from pathlib import Path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--route", required=True, help="EIA v2 route path, e.g., natural-gas/pri/fut/data")
    ap.add_argument("--series", required=True, help="Series identifier used in facets[series][], e.g., RNGWHHD")
    ap.add_argument("--frequency", default="daily")
    ap.add_argument("--start", default="2017-01-01")
    ap.add_argument("--end", default=None)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    key = os.environ.get("EIA_API_KEY", "").strip()
    if not key:
        raise SystemExit("EIA_API_KEY not set")

    url = f"https://api.eia.gov/v2/{args.route}"
    params = {
        "frequency": args.frequency,
        "data[0]": "value",
        "facets[series][]": args.series,
        "start": args.start,
        "sort[0][column]": "period",
        "sort[0][direction]": "asc",
        "api_key": key,
    }
    if args.end:
        params["end"] = args.end

    r = requests.get(url, params=params, timeout=90)
    r.raise_for_status()
    js = r.json()
    rows = js.get("response", {}).get("data", [])
    if not rows:
        raise SystemExit(f"No rows returned. Check route/series. url={url}")

    df = pd.DataFrame(rows).rename(columns={"period":"date","value":args.series})
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
    df = df[["date", args.series]].sort_values("date").reset_index(drop=True)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"[OK] wrote {out} rows={len(df)}")

if __name__ == "__main__":
    main()
