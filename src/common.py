"""Shared plumbing for every collector and builder.

Design rules for this project:
  * Every dataset written to data/processed/ carries a sibling .meta.json giving
    the source URL, collection timestamp, row count and known gaps. The website
    reads these and prints them under each chart. No chart ships without a source.
  * Collectors are idempotent and cache raw payloads, so re-running is cheap and
    we never hammer a source.
  * Nothing fails the whole pipeline. A collector that cannot reach its source
    logs a warning, leaves the previous data in place and exits non-fatally.
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW = DATA / "raw"
PROCESSED = DATA / "processed"
MANUAL = DATA / "manual"
CACHE = DATA / "cache"
DOCS = ROOT / "docs"
CONFIG = ROOT / "config"

for _d in (RAW, PROCESSED, MANUAL, CACHE, DOCS):
    _d.mkdir(parents=True, exist_ok=True)

load_dotenv(ROOT / ".env")

# --------------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s %(name)-22s %(message)s",
    datefmt="%H:%M:%S",
)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


log = get_logger("common")


# --------------------------------------------------------------------------
# Config / secrets
# --------------------------------------------------------------------------
def key(name: str, default: str = "") -> str:
    """Read an API key from the environment. Returns '' when unset."""
    return os.environ.get(name, default).strip()


def sec_user_agent() -> str:
    ua = key("SEC_USER_AGENT")
    if not ua:
        # SEC blocks generic agents. This fallback is descriptive enough to work
        # but the user should set a real email in .env.
        ua = "Copart AltData Research (contact via github repo)"
    return ua


# --------------------------------------------------------------------------
# HTTP with retry + on-disk cache
# --------------------------------------------------------------------------
_SESSION: requests.Session | None = None

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def session() -> requests.Session:
    global _SESSION
    if _SESSION is None:
        s = requests.Session()
        s.headers.update(DEFAULT_HEADERS)
        _SESSION = s
    return _SESSION


def fetch(
    url: str,
    *,
    cache_name: str | None = None,
    max_age_hours: float = 24.0,
    headers: dict | None = None,
    params: dict | None = None,
    timeout: int = 60,
    tries: int = 3,
    pause: float = 1.5,
    binary: bool = False,
):
    """GET a URL with retries and an on-disk cache.

    Returns text (or bytes when binary=True), or None on failure.
    cache_name: file name under data/cache. When the cached copy is younger than
    max_age_hours it is returned without touching the network.
    """
    cache_path = CACHE / cache_name if cache_name else None

    if cache_path and cache_path.exists():
        age_h = (time.time() - cache_path.stat().st_mtime) / 3600.0
        if age_h < max_age_hours:
            log.info("cache hit (%.1fh old) %s", age_h, cache_path.name)
            return cache_path.read_bytes() if binary else cache_path.read_text(
                encoding="utf-8", errors="replace"
            )

    hdrs = dict(DEFAULT_HEADERS)
    if headers:
        hdrs.update(headers)

    last_err = None
    for attempt in range(1, tries + 1):
        try:
            r = session().get(url, headers=hdrs, params=params, timeout=timeout)
            if r.status_code == 200:
                payload = r.content if binary else r.text
                if cache_path:
                    cache_path.parent.mkdir(parents=True, exist_ok=True)
                    if binary:
                        cache_path.write_bytes(payload)
                    else:
                        cache_path.write_text(payload, encoding="utf-8")
                return payload
            last_err = f"HTTP {r.status_code}"
            # Rate limited or blocked: back off harder.
            if r.status_code in (403, 429, 503):
                time.sleep(pause * attempt * 3)
            else:
                time.sleep(pause * attempt)
        except Exception as exc:  # noqa: BLE001
            last_err = repr(exc)
            time.sleep(pause * attempt)
        log.warning("fetch attempt %d/%d failed (%s) %s", attempt, tries, last_err, url[:110])

    log.error("GAVE UP on %s  last_error=%s", url[:110], last_err)
    # Serve a stale cache rather than nothing.
    if cache_path and cache_path.exists():
        log.warning("serving STALE cache for %s", cache_path.name)
        return cache_path.read_bytes() if binary else cache_path.read_text(
            encoding="utf-8", errors="replace"
        )
    return None


# --------------------------------------------------------------------------
# Dataset output with provenance
# --------------------------------------------------------------------------
def write_dataset(
    df,
    name: str,
    *,
    source: str,
    method: str,
    gaps: str = "",
    units: str = "",
    frequency: str = "",
) -> Path:
    """Write a processed dataset plus its provenance sidecar.

    name: file stem, e.g. 'kpi_panel' -> data/processed/kpi_panel.csv
    Every field here surfaces on the website under the chart, so write them for
    a reader who has never seen the code.
    """
    PROCESSED.mkdir(parents=True, exist_ok=True)
    csv_path = PROCESSED / f"{name}.csv"
    df.to_csv(csv_path, index=False)

    meta = {
        "dataset": name,
        "source": source,
        "method": method,
        "gaps": gaps,
        "units": units,
        "frequency": frequency,
        "rows": int(len(df)),
        "columns": list(df.columns),
        "collected_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }
    (PROCESSED / f"{name}.meta.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )
    log.info("wrote %-28s %4d rows", csv_path.name, len(df))
    return csv_path


def read_dataset(name: str):
    """Read a processed dataset, or None when it has not been collected yet."""
    import pandas as pd

    p = PROCESSED / f"{name}.csv"
    if not p.exists():
        log.warning("dataset missing: %s (run its collector)", name)
        return None
    return pd.read_csv(p)


def read_meta(name: str) -> dict:
    p = PROCESSED / f"{name}.meta.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def today_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")
