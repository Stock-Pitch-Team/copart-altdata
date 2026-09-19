"""One command to refresh everything.

    python run_all.py            collect, model, then rebuild the site
    python run_all.py --check    validate the hand-entered CSVs and stop
    python run_all.py --site     rebuild the site only (no network)
    python run_all.py --offline  same as --site

A failing collector never stops the run. Sources go down, rate limits get hit,
and a network blip should not leave you without a website. Each step reports its
own status and the site is built from whatever data is on disk.
"""

from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = ROOT / ".venv" / "Scripts" / "python.exe"
if not PY.exists():  # posix layout or a system interpreter
    alt = ROOT / ".venv" / "bin" / "python"
    PY = alt if alt.exists() else Path(sys.executable)

COLLECT = [
    ("src.collect.sec_financials", "SEC filings for CPRT, RBA, ACVA, PGR"),
    ("src.collect.macro", "BLS repair and used-vehicle price indices"),
]
BUILD = [
    ("src.build.tlf_nowcast", "Total-loss-frequency nowcast model"),
    ("src.build.tlf_backtest", "Historical nowcast validation versus baselines"),
]
SITE = ("src.site.build_site", "Static website into docs/")


def check_manual_csvs() -> int:
    """Catch the mistake that actually happens: a comma inside a text field.

    A hand-edited CSV with an unquoted comma silently shifts every later column,
    which would put wrong numbers on the website. This refuses to continue.
    """
    manual = ROOT / "data" / "manual"
    if not manual.exists():
        print("  no data/manual directory")
        return 0

    problems = 0
    for path in sorted(manual.glob("*.csv")):
        try:
            with path.open(newline="", encoding="utf-8") as fh:
                rows = [r for r in csv.reader(fh) if r]
        except Exception as exc:  # noqa: BLE001
            print(f"  FAIL  {path.name}: cannot read ({exc})")
            problems += 1
            continue

        if not rows:
            print(f"  FAIL  {path.name}: file is empty")
            problems += 1
            continue

        width = len(rows[0])
        bad = [(i + 1, len(r)) for i, r in enumerate(rows) if len(r) != width]
        if bad:
            problems += 1
            print(f"  FAIL  {path.name}: header has {width} columns but:")
            for line_no, got in bad[:6]:
                print(f"          line {line_no} has {got} columns")
            print("          Most likely a comma inside a text field. Wrap that")
            print('          field in double quotes, e.g. "Bloomberg (est, not reported)".')
        else:
            has_source = "source" in [c.strip().lower() for c in rows[0]] or \
                         any("source" in c.strip().lower() for c in rows[0])
            flag = "" if has_source else "   (note: no source column)"
            print(f"  ok    {path.name}: {len(rows) - 1} rows, {width} columns{flag}")

    return problems


def run(module: str, label: str) -> bool:
    print(f"\n>>> {label}\n    ({module})")
    try:
        res = subprocess.run(
            [str(PY), "-m", module], cwd=str(ROOT), capture_output=True, text=True, timeout=1800
        )
    except subprocess.TimeoutExpired:
        print("    TIMED OUT after 30 minutes")
        return False

    tail = [l for l in (res.stdout + res.stderr).strip().splitlines() if l.strip()]
    for line in tail[-12:]:
        print("    " + line)
    ok = res.returncode == 0
    print(f"    -> {'OK' if ok else 'FAILED (continuing)'}")
    return ok


def main(argv: list[str]) -> int:
    args = set(a.lstrip("-").lower() for a in argv[1:])

    print("=" * 72)
    print("Validating hand-entered CSVs in data/manual")
    print("=" * 72)
    problems = check_manual_csvs()
    if problems:
        print(f"\n{problems} file(s) have structural problems. Fix them before continuing.")
        print("Nothing else was run, because bad CSVs would put wrong numbers on the site.")
        return 1
    print("\nAll manual CSVs are structurally valid.")

    if "check" in args:
        return 0

    offline = bool(args & {"site", "offline"})
    results = []

    if not offline:
        print("\n" + "=" * 72)
        print("Collecting from public sources")
        print("=" * 72)
        for module, label in COLLECT:
            results.append((label, run(module, label)))
    else:
        print("\nSkipping collection (offline/site mode).")

    print("\n" + "=" * 72)
    print("Running models")
    print("=" * 72)
    for module, label in BUILD:
        results.append((label, run(module, label)))

    print("\n" + "=" * 72)
    print("Building the website")
    print("=" * 72)
    site_ok = run(*SITE)
    results.append((SITE[1], site_ok))

    print("\n" + "=" * 72)
    print("Summary")
    print("=" * 72)
    for label, ok in results:
        print(f"  {'OK    ' if ok else 'FAILED'}  {label}")

    if site_ok:
        print(f"\nOpen the site:  {ROOT / 'docs' / 'index.html'}")
        print("Or serve it:    .venv/Scripts/python.exe -m http.server 8765 --directory docs")
    return 0 if site_ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
