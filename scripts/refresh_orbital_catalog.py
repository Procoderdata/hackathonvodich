#!/usr/bin/env python3
"""Fetch and refresh orbital-element catalog from NASA Exoplanet Archive."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import io
import json
from pathlib import Path

import pandas as pd
import requests

TAP_SYNC_URL = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"

SQL_QUERY = """
SELECT
  pl_name,
  hostname,
  disc_year,
  disc_facility,
  sy_dist,
  ra,
  dec,
  pl_orbper,
  pl_orbsmax,
  pl_orbeccen,
  pl_orbincl,
  pl_orblper,
  pl_orbtper,
  pl_tranmid,
  pl_rade,
  pl_bmasse,
  pl_eqt,
  pl_insol,
  st_rad,
  st_teff
FROM pscomppars
WHERE pl_orbper IS NOT NULL
  AND pl_orbsmax IS NOT NULL
""".strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh orbital elements catalog from NASA TAP")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/orbital_elements.csv"),
        help="CSV output path",
    )
    parser.add_argument(
        "--meta",
        type=Path,
        default=Path("data/orbital_elements.meta.json"),
        help="Metadata JSON output path",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=1500,
        help="Max rows to keep after sorting by orbital period",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="HTTP timeout in seconds",
    )
    return parser.parse_args()


def fetch_catalog(timeout: int) -> pd.DataFrame:
    response = requests.get(
        TAP_SYNC_URL,
        params={"query": SQL_QUERY, "format": "csv"},
        headers={"User-Agent": "atlas-orrery-refresh/1.0"},
        timeout=timeout,
    )
    if not response.ok:
        body_preview = " ".join(response.text.split())[:360]
        raise RuntimeError(f"NASA TAP request failed ({response.status_code}): {body_preview}")

    raw_df = pd.read_csv(io.StringIO(response.text))
    if raw_df.empty:
        raise RuntimeError("NASA TAP returned an empty dataset")

    df = raw_df.drop_duplicates(subset=["pl_name"], keep="first").copy()

    numeric_cols = [
        "sy_dist",
        "ra",
        "dec",
        "pl_orbper",
        "pl_orbsmax",
        "pl_orbeccen",
        "pl_orbincl",
        "pl_orblper",
        "pl_orbtper",
        "pl_tranmid",
        "pl_rade",
        "pl_bmasse",
        "pl_eqt",
        "pl_insol",
        "st_rad",
        "st_teff",
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df[df["pl_orbper"].notna() & df["pl_orbsmax"].notna()].copy()
    df.sort_values(by=["pl_orbper", "pl_orbsmax"], inplace=True, ascending=[True, True])
    return df


def write_outputs(df: pd.DataFrame, output_path: Path, meta_path: Path, limit: int) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.parent.mkdir(parents=True, exist_ok=True)

    if limit > 0 and len(df) > limit:
        df = df.head(limit).copy()

    df.to_csv(output_path, index=False)

    now_utc = datetime.now(timezone.utc)
    meta = {
        "refreshed_at_utc": now_utc.isoformat(),
        "source": "NASA Exoplanet Archive TAP / pscomppars",
        "query": SQL_QUERY,
        "rows": int(len(df)),
        "columns": list(df.columns),
    }

    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print(f"Wrote {len(df)} rows -> {output_path}")
    print(f"Wrote metadata -> {meta_path}")


def main() -> None:
    args = parse_args()
    df = fetch_catalog(timeout=args.timeout)
    write_outputs(df, args.output, args.meta, args.limit)


if __name__ == "__main__":
    main()
