"""Project 3 — total-loss-frequency nowcast from the repair-to-value scissors.

THE IDEA, in plain English
--------------------------
An insurer declares a vehicle a total loss when the cost to repair it gets close
to what the vehicle is worth. So the single number that should drive total-loss
frequency is the GAP between repair-cost inflation and used-vehicle-value
inflation. We call that gap the "scissors":

    scissors = repair CPI YoY  -  used vehicle CPI YoY

When repair costs rise 8% while used values fall 2%, the scissors is +10 points
and more borderline claims tip over into total losses.

WHY THIS IS AN EDGE
-------------------
Total-loss frequency is published by CCC Intelligent Solutions quarterly, with a
long lag, and the sell side quotes it months late (the JPM note used data through
calendar Q3 2025). The BLS CPI inputs are monthly with roughly a two-week lag.
So this model gives a read on the salvage supply funnel well before the
authoritative number is published, using only free public data.

HONEST LIMITATIONS (also printed on the website)
------------------------------------------------
  * ~27 quarterly observations. This is a small sample. Treat the output as
    directional, not precise.
  * Consumer CPI is a proxy for insurer-paid repair cost and wholesale salvage
    values. The direction is right; the level is not a like-for-like match.
  * The relationship is not causally identified. Fleet age, claim mix and
    deductible changes all move total-loss frequency too.

Run:  python -m src.build.tlf_nowcast
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.common import MANUAL, get_logger, read_dataset, write_dataset  # noqa: E402

log = get_logger("tlf_nowcast")

# How many quarters the scissors leads total-loss frequency. Claims take time to
# be adjudicated, so a lag is expected. We test 0-3 and pick the best fit.
CANDIDATE_LAGS = [0, 1, 2, 3]


def _quarter_end(ts: pd.Timestamp) -> pd.Timestamp:
    return ts + pd.offsets.QuarterEnd(0)


def load_inputs() -> pd.DataFrame | None:
    cpi = read_dataset("macro_cpi_long")
    if cpi is None:
        log.error("macro_cpi_long missing - run: python -m src.collect.macro")
        return None

    tlf_path = MANUAL / "tlf_quarterly.csv"
    if not tlf_path.exists():
        log.error("missing %s", tlf_path)
        return None
    tlf = pd.read_csv(tlf_path)

    cpi["date"] = pd.to_datetime(cpi["date"])
    wide = cpi.pivot_table(index="date", columns="series", values="value_yoy_pct")

    need = ["cpi_motor_vehicle_maintenance_repair", "cpi_used_cars_trucks"]
    missing = [c for c in need if c not in wide.columns]
    if missing:
        log.error("CPI series missing: %s", missing)
        return None

    wide = wide.dropna(subset=need)
    wide["scissors"] = (
        wide["cpi_motor_vehicle_maintenance_repair"] - wide["cpi_used_cars_trucks"]
    )

    # Collapse monthly CPI to calendar quarters (mean of the three months).
    wide["quarter_end"] = [_quarter_end(d) for d in wide.index]
    q = (
        wide.groupby("quarter_end")[
            ["cpi_motor_vehicle_maintenance_repair", "cpi_used_cars_trucks", "scissors"]
        ]
        .mean()
        .reset_index()
    )
    q = q.rename(
        columns={
            "cpi_motor_vehicle_maintenance_repair": "repair_cpi_yoy",
            "cpi_used_cars_trucks": "used_cpi_yoy",
        }
    )

    tlf["quarter_end"] = pd.to_datetime(tlf["period_end"]) + pd.offsets.QuarterEnd(0)
    tlf = tlf[["quarter_end", "total_loss_frequency", "calendar_quarter"]]

    merged = q.merge(tlf, on="quarter_end", how="left").sort_values("quarter_end")
    return merged


def fit_and_nowcast(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Fit TLF on the lagged scissors PLUS a linear time trend.

    The trend term is not a fudge: every industry source attributes a structural
    rise in total-loss frequency to the ageing fleet and rising vehicle
    complexity (calibrations, sensors), which is a slow drift independent of the
    repair-vs-value cycle. Fitting the scissors alone underpredicts recent levels
    by roughly two points because it has no way to represent that drift.
    So: trend captures the structural climb, scissors captures the cycle.
    """
    import statsmodels.api as sm

    df = df.copy()
    # Trend measured in years since the start of the sample, so beta is readable
    # as "points of total-loss frequency per year of structural drift".
    t0 = df["quarter_end"].min()
    df["trend_years"] = (df["quarter_end"] - t0).dt.days / 365.25

    best = None
    for lag in CANDIDATE_LAGS:
        d = df.copy()
        d["x"] = d["scissors"].shift(lag)
        train = d.dropna(subset=["x", "total_loss_frequency", "trend_years"])
        if len(train) < 12:
            continue
        X = sm.add_constant(train[["x", "trend_years"]])
        model = sm.OLS(train["total_loss_frequency"], X).fit()
        # Prefer adjusted R-squared since we are now comparing a 2-regressor spec.
        score = float(model.rsquared_adj)
        if best is None or score > best["rsquared_adj"]:
            best = {
                "lag": lag,
                "rsquared": float(model.rsquared),
                "rsquared_adj": score,
                "n": int(len(train)),
                "const": float(model.params["const"]),
                "beta_scissors": float(model.params["x"]),
                "beta_trend_per_year": float(model.params["trend_years"]),
                "pvalue_scissors": float(model.pvalues["x"]),
                "pvalue_trend": float(model.pvalues["trend_years"]),
                "resid_std": float(np.std(model.resid, ddof=3)),
                "trend_origin": t0.strftime("%Y-%m-%d"),
            }

    if best is None:
        raise RuntimeError("not enough overlapping observations to fit")

    lag = best["lag"]
    out = df.copy()
    out["scissors_lagged"] = out["scissors"].shift(lag)
    out["tlf_fitted"] = (
        best["const"]
        + best["beta_scissors"] * out["scissors_lagged"]
        + best["beta_trend_per_year"] * out["trend_years"]
    ).round(2)

    # A nowcast only counts for quarters AFTER the last published actual.
    # Without this guard the model "nowcasts" pre-sample quarters, which is
    # backfilling, not forecasting.
    actuals = out.dropna(subset=["total_loss_frequency"])
    last_actual = actuals["quarter_end"].max() if len(actuals) else out["quarter_end"].min()
    out["is_nowcast"] = (
        out["total_loss_frequency"].isna()
        & out["tlf_fitted"].notna()
        & (out["quarter_end"] > last_actual)
    )

    band = 1.96 * best["resid_std"]
    out["tlf_nowcast_low"] = (out["tlf_fitted"] - band).round(2)
    out["tlf_nowcast_high"] = (out["tlf_fitted"] + band).round(2)
    out.loc[~out["is_nowcast"], ["tlf_nowcast_low", "tlf_nowcast_high"]] = np.nan

    stats = dict(best)
    stats["band_95"] = round(band, 2)
    stats["last_published_actual"] = last_actual.strftime("%Y-%m-%d")
    return out, stats


