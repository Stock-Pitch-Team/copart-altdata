"""Project 4 (part 1) — where catastrophe salvage volume actually comes from.

Builds a county-level ranking of vehicle-damaging weather events from NOAA's
Storm Events Database, so we can later measure how much owned yard capacity each
company has near the counties that generate salvage surges.

Event types are filtered to the ones that write cars off: hail, flood, hurricane,
tornado, tropical storm, storm surge. Heat, drought, cold and wind alone are
excluded because they rarely total a vehicle.

No API key. The database is bulk gzipped CSV, one file per year, going back to
1950. We take the most recent years only, because yard networks from the 1990s
are not the relevant comparison.

IMPORTANT CONTEXT for how this gets used: NOAA's August 2026 outlook puts a 75%
chance of a BELOW-normal Atlantic hurricane season under El Nino conditions, and
Colorado State forecasts below-average landfall probability. So this dataset
supports a claim about durable land advantage and optionality. It does NOT
support forecasting a catastrophe-driven earnings beat this fiscal year. Hail and
flood events, which the hurricane outlook does not cover, remain live.

Run:  python -m src.collect.noaa_storms
"""

from __future__ import annotations

import gzip
import io
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.common import fetch, get_logger, write_dataset  # noqa: E402

log = get_logger("noaa_storms")

BASE = "https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/"

# Years to pull. Ten years is enough to characterise where damage concentrates
# without downloading 70 years of files.
YEARS = list(range(2016, 2027))

# Event types that actually total vehicles.
VEHICLE_DAMAGING = {
    "HAIL",
    "FLASH FLOOD",
    "FLOOD",
    "HURRICANE",
    "HURRICANE (TYPHOON)",
    "TORNADO",
    "TROPICAL STORM",
    "STORM SURGE/TIDE",
    "COASTAL FLOOD",
}


def _index_files() -> dict[int, str]:
    """Map year -> details file name by reading the directory listing."""
    html = fetch(BASE, cache_name="noaa_index.html", max_age_hours=168)
    if not html:
        log.error("could not read the NOAA file index")
        return {}
    out: dict[int, str] = {}
    for m in re.finditer(r'StormEvents_details-ftp_v1\.0_d(\d{4})_c\d+\.csv\.gz', html):
        year = int(m.group(1))
        out[year] = m.group(0)
    log.info("NOAA index lists %d yearly detail files", len(out))
    return out


def _load_year(year: int, filename: str) -> pd.DataFrame | None:
    raw = fetch(
        BASE + filename,
        cache_name=f"noaa_{year}.csv.gz",
        max_age_hours=24 * 30,
        binary=True,
        timeout=180,
    )
    if not raw:
        return None
    try:
        with gzip.open(io.BytesIO(raw), "rb") as fh:
            df = pd.read_csv(fh, low_memory=False)
    except Exception as exc:  # noqa: BLE001
        log.warning("%d: could not parse (%r)", year, exc)
        return None

    cols = {c.upper(): c for c in df.columns}
    need = ["EVENT_TYPE", "STATE", "CZ_NAME", "YEAR"]
    if any(n not in cols for n in need):
        log.warning("%d: unexpected columns", year)
        return None

    df = df.rename(columns={cols[n]: n for n in need if n in cols})
    keep = ["YEAR", "STATE", "CZ_NAME", "EVENT_TYPE"]
    for extra in ("DAMAGE_PROPERTY", "BEGIN_LAT", "BEGIN_LON", "MAGNITUDE"):
        if extra in cols:
            df = df.rename(columns={cols[extra]: extra})
            keep.append(extra)

    df = df[keep]
    df["EVENT_TYPE"] = df["EVENT_TYPE"].astype(str).str.upper().str.strip()
    return df[df["EVENT_TYPE"].isin(VEHICLE_DAMAGING)].copy()


def _parse_damage(v) -> float:
    """NOAA writes property damage as strings like '2.50K' or '1.2M'."""
    if pd.isna(v):
        return 0.0
    s = str(v).strip().upper()
    if not s or s in {"0", "0.00", "NAN"}:
        return 0.0
    mult = 1.0
    if s.endswith("K"):
        mult, s = 1e3, s[:-1]
    elif s.endswith("M"):
        mult, s = 1e6, s[:-1]
    elif s.endswith("B"):
        mult, s = 1e9, s[:-1]
    try:
        return float(s) * mult
    except ValueError:
        return 0.0


