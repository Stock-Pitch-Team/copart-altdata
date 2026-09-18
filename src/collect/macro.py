"""Project 3 (inputs) â€” the macro series that drive total-loss frequency.

The economic chain we are testing:
    repair cost inflation UP + used vehicle values DOWN
        -> repair cost exceeds a larger share of vehicle value
        -> more claims cross the total-loss threshold
        -> more salvage units routed to Copart and IAA

Primary source is the BLS public API, which works with NO API KEY (the keyless
v1 endpoint). Setting BLS_API_KEY in .env upgrades to v2, which allows 20-year
windows and 500 requests a day instead of 10 years and 25.

FRED is supported as an optional supplement when FRED_API_KEY is set. Note the
keyless fredgraph.csv endpoint is unreliable from some networks, so we do not
depend on it.

Run:  python -m src.collect.macro
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.common import DEFAULT_HEADERS, get_logger, key, write_dataset  # noqa: E402

log = get_logger("macro")

# BLS series. Every one of these is a published CPI index.
BLS_SERIES = {
    "CUSR0000SETD": "cpi_motor_vehicle_maintenance_repair",
    "CUSR0000SETA02": "cpi_used_cars_trucks",
    "CUSR0000SETA01": "cpi_new_vehicles",
    "CUSR0000SETE": "cpi_motor_vehicle_insurance",
    "CUSR0000SETB01": "cpi_gasoline_all_types",
    "CUSR0000SAT": "cpi_transportation",
    "CUSR0000SA0": "cpi_all_items",
}

# Monthly BLS periods are M01..M12; M13 is an annual average we drop.
_MONTH_MAP = {f"M{i:02d}": i for i in range(1, 13)}


def _fetch_bls(series_ids: list[str], start_year: int, end_year: int) -> dict | None:
    api_key = key("BLS_API_KEY")
    if api_key:
        url = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
        payload = {
            "seriesid": series_ids,
            "startyear": str(start_year),
            "endyear": str(end_year),
            "registrationkey": api_key,
        }
    else:
        url = "https://api.bls.gov/publicAPI/v1/timeseries/data/"
        payload = {
            "seriesid": series_ids,
            "startyear": str(start_year),
            "endyear": str(end_year),
        }
        log.info("no BLS_API_KEY set - using keyless v1 (10-year window, 25 req/day)")

    try:
        r = requests.post(
            url,
            json=payload,
            headers={**DEFAULT_HEADERS, "Content-Type": "application/json"},
            timeout=90,
        )
    except Exception as exc:  # noqa: BLE001
        log.error("BLS request failed: %r", exc)
        return None

    if r.status_code != 200:
        log.error("BLS HTTP %s", r.status_code)
        return None

    try:
        data = r.json()
    except json.JSONDecodeError:
        log.error("BLS returned non-JSON")
        return None

    if data.get("status") != "REQUEST_SUCCEEDED":
        log.error("BLS status=%s messages=%s", data.get("status"), data.get("message"))
        return None
    return data


def _parse_bls(data: dict) -> pd.DataFrame:
    rows = []
    for series in data.get("Results", {}).get("series", []):
        sid = series.get("seriesID")
        friendly = BLS_SERIES.get(sid, sid)
        for item in series.get("data", []):
            period = item.get("period", "")
            if period not in _MONTH_MAP:
                continue  # skip M13 annual averages and semiannual figures
            try:
                val = float(item["value"])
            except (KeyError, ValueError):
                continue
            rows.append(
                {
                    "date": f"{item['year']}-{_MONTH_MAP[period]:02d}-01",
                    "series_id": sid,
                    "series": friendly,
                    "value": val,
                }
            )
    return pd.DataFrame(rows)



def add_calendar_yoy(df: pd.DataFrame) -> pd.DataFrame:
    """Match the same calendar month last year; never substitute an older row.

    BLS can omit months (for example October 2025). Row-based pct_change(12)
    silently compares the wrong months after a gap.
    """
    df = df.drop(columns=["value_yoy_pct"], errors="ignore").copy()
    prior = df[["series", "date", "value"]].copy()
    prior["date"] = (pd.to_datetime(prior["date"]) + pd.DateOffset(years=1)).dt.strftime("%Y-%m-%d")
    prior = prior.rename(columns={"value": "prior_year_value"})
    df = df.merge(prior, on=["series", "date"], how="left", validate="one_to_one")
    df["value_yoy_pct"] = ((df["value"] / df["prior_year_value"] - 1) * 100).round(2)
    return df.drop(columns=["prior_year_value"])


def main() -> int:
    has_key = bool(key("BLS_API_KEY"))
    # Keyless v1 allows a 10-year span per request; v2 allows 20.
    windows = [(2017, 2026)] if not has_key else [(2007, 2026)]

    frames = []
    for start, end in windows:
        data = _fetch_bls(list(BLS_SERIES), start, end)
        if data is None:
            continue
        df = _parse_bls(data)
        if not df.empty:
            frames.append(df)

    if not frames:
        log.error(
            "collected nothing from BLS. The keyless endpoint is limited to 25 "
            "requests per IP per day - if you have hit that, add BLS_API_KEY to .env."
        )
        return 1

    df = pd.concat(frames, ignore_index=True).drop_duplicates(
        subset=["date", "series_id"]
    )
    df = df.sort_values(["series", "date"])

    # Year-over-year change is what actually matters for the thesis, so compute
    # it here rather than in every chart.
    df = add_calendar_yoy(df)

    wide = df.pivot_table(index="date", columns="series", values="value").reset_index()

    write_dataset(
        df[["date", "series", "series_id", "value", "value_yoy_pct"]],
        "macro_cpi_long",
        source="US Bureau of Labor Statistics public API (api.bls.gov), public domain",
        method=(
            "Monthly seasonally-adjusted CPI index levels for vehicle repair, used "
            "vehicles, new vehicles, motor vehicle insurance, gasoline, transportation "
            "and all items. Year-over-year percent change computed as a 12-month "
            f"change on the index level. Collected via {'v2 (keyed)' if has_key else 'v1 (keyless)'}."
        ),
        gaps=(
            "The keyless v1 endpoint returns at most a 10-year window, so history "
            "before 2017 requires a free BLS_API_KEY. CPI measures consumer prices, "
            "which proxy but do not equal the insurer-paid repair costs that drive "
            "total-loss decisions. The Manheim wholesale index is not published by "
            "BLS and is hand-entered in data/manual instead."
        ),
        units="index level, and percent for value_yoy_pct",
        frequency="monthly",
    )

    write_dataset(
        wide,
        "macro_cpi_wide",
        source="US Bureau of Labor Statistics public API (api.bls.gov), public domain",
        method="Same data as macro_cpi_long, pivoted to one column per series for charting.",
        gaps="See macro_cpi_long.",
        units="index level",
        frequency="monthly",
    )

    latest = df.groupby("series").tail(1)
    log.info("latest observations:")
    for _, r in latest.iterrows():
        log.info("  %-40s %s  %8.2f  yoy %+.2f%%", r["series"], r["date"], r["value"], r["value_yoy_pct"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