def main() -> int:
    df = load_inputs()
    if df is None:
        return 1

    out, stats = fit_and_nowcast(df)

    log.info(
        "best fit: lag=%d quarters  R2=%.3f (adj %.3f)  n=%d  95%% band=+/-%.2f pts",
        stats["lag"], stats["rsquared"], stats["rsquared_adj"], stats["n"], stats["band_95"],
    )
    log.info(
        "  scissors beta = %+.4f pts of TLF per point of spread (p=%.4f)",
        stats["beta_scissors"], stats["pvalue_scissors"],
    )
    log.info(
        "  structural trend = %+.3f pts of TLF per year (p=%.4f)",
        stats["beta_trend_per_year"], stats["pvalue_trend"],
    )
    log.info("  last published CCC actual: %s", stats["last_published_actual"])

    nowcasts = out[out["is_nowcast"]].tail(6)
    if len(nowcasts):
        log.info("nowcast for quarters CCC has not published:")
        for _, r in nowcasts.iterrows():
            log.info(
                "  %s  scissors=%+.1f  ->  TLF %.1f%% (95%% CI %.1f to %.1f)",
                r["quarter_end"].date(), r["scissors_lagged"],
                r["tlf_fitted"], r["tlf_nowcast_low"], r["tlf_nowcast_high"],
            )

    export = out[[
        "quarter_end", "calendar_quarter", "repair_cpi_yoy", "used_cpi_yoy",
        "scissors", "scissors_lagged", "total_loss_frequency", "tlf_fitted",
        "tlf_nowcast_low", "tlf_nowcast_high", "is_nowcast",
    ]].copy()
    export["quarter_end"] = export["quarter_end"].dt.strftime("%Y-%m-%d")
    for c in ("repair_cpi_yoy", "used_cpi_yoy", "scissors", "scissors_lagged"):
        export[c] = export[c].round(2)

    write_dataset(
        export,
        "tlf_nowcast",
        source=(
            "Total-loss frequency from CCC Intelligent Solutions as cited in J.P. Morgan "
            "research (calendar 1Q19-3Q25) and by Copart on its FY26Q4 earnings call "
            "(calendar 2Q26). Repair and used-vehicle CPI from the US Bureau of Labor "
            "Statistics public API."
        ),
        method=(
            "Defined the repair-to-value 'scissors' as repair CPI year-over-year minus "
            "used-vehicle CPI year-over-year, averaged monthly CPI to calendar quarters, "
            f"then fitted ordinary least squares of total-loss frequency on (a) the "
            f"scissors lagged {stats['lag']} quarter(s) and (b) a linear time trend that "
            "represents the structural drift from the ageing fleet and rising vehicle "
            "complexity. Lags 0-3 were tested and the highest adjusted R-squared chosen "
            f"(R2={stats['rsquared']:.3f}, adjusted {stats['rsquared_adj']:.3f}, n={stats['n']}). "
            f"Fitted: scissors {stats['beta_scissors']:+.4f} pts per point of spread "
            f"(p={stats['pvalue_scissors']:.4f}), trend {stats['beta_trend_per_year']:+.3f} pts "
            f"per year (p={stats['pvalue_trend']:.4f}). The nowcast band is the 95 percent "
            "residual interval and is populated only for quarters after the last published "
            f"CCC actual ({stats['last_published_actual']})."
        ),
        gaps=(
            f"Only {stats['n']} overlapping quarterly observations, so this is directional "
            "rather than precise. Consumer CPI proxies but does not equal insurer-paid "
            "repair cost or wholesale salvage value. The relationship is correlational: "
            "fleet age, claim mix and deductible changes also move total-loss frequency. "
            "The CCC series cited by J.P. Morgan (percent of claims flagged total loss) "
            "and the annual CCC Crash Course figures use slightly different definitions."
        ),
        units="percent for all columns except is_nowcast",
        frequency="quarterly",
    )

    stats_df = pd.DataFrame([stats])
    write_dataset(
        stats_df,
        "tlf_nowcast_stats",
        source="Computed by src/build/tlf_nowcast.py",
        method="Regression diagnostics for the chosen specification.",
        gaps="See tlf_nowcast.",
        units="mixed",
        frequency="one row",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