def main() -> int:
    index = _index_files()
    if not index:
        return 1

    frames = []
    for year in YEARS:
        fn = index.get(year)
        if not fn:
            log.info("%d: no file published yet", year)
            continue
        df = _load_year(year, fn)
        if df is None or df.empty:
            continue
        log.info("%d: %6d vehicle-damaging events", year, len(df))
        frames.append(df)

    if not frames:
        log.error("no storm data collected")
        return 1

    allf = pd.concat(frames, ignore_index=True)
    if "DAMAGE_PROPERTY" in allf.columns:
        allf["damage_usd"] = allf["DAMAGE_PROPERTY"].map(_parse_damage)
    else:
        allf["damage_usd"] = 0.0

    allf["county"] = allf["CZ_NAME"].astype(str).str.title().str.strip()
    allf["state"] = allf["STATE"].astype(str).str.title().str.strip()

    county = (
        allf.groupby(["state", "county"])
        .agg(
            events=("EVENT_TYPE", "size"),
            hail_events=("EVENT_TYPE", lambda s: int((s == "HAIL").sum())),
            flood_events=("EVENT_TYPE", lambda s: int(s.isin(
                ["FLOOD", "FLASH FLOOD", "COASTAL FLOOD", "STORM SURGE/TIDE"]).sum())),
            wind_events=("EVENT_TYPE", lambda s: int(s.isin(
                ["HURRICANE", "HURRICANE (TYPHOON)", "TORNADO", "TROPICAL STORM"]).sum())),
            damage_usd=("damage_usd", "sum"),
        )
        .reset_index()
        .sort_values("events", ascending=False)
    )

    by_state = (
        allf.groupby("state")
        .agg(events=("EVENT_TYPE", "size"), damage_usd=("damage_usd", "sum"))
        .reset_index()
        .sort_values("events", ascending=False)
    )

    by_year_type = (
        allf.groupby(["YEAR", "EVENT_TYPE"]).size().reset_index(name="events")
        .rename(columns={"YEAR": "year", "EVENT_TYPE": "event_type"})
    )

    src = "NOAA National Centers for Environmental Information, Storm Events Database (public domain)"
    method = (
        f"Downloaded the yearly 'details' files for {min(YEARS)}-{max(YEARS)} and kept only "
        "event types that plausibly total a vehicle: hail, flood, flash flood, coastal flood, "
        "storm surge, hurricane, tornado and tropical storm. Heat, drought, cold and "
        "straight-line wind are excluded. Property damage strings such as '2.50K' and '1.2M' "
        "are parsed to dollars and summed."
    )
    gaps = (
        "Storm Events counts REPORTED events, so densely populated counties are "
        "over-represented relative to sparsely populated ones. Property damage is an "
        "all-property figure, not vehicle-specific, so it proxies rather than measures "
        "salvage supply. County names come from NOAA's CZ_NAME field, which mixes counties "
        "and forecast zones, so joining to yard locations needs care. The current year is "
        "incomplete. Separately: NOAA's August 2026 seasonal outlook gives a 75 percent "
        "chance of a below-normal Atlantic hurricane season, so this data supports a claim "
        "about durable land advantage, not a forecast of catastrophe-driven upside this year."
    )

    write_dataset(county, "storm_county", source=src, method=method, gaps=gaps,
                  units="event counts and USD", frequency="cumulative over the period")
    write_dataset(by_state, "storm_state", source=src, method=method, gaps=gaps,
                  units="event counts and USD", frequency="cumulative over the period")
    write_dataset(by_year_type, "storm_year_type", source=src, method=method, gaps=gaps,
                  units="event counts", frequency="annual")

    log.info("top 10 counties by vehicle-damaging events:")
    for _, r in county.head(10).iterrows():
        log.info("  %-22s %-14s %5d events  hail %4d  flood %4d",
                 r["county"], r["state"], r["events"], r["hail_events"], r["flood_events"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
