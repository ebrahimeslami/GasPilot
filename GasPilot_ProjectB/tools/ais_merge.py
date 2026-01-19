"""Merge AIS vessel events (manual downloads) into daily features.

Expected input (one or many CSVs) with at least:
  - timestamp or time column (UTC preferred)
  - terminal (optional; can be inferred from destination)
  - vessel_id or MMSI (optional)
  - event_type (optional; e.g., DEPARTURE / ARRIVAL)
If you only have departures, that is fine.

Outputs:
  data/external/ais_daily.csv with:
    date, departures, arrivals (if available), unique_vessels
"""
import argparse, glob
import pandas as pd
from pathlib import Path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input_glob", required=True, help="Glob to AIS CSVs, e.g., data/external/ais_*.csv")
    ap.add_argument("--time_col", default="timestamp")
    ap.add_argument("--event_col", default="event_type")
    ap.add_argument("--out", default="data/external/ais_daily.csv")
    args = ap.parse_args()

    files = sorted(glob.glob(args.input_glob))
    if not files:
        raise FileNotFoundError(f"No files matched {args.input_glob}")

    dfs = []
    for f in files:
        df = pd.read_csv(f)
        if args.time_col not in df.columns:
            # try common variants
            for c in ["time","datetime","ts","Timestamp","DateTime"]:
                if c in df.columns:
                    df = df.rename(columns={c: args.time_col})
                    break
        df[args.time_col] = pd.to_datetime(df[args.time_col], errors="coerce").dt.tz_localize(None)
        df = df.dropna(subset=[args.time_col])
        dfs.append(df)

    all_df = pd.concat(dfs, ignore_index=True)
    all_df["date"] = all_df[args.time_col].dt.floor("D")

    # counts
    out = pd.DataFrame({"date": sorted(all_df["date"].unique())})
    if args.event_col in all_df.columns:
        ev = all_df[args.event_col].astype(str).str.upper()
        all_df["_ev"] = ev
        dep = all_df[all_df["_ev"].str.contains("DEP")].groupby("date").size().rename("departures")
        arr = all_df[all_df["_ev"].str.contains("ARR")].groupby("date").size().rename("arrivals")
        out = out.merge(dep, on="date", how="left").merge(arr, on="date", how="left")
    else:
        dep = all_df.groupby("date").size().rename("departures")
        out = out.merge(dep, on="date", how="left")

    # unique vessels
    vid = None
    for c in ["vessel_id","mmsi","MMSI","imo","IMO"]:
        if c in all_df.columns:
            vid = c; break
    if vid:
        uv = all_df.groupby("date")[vid].nunique().rename("unique_vessels")
        out = out.merge(uv, on="date", how="left")

    for c in ["departures","arrivals","unique_vessels"]:
        if c in out.columns:
            out[c] = out[c].fillna(0).astype(int)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out, index=False)
    print(f"[OK] wrote {args.out} rows={len(out)}")

if __name__ == "__main__":
    main()
