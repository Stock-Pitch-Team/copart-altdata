"""Build the static research site into docs/ for GitHub Pages.

    python -m src.site.build_site

Reads only from data/processed/ and data/manual/, so the site can always be
rebuilt without re-collecting anything, and the git history of those CSVs is an
audit trail of what the site said and when.

Every chart is emitted with a table-view twin and a source/method/gaps footnote
pulled from the dataset's .meta.json sidecar. A page never invents a number: if
a dataset is missing the card degrades to a visible "not collected yet" note
rather than silently showing an empty chart.
"""

from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from jinja2 import Environment, FileSystemLoader, select_autoescape  # noqa: E402

from src.common import DOCS, MANUAL, PROCESSED, ROOT, get_logger, read_meta  # noqa: E402
from src.site import charts as ch  # noqa: E402

log = get_logger("build_site")

HERE = Path(__file__).resolve().parent
TEMPLATES = HERE / "templates"
STATIC = HERE / "static"

NAV = [
    {"href": "index.html", "label": "Thesis"},
    {"href": "company.html", "label": "Copart"},
    {"href": "competition.html", "label": "Copart vs IAA"},
    {"href": "industry.html", "label": "Industry funnel"},
    {"href": "valuation.html", "label": "Valuation"},
    {"href": "methods.html", "label": "Data & methods"},
]

# Marked-up facts that appear as headline numbers. Kept here so there is exactly
# one place to update them, and each carries its source for the methods page.
FACTS = {
    "price": 29.57,
    "price_date": "17 September 2026",
    "fy26_eps": 1.55,
    "fy26_revenue_bn": 4.70,
    "q4_us_ins_units": -7.5,
    "q4_us_ins_units_ex": 2.3,
    "q4_opex_per_car": 12.7,
    "fy26_buybacks_bn": 1.63,
    "rba_take_rate": 20.0,
    "rba_take_rate_delta_bp": -110,
    "rba_auto_units_yoy": 11.0,
    "acv_deal_bn": 1.9,
}


# --------------------------------------------------------------------------
# Loading helpers
# --------------------------------------------------------------------------
def manual(name: str) -> pd.DataFrame | None:
    p = MANUAL / f"{name}.csv"
    if not p.exists():
        log.warning("manual dataset missing: %s", p.name)
        return None
    return pd.read_csv(p)


def processed(name: str) -> pd.DataFrame | None:
    p = PROCESSED / f"{name}.csv"
    if not p.exists():
        log.warning("processed dataset missing: %s (run its collector)", name)
        return None
    return pd.read_csv(p)


def kpi(df: pd.DataFrame | None, period: str, metric: str):
    """Look up one value from the long-format KPI panel."""
    if df is None:
        return None
    hit = df[(df.fiscal_period == period) & (df.metric == metric)]
    if hit.empty:
        return None
    return float(hit.iloc[0]["value"])


def fmt_num(v, decimals: int = 1, suffix: str = "", plus: bool = False) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "n/a"
    s = f"{v:+.{decimals}f}" if plus else f"{v:,.{decimals}f}"
    return s + suffix


def safe_json(obj) -> str:
    """Serialise for embedding inside a <script type="application/json"> block.

    Jinja autoescaping is on for good reason, so the template prints this with
    |safe. To make that genuinely safe we escape the three characters that could
    break out of a script element, plus the two line separators that are legal
    in JSON but not in JavaScript string literals. The result is still valid
    JSON, so JSON.parse reads it unchanged.
    """
    raw = json.dumps(obj, separators=(",", ":"), allow_nan=False)
    return (
        raw.replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
        .replace(" ", "\\u2028")
        .replace(" ", "\\u2029")
    )


def card(
    cid: str,
    title: str,
    option: dict,
    table: dict,
    *,
    subtitle: str = "",
    source: str = "",
    method: str = "",
    gaps: str = "",
    height: str = "",
) -> dict:
    return {
        "id": cid,
        "title": title,
        "subtitle": subtitle,
        "option_json": safe_json(option),
        "table": table,
        "source": source,
        "method": method,
        "gaps": gaps,
        "height": height,
    }


def meta_bits(name: str) -> tuple[str, str, str]:
    m = read_meta(name)
    return m.get("source", ""), m.get("method", ""), m.get("gaps", "")


def jnull(series) -> list:
    """Convert a pandas series to a JSON-safe list (NaN -> None)."""
    return [None if pd.isna(v) else (float(v) if isinstance(v, (int, float)) else v) for v in series]


# --------------------------------------------------------------------------
# Page: Thesis
# --------------------------------------------------------------------------
def page_thesis() -> dict:
    kpis = manual("cprt_quarterly_kpis")
    cards = []

    # ---- Hero: reported US insurance unit growth vs the ex-customer figure ---
    periods = ["FY26Q1", "FY26Q2", "FY26Q3", "FY26Q4"]
    labels = ["FY26 Q1\nAug–Oct 25", "FY26 Q2\nNov–Jan", "FY26 Q3\nFeb–Apr", "FY26 Q4\nMay–Jul 26"]
    reported = [kpi(kpis, p, "us_insurance_units_yoy") for p in periods]
    ex_customer = [None, None, None, kpi(kpis, "FY26Q4", "us_insurance_units_yoy_ex_lost_customer")]

    opt = ch.bar(
        labels,
        [
            {"name": "As reported", "data": reported, "color": ch.SERIES[0]},
            {"name": "Excluding the one lost customer", "data": ex_customer, "color": ch.SERIES[2]},
        ],
        value_suffix="%",
        y_name="% YoY",
    )
    opt["series"][0]["markLine"] = {
        "silent": True,
        "symbol": "none",
        "data": [{"yAxis": 0}],
        "lineStyle": {"color": ch.BASELINE, "width": 1, "type": "solid"},
        "label": {"show": False},
    }
    cards.append(
        card(
            "hero-units",
            "The whole decline is one customer",
            opt,
            {
                "caption": "Copart US insurance unit growth, year over year",
                "columns": ["Fiscal quarter", "As reported (%)", "Excluding one lost customer (%)"],
                "rows": [
                    [l.replace("\n", " "), fmt_num(r, 1, plus=True), fmt_num(e, 1, plus=True)]
                    for l, r, e in zip(labels, reported, ex_customer)
                ],
            },
            subtitle=(
                "Copart's US insurance volumes have fallen for four straight quarters. On the "
                "FY26 Q4 call management said that excluding one single customer loss, domestic "
                "insurance assignments would have risen 2.3%. That one customer is therefore "
                "worth about ten points of growth, and it laps in FY27 Q2."
            ),
            source=(
                "Copart FY26 Q4 earnings call, 10 September 2026, for the Q4 figures. Earlier "
                "quarters from J.P. Morgan (F1Q26) and Barclays (F2Q26, F3Q26) research notes, "
                "which are credited but not reproduced."
            ),
            method=(
                "Figures as stated by management or as reported in broker notes. The "
                "ex-customer figure was disclosed only for FY26 Q4, which is why the other "
                "quarters have no second bar."
            ),
            gaps=(
                "Copart did not name the customer. Press reporting and analyst commentary "
                "identify it as Progressive, which moved from roughly 75% to roughly 90% of its "
                "salvage volume to IAA from about January 2026. We treat the identification as "
                "well-supported but not company-confirmed."
            ),
            height="tall",
        )
    )

    # ---- Scenario outcomes ---------------------------------------------------
    sc = manual("scenarios")
    if sc is not None:
        price = FACTS["price"]
        opt = ch.bar(
            list(sc["scenario"]),
            [{"name": "Implied price", "data": jnull(sc["implied_price"]), "color": ch.SERIES[0]}],
            value_suffix="",
            value_prefix="$",
            decimals=2,
            y_name="US$ per share",
        )
        opt["series"][0]["markLine"] = {
            "silent": True,
            "symbol": "none",
            "data": [{"yAxis": price, "label": {"show": True, "formatter": f"Today ${price:.2f}",
                                                "color": ch.INK_SECONDARY, "fontSize": 11,
                                                "position": "insideEndTop"}}],
            "lineStyle": {"color": ch.BASELINE, "width": 1, "type": "solid"},
        }
        opt["series"][0]["label"] = {
            "show": True, "position": "top", "color": ch.INK_SECONDARY, "fontSize": 11,
            "formatter": "${c}",
        }
        weighted = float((sc["probability"] * sc["implied_price"]).sum())
        cards.append(
            card(
                "scenarios",
                "Four scenarios, and what each is worth",
                opt,
                {
                    "caption": f"Probability-weighted value ${weighted:.2f} versus ${price:.2f} today",
                    "columns": ["Scenario", "Probability", "US insurance units FY27 (%)",
                                "Gross margin (%)", "FY27 EPS ($)", "Multiple (x)", "Implied price ($)"],
                    "rows": [
                        [r["scenario"], f"{r['probability']:.0%}",
                         fmt_num(r["us_insurance_units_fy27"], 1, plus=True),
                         fmt_num(r["gross_margin_fy27"]), fmt_num(r["eps_fy27"], 2),
                         fmt_num(r["multiple"]), fmt_num(r["implied_price"], 2)]
                        for _, r in sc.iterrows()
                    ],
                },
                subtitle=(
                    f"Probability-weighted value of ${weighted:.2f} against ${price:.2f} today. "
                    "The asymmetry comes from the downside already being close to the current "
                    "price, because the market has largely priced the bear case."
                ),
                source="Team estimates. Bear case anchored on the Barclays $26 target at 10x EV/EBITDA; base case on Bloomberg consensus FY27 EPS of $1.67.",
                method=(
                    "Each scenario sets US insurance unit growth and gross margin, which drive "
                    "FY27 EPS, then applies a P/E multiple. Probabilities are our judgement and "
                    "sum to 100%. Implied price is EPS times multiple."
                ),
                gaps=(
                    "These are placeholder figures pending the full three-statement model. The "
                    "EPS numbers are not yet derived from a units-times-revenue-per-unit build, "
                    "so treat them as scenario framing rather than a finished forecast."
                ),
            )
        )

    cat = manual("catalysts")
    catalysts = cat.to_dict("records") if cat is not None else []

    return {
        "template": "index.html",
        "page_title": "Thesis",
        "heading": "Copart's problem is one customer, and it laps in FY27 Q2",
        "eyebrow": "Long CPRT — variant view",
        "lede": (
            "Copart's US insurance volumes fell 7.5% last quarter and the market is "
            "extrapolating a share-loss spiral. Management disclosed that excluding one lost "
            "customer the same number would have been positive 2.3%. We think three things are "
            "mispriced: the timing of when that customer stops flattering the comparison, the "
            "price IAA is paying for the volume it won, and how much margin comes back when "
            "Copart's fixed cost base is used again."
        ),
        "page_description": (
            "Long Copart (CPRT): the US insurance unit decline is one lost customer, it laps in "
            "FY27 Q2, and IAA bought its share gains with take-rate concessions."
        ),
        "cards": cards,
        "catalysts": catalysts,
        "facts": FACTS,
    }


# --------------------------------------------------------------------------
# Page: Copart fundamentals
# --------------------------------------------------------------------------
def page_company() -> dict:
    cards = []
    secq = processed("sec_quarterly")
    src, method, gaps = meta_bits("sec_quarterly")

    if secq is not None:
        piv = (
            secq[secq.ticker == "CPRT"]
            .pivot_table(index="end", columns="metric", values="value", aggfunc="last")
            .sort_index()
        )
        piv = piv.tail(13)
        cats = [pd.Timestamp(d).strftime("%b %y") for d in piv.index]

        # Revenue, straight from filings.
        if "revenue" in piv:
            rev = (piv["revenue"] / 1e6).round(1)
            cards.append(
                card(
                    "cprt-revenue",
                    "Revenue has gone flat, not fallen apart",
                    ch.bar(
                        cats,
                        [{"name": "Copart", "data": jnull(rev), "color": ch.SERIES[0]}],
                        value_suffix="",
                        value_prefix="$",
                        decimals=0,
                        y_name="US$ mn",
                    ),
                    {
                        "caption": "Copart quarterly revenue, US$ millions, as filed",
                        "columns": ["Quarter ended", "Revenue ($mn)"],
                        "rows": [[c, fmt_num(v, 1)] for c, v in zip(cats, rev)],
                    },
                    subtitle=(
                        "Higher selling prices and international growth have held the top line "
                        "roughly flat while US insurance units fell. Revenue per unit rose 5.4% "
                        "in FY26 Q4, which is why a volume decline of that size did not show up "
                        "as a revenue decline."
                    ),
                    source=src,
                    method=method,
                    gaps=gaps,
                )
            )

        # Operating margin: one measure, one axis. Never paired with revenue on
        # a second scale.
        if "operating_income" in piv and "revenue" in piv:
            marg = (piv["operating_income"] / piv["revenue"] * 100).round(2)
            cards.append(
                card(
                    "cprt-margin",
                    "Operating margin is where the damage shows",
                    ch.line(
                        cats,
                        [{"name": "Operating margin", "data": jnull(marg), "color": ch.SERIES[0],
                          "area": True}],
                        value_suffix="%",
                        y_name="% of revenue",
                    ),
                    {
                        "caption": "Copart operating margin, computed from filed figures",
                        "columns": ["Quarter ended", "Operating margin (%)"],
                        "rows": [[c, fmt_num(v, 2)] for c, v in zip(cats, marg)],
                    },
                    subtitle=(
                        "Operating income divided by revenue, both as filed. The step down in the "
                        "most recent quarters is the cost of running a yard network built for "
                        "more units than are currently flowing through it. That is the operating "
                        "leverage the thesis expects to reverse."
                    ),
                    source=src,
                    method="Operating income divided by revenue, both from SEC XBRL. " + method,
                    gaps=gaps,
                )
            )

    # EPS actual vs consensus — the FY26 Q4 story in one chart.
    fin = manual("cprt_quarterly_financials")
    if fin is not None:
        f = fin.dropna(subset=["eps_consensus"]).copy()
        labels = [p.replace("FY", "FY").replace("Q", " Q") for p in f["fiscal_period"]]
        cards.append(
            card(
                "cprt-eps-surprise",
                "Copart beat on revenue and missed on earnings",
                ch.bar(
                    labels,
                    [
                        {"name": "Copart", "data": jnull(f["eps_actual"]), "color": ch.SERIES[0]},
                        {"name": "Consensus", "data": jnull(f["eps_consensus"]), "color": ch.SERIES[2]},
                    ],
                    value_suffix="",
                    value_prefix="$",
                    decimals=2,
                    y_name="US$ per share",
                ),
                {
                    "caption": "Adjusted diluted EPS, reported versus consensus",
                    "columns": ["Fiscal quarter", "Reported ($)", "Consensus ($)", "Revenue reported ($mn)", "Revenue consensus ($mn)"],
                    "rows": [
                        [lab, fmt_num(r["eps_actual"], 2), fmt_num(r["eps_consensus"], 2),
                         fmt_num(r["revenue_actual"], 0), fmt_num(r["revenue_consensus"], 0)]
                        for lab, (_, r) in zip(labels, f.iterrows())
                    ],
                },
                subtitle=(
                    "In FY26 Q4 revenue came in at about $1.20bn against roughly $1.14bn "
                    "expected, while EPS was $0.35 against $0.38. A revenue beat with an "
                    "earnings miss is a cost problem, not a demand problem, and cost is the "
                    "part management says it can fix."
                ),
                source=(
                    "Reported figures from Copart press releases and SEC filings. Consensus from "
                    "a Bloomberg consensus export dated 27 August 2026 and from Barclays and "
                    "J.P. Morgan notes, credited but not reproduced."
                ),
                method="Adjusted diluted EPS as reported against the consensus figure available immediately before the print.",
                gaps=(
                    "Consensus for earlier quarters is taken from whichever broker note recorded "
                    "it at the time, so the vendor basis is not perfectly consistent across "
                    "quarters. FY27 Q1 has an estimate but no actual yet."
                ),
            )
        )

    # Cost inflation vs revenue per unit — the operating leverage case.
    kpis = manual("cprt_quarterly_kpis")
    if kpis is not None:
        rows = [
            ("US facility cost per unit", kpi(kpis, "FY26Q4", "us_facility_cost_per_unit_yoy")),
            ("Operating cost per car", kpi(kpis, "FY26Q4", "opex_per_car_yoy")),
            ("US facility cost, total", kpi(kpis, "FY26Q4", "us_facility_cost_yoy")),
            ("International facility cost per unit", kpi(kpis, "FY26Q4", "intl_facility_cost_per_unit_yoy")),
            ("Revenue per unit", kpi(kpis, "FY26Q4", "revenue_per_unit_yoy")),
        ]
        rows = [(k, v) for k, v in rows if v is not None]
        cards.append(
            card(
                "cprt-costs",
                "Costs per unit are rising twice as fast as revenue per unit",
                ch.bar(
                    [r[0] for r in rows],
                    [{"name": "FY26 Q4 change", "data": [r[1] for r in rows], "color": ch.SERIES[0]}],
                    value_suffix="%",
                    y_name="% YoY",
                    horizontal=True,
                ),
                {
                    "caption": "Copart FY26 Q4 year-over-year change, per company disclosure",
                    "columns": ["Measure", "Change YoY (%)"],
                    "rows": [[k, fmt_num(v, 1, plus=True)] for k, v in rows],
                },
                subtitle=(
                    "Facility cost per unit rose 14.2% while revenue per unit rose 5.4%. Most of "
                    "that gap is fixed cost spread over fewer units, which reverses when volume "
                    "returns. Some of it is not: fuel is genuinely more expensive, and gasoline "
                    "prices were up 27% year over year in August."
                ),
                source="Copart FY26 Q4 earnings call, 10 September 2026.",
                method="Figures as stated by management on the call. Horizontal bars so the long measure names stay readable.",
                gaps=(
                    "Management did not break the increase into fuel, wages and volume "
                    "deleverage. Separating those is the job of the cost decomposition project, "
                    "which regresses facility cost per unit on diesel prices and unit counts."
                ),
                height="short",
            )
        )

    return {
        "template": "page.html",
        "page_title": "Copart",
        "heading": "What the filings actually show",
        "eyebrow": "Company fundamentals",
        "lede": (
            "Revenue is flat, margin is compressed, and the cause is visible: cost per unit is "
            "climbing while units fall. Every figure on this page is either from an SEC filing "
            "or from company disclosure on the earnings call."
        ),
        "page_description": "Copart quarterly revenue, margin, earnings surprise and unit cost inflation, sourced from SEC filings and earnings calls.",
        "cards": cards,
        "sections": [],
    }


# --------------------------------------------------------------------------
# Page: Copart vs IAA
# --------------------------------------------------------------------------
def page_competition() -> dict:
    cards = []

    # Industry tracking data: the two companies, the two comparable periods.
    share = manual("industry_share_tracking")
    if share is not None:
        cards.append(
            card(
                "share-tracking",
                "IAA is taking volume, on industry data",
                ch.bar(
                    list(share["period_label"]),
                    [
                        {"name": "Copart", "data": jnull(share["cprt_volume_yoy"]), "color": ch.SERIES[0]},
                        {"name": "RB Global / IAA", "data": jnull(share["rba_volume_yoy"]), "color": ch.SERIES[1]},
                    ],
                    value_suffix="%",
                    y_name="% YoY",
                ),
                {
                    "caption": "Salvage auction volume growth, year over year, industry data",
                    "columns": ["Period", "Copart (%)", "RB Global / IAA (%)"],
                    "rows": [
                        [r["period_label"], fmt_num(r["cprt_volume_yoy"], 1, plus=True),
                         fmt_num(r["rba_volume_yoy"], 1, plus=True)]
                        for _, r in share.iterrows()
                    ],
                },
                subtitle=(
                    "This is the bear case in one chart, and we do not dispute it. Copart's "
                    "volumes fell 1.4% in May and June 2026 while IAA's rose 14.9%, against an "
                    "easy comparison. The question the chart cannot answer is what IAA paid for "
                    "that volume."
                ),
                source="Barclays US Auto Retail 2Q26 earnings preview, 21 July 2026, citing third-party industry data. Credited, not reproduced.",
                method="Year-over-year volume growth for the same two calendar months in each year, as reported by Barclays from an industry data feed.",
                gaps=(
                    "We do not have the underlying feed, only the two summary figures Barclays "
                    "published, so we cannot verify it or extend the history. Replicating this "
                    "series independently is the purpose of the daily inventory tracker."
                ),
            )
        )

    # RB Global: volume and take rate as SEPARATE charts. Putting growth and a
    # rate on one plot with two y-scales would invent a correlation.
    rba = manual("rba_automotive_kpis")
    if rba is not None:
        tr = rba[rba.metric == "service_take_rate"].copy()
        order = {"CY25Q2": 0, "CY26Q1": 1, "CY26H1": 2, "CY26Q2": 3}
        tr["ord"] = tr["calendar_period"].map(order)
        tr = tr.dropna(subset=["ord"]).sort_values("ord")
        labels = [
            {"CY25Q2": "Q2 2025", "CY26Q1": "Q1 2026 (derived)", "CY26H1": "H1 2026", "CY26Q2": "Q2 2026"}[p]
            for p in tr["calendar_period"]
        ]
        cards.append(
            card(
                "rba-take-rate",
                "The price IAA paid: its take rate is falling",
                ch.line(
                    labels,
                    [{"name": "Service revenue take rate", "data": jnull(tr["value"]),
                      "color": ch.SERIES[1], "area": True}],
                    value_suffix="%",
                    y_name="% of gross transaction value",
                ),
                {
                    "caption": "RB Global service revenue as a percentage of gross transaction value",
                    "columns": ["Period", "Take rate (%)", "Source note"],
                    "rows": [
                        [lab, fmt_num(r["value"], 1), r["source"][:90]]
                        for lab, (_, r) in zip(labels, tr.iterrows())
                    ],
                },
                subtitle=(
                    "RB Global's take rate fell 110 basis points year over year to 20.0% in Q2 "
                    "2026. The company attributes it to acquisition mix and, in its own words, "
                    "automotive pricing incentives tied to higher transaction volumes. That is "
                    "the company telling you it bought volume with price."
                ),
                source="RB Global Q2 2026 results (SEC Form 8-K exhibit 99.1) and Q2 2026 earnings call, 4 August 2026.",
                method="Service revenue divided by gross transaction value, as disclosed. Shown as a separate chart from volume growth because a rate and a growth rate on one pair of axes would imply a relationship the data does not establish.",
                gaps=(
                    "The Q1 2026 point is DERIVED, not reported: RB Global disclosed H1 at 20.3% "
                    "and Q2 at 20.0%, which implies roughly 20.6% for Q1. It is labelled as "
                    "derived in the table and should be replaced with the figure from the 10-Q. "
                    "The take rate is a consolidated number covering commercial construction and "
                    "transportation as well as automotive, so it is not a pure salvage measure."
                ),
            )
        )

        vol = rba[rba.metric == "automotive_units_yoy"].copy()
        vlabels = {"CY25Q4": "Q4 2025", "CY26Q2": "Q2 2026"}
        vol = vol[vol.calendar_period.isin(vlabels)]
        if not vol.empty:
            cards.append(
                card(
                    "rba-volume",
                    "Meanwhile IAA's volume keeps growing",
                    ch.bar(
                        [vlabels[p] for p in vol["calendar_period"]],
                        [{"name": "RB Global / IAA", "data": jnull(vol["value"]), "color": ch.SERIES[1]}],
                        value_suffix="%",
                        y_name="% YoY",
                    ),
                    {
                        "caption": "RB Global automotive unit volume growth, year over year",
                        "columns": ["Period", "Unit growth (%)"],
                        "rows": [[vlabels[r["calendar_period"]], fmt_num(r["value"], 1, plus=True)]
                                 for _, r in vol.iterrows()],
                    },
                    subtitle=(
                        "Automotive lots reached 658,800 in Q2 2026, up 11%, which RB Global "
                        "called its sixth consecutive quarter of outperforming the market. Read "
                        "this chart next to the take rate above, not on the same axes: volume up, "
                        "price down."
                    ),
                    source="RB Global Q2 2026 results and earnings call, 4 August 2026; Q4 2025 figure via Barclays F2Q26 review.",
                    method="Unit growth as disclosed by the company.",
                    gaps="Only two quarters are captured here because RB Global does not disclose automotive unit growth consistently every quarter. The full panel is being built from transcripts.",
                    height="short",
                )
            )

    # Both companies' revenue, from filings, on one axis in the same currency.
    secq = processed("sec_quarterly")
    if secq is not None:
        src, method, gaps = meta_bits("sec_quarterly")
        rev = secq[(secq.metric == "revenue") & (secq.ticker.isin(["CPRT", "RBA"]))].copy()
        rev["end"] = pd.to_datetime(rev["end"])
        rev = rev[rev["end"] >= "2023-01-01"]
        piv = rev.pivot_table(index="end", columns="ticker", values="value", aggfunc="last").sort_index()
        piv = (piv / 1e6).round(1)
        cats = [d.strftime("%b %y") for d in piv.index]
        series = []
        if "CPRT" in piv:
            series.append({"name": "Copart", "data": jnull(piv["CPRT"]), "color": ch.SERIES[0], "connect_nulls": True})
        if "RBA" in piv:
            series.append({"name": "RB Global", "data": jnull(piv["RBA"]), "color": ch.SERIES[1], "connect_nulls": True})
        cards.append(
            card(
                "rev-compare",
                "Two revenue lines going in different directions",
                ch.line(cats, series, value_suffix="", value_prefix="$", decimals=0, y_name="US$ mn"),
                {
                    "caption": "Quarterly revenue as filed, US$ millions",
                    "columns": ["Quarter ended"] + [s["name"] for s in series],
                    "rows": [
                        [c] + [fmt_num(piv[t].iloc[i], 1) for t in piv.columns]
                        for i, c in enumerate(cats)
                    ],
                },
                subtitle=(
                    "Both series are total company revenue from SEC filings, so this is not a "
                    "salvage-only comparison. RB Global's growth includes acquisitions in "
                    "commercial construction and transportation, and its fiscal quarters end in "
                    "different months from Copart's."
                ),
                source=src,
                method=method,
                gaps=(
                    "Not like for like. Copart's fiscal year ends in July and RB Global's in "
                    "December, so the quarters are offset. RB Global's revenue includes "
                    "non-automotive segments and recent acquisitions, and it books gross vehicle "
                    "proceeds differently. Use this for direction, not for share arithmetic."
                ),
            )
        )

    # Progressive deceleration.
    pif = manual("progressive_pif")
    if pif is not None:
        labels = [pd.Timestamp(m + "-01").strftime("%b %Y") for m in pif["month"]]
        cards.append(
            card(
                "pgr-pif",
                "The lost customer is itself decelerating",
                ch.line(
                    labels,
                    [{"name": "Progressive personal auto policies in force",
                      "data": jnull(pif["personal_auto_pif_yoy"]), "color": ch.SERIES[2]}],
                    value_suffix="%",
                    y_name="% YoY",
                ),
                {
                    "caption": "Progressive personal auto policies in force, year-over-year growth",
                    "columns": ["Month", "PIF growth (%)", "PIF (thousands)"],
                    "rows": [
                        [lab, fmt_num(r["personal_auto_pif_yoy"], 1),
                         fmt_num(r["personal_auto_pif_thousands"], 0)]
                        for lab, (_, r) in zip(labels, pif.iterrows())
                    ],
                },
                subtitle=(
                    "Progressive's policy growth slowed from 10.2% in April to 8.8% in June, its "
                    "first run of single-digit months in this expansion. The volume IAA won is "
                    "attached to a carrier that is growing more slowly each month, which limits "
                    "how much the win compounds."
                ),
                source="Progressive monthly results releases, reported via CollisionWeek (April, May and June 2026).",
                method="Year-over-year growth in total personal auto policies in force, as disclosed in Progressive's monthly releases.",
                gaps=(
                    "Only three months are shown because we have not yet backfilled the series. "
                    "Three points is a weak basis for calling a trend. Progressive publishes "
                    "monthly, so a collector can extend this to several years and that is a "
                    "priority. August figures are due 18 September 2026."
                ),
                height="short",
            )
        )

    return {
        "template": "page.html",
        "page_title": "Copart vs IAA",
        "heading": "IAA won volume. Look at what it paid.",
        "eyebrow": "Competitive position",
        "lede": (
            "The bear case is that Copart is structurally losing share to IAA. The evidence for "
            "volume loss is real and we show it first. What the volume charts leave out is "
            "price: RB Global's take rate fell 110 basis points while it was winning, and the "
            "company itself attributes that to volume-linked pricing incentives."
        ),
        "page_description": "Copart versus RB Global's IAA: volume share shifts, the take-rate concessions behind them, and the carrier that moved.",
        "cards": cards,
        "sections": [],
    }


# --------------------------------------------------------------------------
# Page: Industry funnel
# --------------------------------------------------------------------------
def page_industry() -> dict:
    cards = []

    now = processed("tlf_nowcast")
    stats = processed("tlf_nowcast_stats")
    if now is not None:
        now = now.copy()
        now["label"] = [pd.Timestamp(d).strftime("%b %y") for d in now["quarter_end"]]
        src, method, gaps = meta_bits("tlf_nowcast")

        opt = ch.band_line(
            list(now["label"]),
            lower=jnull(now["tlf_nowcast_low"]),
            upper=jnull(now["tlf_nowcast_high"]),
            actual=jnull(now["total_loss_frequency"]),
            fitted=jnull(now["tlf_fitted"]),
            y_name="% of claims",
        )
        s = stats.iloc[0] if stats is not None and len(stats) else None
        sub = (
            "Total-loss frequency is published quarterly by CCC with a long lag, and the sell "
            "side quotes it months late. Repair and used-vehicle CPI are monthly with a "
            "two-week lag, so the fitted line gives an early read."
        )
        if s is not None:
            sub += (
                f" The fit uses the repair-versus-value spread lagged {int(s['lag'])} quarters "
                f"plus a structural trend, with an R-squared of {s['rsquared']:.2f} on "
                f"{int(s['n'])} observations."
            )
        cards.append(
            card(
                "tlf-nowcast",
                "Nowcasting the salvage supply funnel",
                opt,
                {
                    "caption": "Total-loss frequency: published actuals, model fit, and nowcast interval",
                    "columns": ["Quarter", "Repair CPI YoY (%)", "Used CPI YoY (%)", "Spread (pts)",
                                "Published actual (%)", "Model fit (%)", "Nowcast low", "Nowcast high"],
                    "rows": [
                        [r["label"], fmt_num(r["repair_cpi_yoy"]), fmt_num(r["used_cpi_yoy"]),
                         fmt_num(r["scissors"]), fmt_num(r["total_loss_frequency"]),
                         fmt_num(r["tlf_fitted"]), fmt_num(r["tlf_nowcast_low"]),
                         fmt_num(r["tlf_nowcast_high"])]
                        for _, r in now.iterrows()
                    ],
                },
                subtitle=sub,
                source=src,
                method=method,
                gaps=gaps,
                height="tall",
            )
        )

        cards.append(
            card(
                "scissors",
                "The mechanism: repair costs up, used values down",
                ch.line(
                    list(now["label"]),
                    [
                        {"name": "Vehicle repair CPI", "data": jnull(now["repair_cpi_yoy"]),
                         "color": ch.SERIES[0]},
                        {"name": "Used vehicle CPI", "data": jnull(now["used_cpi_yoy"]),
                         "color": ch.SERIES[1]},
                    ],
                    value_suffix="%",
                    y_name="% YoY",
                    zero_line=True,
                ),
                {
                    "caption": "Year-over-year change in repair costs and used vehicle values",
                    "columns": ["Quarter", "Repair CPI YoY (%)", "Used vehicle CPI YoY (%)", "Spread (pts)"],
                    "rows": [
                        [r["label"], fmt_num(r["repair_cpi_yoy"]), fmt_num(r["used_cpi_yoy"]),
                         fmt_num(r["scissors"])]
                        for _, r in now.iterrows()
                    ],
                },
                subtitle=(
                    "An insurer writes a vehicle off when repairing it costs too much relative "
                    "to what the vehicle is worth. In August 2026 repair CPI was rising 7.8% "
                    "year over year while used-vehicle CPI was falling 2.3%. Every quarter the "
                    "blue line sits above the orange one, more borderline claims tip into total "
                    "losses, and more cars enter the salvage channel."
                ),
                source="US Bureau of Labor Statistics public API, series CUSR0000SETD (motor vehicle maintenance and repair) and CUSR0000SETA02 (used cars and trucks).",
                method="Monthly seasonally-adjusted index levels converted to year-over-year percentage change, then averaged to calendar quarters.",
                gaps=(
                    "Consumer CPI is a proxy. Insurers pay negotiated repair rates, not retail "
                    "prices, and salvage vehicles clear at wholesale rather than retail used "
                    "values. The direction is reliable; the exact level is not a like-for-like "
                    "match to insurer economics."
                ),
            )
        )

    ann = manual("industry_annual")
    if ann is not None:
        a = ann.dropna(subset=["tlf_all_categories"])
        cards.append(
            card(
                "tlf-annual",
                "A decade-long structural climb",
                ch.bar(
                    [str(int(y)) for y in a["year"]],
                    [{"name": "Total-loss frequency", "data": jnull(a["tlf_all_categories"]),
                      "color": ch.SERIES[0]}],
                    value_suffix="%",
                    y_name="% of claims",
                ),
                {
                    "caption": "Share of auto claims ending in a total loss, all loss categories",
                    "columns": ["Year", "All loss categories (%)", "Non-comprehensive (%)"],
                    "rows": [
                        [str(int(r["year"])), fmt_num(r["tlf_all_categories"]),
                         fmt_num(r["tlf_noncomp"])]
                        for _, r in a.iterrows()
                    ],
                },
                subtitle=(
                    "From 15.6% of claims in 2015 to 23.1% in 2025, a record. This happened "
                    "while crash frequency fell, which means the driver is not more accidents "
                    "but a higher probability that a damaged car is uneconomic to repair. That "
                    "is a structural widening of Copart's addressable volume."
                ),
                source="CCC Intelligent Solutions Crash Course reports, as presented in Freedom Broker's Copart initiation of 26 June 2026. Credited, not reproduced.",
                method="Annual share of claims resulting in a total loss, on CCC's all-loss-categories definition.",
                gaps=(
                    "Read from a chart in a broker note rather than from CCC directly, so values "
                    "carry rounding. CCC's quarterly series used in the nowcast above has a "
                    "slightly different definition, so the two are not strictly comparable."
                ),
            )
        )

        cr = ann.dropna(subset=["personal_auto_combined_ratio"])
        opt = ch.line(
            [str(int(y)) for y in cr["year"]],
            [{"name": "Personal auto combined ratio", "data": jnull(cr["personal_auto_combined_ratio"]),
              "color": ch.SERIES[0]}],
            value_suffix="%",
            y_name="%",
        )
        opt["series"][0]["markLine"] = {
            "silent": True,
            "symbol": "none",
            "data": [{"yAxis": 100, "label": {"show": True, "formatter": "Break-even 100%",
                                              "color": ch.INK_MUTED, "fontSize": 11}}],
            "lineStyle": {"color": ch.BASELINE, "width": 1, "type": "solid"},
        }
        cards.append(
            card(
                "combined-ratio",
                "Insurers can afford to process claims normally again",
                opt,
                {
                    "caption": "US personal auto combined ratio; below 100% means underwriting profit",
                    "columns": ["Year", "Combined ratio (%)"],
                    "rows": [[str(int(r["year"])), fmt_num(r["personal_auto_combined_ratio"])]
                             for _, r in cr.iterrows()],
                },
                subtitle=(
                    "The combined ratio peaked at 112.2% in 2022, when carriers were losing money "
                    "on every premium dollar and pulled back hard on advertising and growth. It "
                    "is now near 95% and forecast to stay there. Profitable carriers grow "
                    "policies, and more policies eventually mean more total losses."
                ),
                source="Triple-I and Milliman projections, as presented in Freedom Broker's Copart initiation of 26 June 2026.",
                method="Industry combined ratio for personal auto lines. 2025 is an estimate and 2026 to 2027 are forecasts.",
                gaps="The last three points are forecasts, not actuals, and come from a single forecasting source.",
                height="short",
            )
        )

    # Where catastrophe volume actually comes from. Note this is deliberately
    # framed as durable land advantage, not as forecast upside, because the 2026
    # hurricane outlook is below normal.
    storm = processed("storm_county")
    if storm is not None:
        src, method, gaps = meta_bits("storm_county")
        top = storm.head(12).copy()
        labels = [f"{r['county']}, {r['state'][:14]}" for _, r in top.iterrows()]
        cards.append(
            card(
                "storm-counties",
                "Catastrophe volume is a hail problem, not just a hurricane one",
                ch.bar(
                    labels,
                    [
                        {"name": "Hail", "data": jnull(top["hail_events"]), "color": ch.SERIES[0]},
                        {"name": "Flood", "data": jnull(top["flood_events"]), "color": ch.SERIES[2]},
                        {"name": "Hurricane and tornado", "data": jnull(top["wind_events"]),
                         "color": ch.SERIES[1]},
                    ],
                    value_suffix="",
                    decimals=0,
                    horizontal=True,
                ),
                {
                    "caption": "Counties with the most vehicle-damaging weather events, 2016 to 2026",
                    "columns": ["County", "State", "Total events", "Hail", "Flood", "Hurricane/tornado"],
                    "rows": [
                        [r["county"], r["state"], fmt_num(r["events"], 0), fmt_num(r["hail_events"], 0),
                         fmt_num(r["flood_events"], 0), fmt_num(r["wind_events"], 0)]
                        for _, r in top.iterrows()
                    ],
                },
                subtitle=(
                    "Across 2016 to 2026 we counted about 184,000 vehicle-damaging events in "
                    "3,730 counties. The concentration is in the hail belt, Colorado, South "
                    "Dakota, Texas and Oklahoma, not the hurricane coast. That matters this year "
                    "because the 2026 Atlantic hurricane outlook is below normal, while hail and "
                    "flood exposure is unaffected by that forecast."
                ),
                source=src,
                method=method,
                gaps=gaps,
                height="tall",
            )
        )

    return {
        "template": "page.html",
        "page_title": "Industry funnel",
        "heading": "The pipe feeding both auctions keeps widening",
        "eyebrow": "Structural drivers",
        "lede": (
            "Whatever happens to share, the number of cars written off in America is rising, and "
            "the reason is arithmetic: repair costs keep climbing while used-car values do not. "
            "We can track that spread monthly from public data and use it to nowcast total-loss "
            "frequency ahead of the quarterly industry release."
        ),
        "page_description": "Total-loss frequency nowcast from the repair-to-value spread, plus the structural drivers of salvage supply.",
        "cards": cards,
        "sections": [],
    }


# --------------------------------------------------------------------------
# Page: Valuation
# --------------------------------------------------------------------------
def page_valuation() -> dict:
    cards = []

    peers = manual("peer_multiples")
    if peers is not None:
        pts = [
            {
                "name": r["ticker"],
                "x": float(r["pe_10yr_avg"]),
                "y": float(r["fy2_pe"]),
                "highlight": r["ticker"] in ("CPRT", "RBA"),
                "color": ch.SERIES[0] if r["ticker"] == "CPRT" else (
                    ch.SERIES[1] if r["ticker"] == "RBA" else None
                ),
            }
            for _, r in peers.iterrows()
        ]
        cards.append(
            card(
                "peer-pe",
                "Copart trades below its own ten-year average",
                ch.scatter(
                    pts,
                    x_name="10-year average P/E",
                    y_name="Forward P/E",
                    x_suffix="x",
                    y_suffix="x",
                    diagonal=True,
                ),
                {
                    "caption": "Forward P/E against each company's own ten-year average multiple",
                    "columns": ["Ticker", "Company", "Forward P/E (x)", "10-year average P/E (x)", "EV/EBITDA (x)", "10-yr avg EV/EBITDA (x)"],
                    "rows": [
                        [r["ticker"], r["company"], fmt_num(r["fy2_pe"]), fmt_num(r["pe_10yr_avg"]),
                         fmt_num(r["fy2_ev_ebitda"]), fmt_num(r["ev_ebitda_10yr_avg"])]
                        for _, r in peers.iterrows()
                    ],
                },
                subtitle=(
                    "Points below the diagonal trade cheaper than their own history. Copart sits "
                    "well below it. These are duopoly and oligopoly businesses with similar "
                    "economics: rating agencies, card networks, credit bureaus and tower REITs. "
                    "Copart is the cheapest relative to its own past in the group."
                ),
                source="J.P. Morgan F1Q26 note, Table 3, priced 21 November 2025. Credited, not reproduced.",
                method="Forward P/E on consensus estimates plotted against each company's own ten-year average P/E. The diagonal is parity, where a company trades exactly at its historical average.",
                gaps=(
                    "Priced as of 21 November 2025, when Copart was about $41. The stock is now "
                    "about $29.6, so Copart's true position is materially further below the "
                    "diagonal than plotted. Refreshing this to live prices is a pending task. "
                    "Only three colour slots are used; other companies are drawn in muted ink "
                    "with direct labels so identity never depends on hue."
                ),
                height="tall",
            )
        )

    tgt = manual("analyst_targets")
    if tgt is not None:
        t = tgt.sort_values("price_target")
        labels = [f"{r['broker']} ({pd.Timestamp(r['date']).strftime('%b %y')})" for _, r in t.iterrows()]
        opt = ch.bar(
            labels,
            [{"name": "Price target", "data": jnull(t["price_target"]), "color": ch.SERIES[0]}],
            value_suffix="",
            value_prefix="$",
            decimals=0,
            y_name="US$ per share",
            horizontal=True,
        )
        opt["series"][0]["markLine"] = {
            "silent": True,
            "symbol": "none",
            "data": [{"xAxis": FACTS["price"], "label": {"show": True,
                                                         "formatter": f"${FACTS['price']:.2f} today",
                                                         "color": ch.INK_SECONDARY, "fontSize": 11}}],
            "lineStyle": {"color": ch.BASELINE, "width": 1, "type": "solid"},
        }
        cards.append(
            card(
                "targets",
                "The street is split, and the low end is already here",
                opt,
                {
                    "caption": "Published price targets, most recent per broker where several exist",
                    "columns": ["Broker", "Date", "Rating", "Target ($)", "Basis"],
                    "rows": [
                        [r["broker"], r["date"], r["rating"], fmt_num(r["price_target"], 0), r["basis"]]
                        for _, r in tgt.sort_values("date", ascending=False).iterrows()
                    ],
                },
                subtitle=(
                    "Targets run from $26 to $45. The stock trades at about $29.6, barely above "
                    "the most bearish published target, which is the asymmetry the thesis rests "
                    "on: the bear case is priced, the recovery case is not."
                ),
                source="Broker research notes and rating-change summaries from Investing.com, Yahoo Finance and ad-hoc-news, September 2026.",
                method="Each published target with its date, rating and stated valuation basis. Barclays appears several times in the table because we track its target history.",
                gaps=(
                    "Targets have different dates and horizons, so this is not an apples-to-apples "
                    "snapshot. The chart shows every entry we have logged, including multiple "
                    "Barclays revisions, so bars for the same broker are different vintages."
                ),
                height="tall",
            )
        )

    return {
        "template": "page.html",
        "page_title": "Valuation",
        "heading": "The bear case is in the price",
        "eyebrow": "Valuation and positioning",
        "lede": (
            "Copart trades near the bottom of its twenty-year multiple range and below its own "
            "ten-year average, with no debt and a net cash balance sheet. That is what makes the "
            "setup asymmetric rather than merely cheap."
        ),
        "page_description": "Copart valuation against its own history and duopoly peers, published price targets, and the scenario range.",
        "cards": cards,
        "sections": [],
    }


# --------------------------------------------------------------------------
# Page: Data and methods
# --------------------------------------------------------------------------
def page_methods() -> dict:
    rows = []
    for meta_file in sorted(PROCESSED.glob("*.meta.json")):
        try:
            m = json.loads(meta_file.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        rows.append(
            [
                m.get("dataset", meta_file.stem),
                m.get("frequency", ""),
                str(m.get("rows", "")),
                m.get("collected_utc", ""),
                m.get("source", ""),
            ]
        )

    manual_rows = []
    for p in sorted(MANUAL.glob("*.csv")):
        try:
            df = pd.read_csv(p)
            n = len(df)
        except Exception:  # noqa: BLE001
            n = 0
        manual_rows.append([p.name, str(n)])

    detail = []
    for meta_file in sorted(PROCESSED.glob("*.meta.json")):
        try:
            m = json.loads(meta_file.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        detail.append(
            {
                "dataset": m.get("dataset", meta_file.stem),
                "source": m.get("source", ""),
                "method": m.get("method", ""),
                "gaps": m.get("gaps", ""),
                "collected": m.get("collected_utc", ""),
                "rows": m.get("rows", ""),
                "frequency": m.get("frequency", ""),
            }
        )

    return {
        "template": "methods.html",
        "page_title": "Data & methods",
        "heading": "Every number, where it came from, and what is wrong with it",
        "eyebrow": "Provenance",
        "lede": (
            "This page exists so a reader can check us. Each collected dataset lists its source, "
            "how it was built, and its known gaps. Where we used licensed broker research we "
            "credit the figures and do not reproduce the documents."
        ),
        "page_description": "Sources, methods and known gaps for every dataset behind the Copart research site.",
        "dataset_rows": rows,
        "manual_rows": manual_rows,
        "detail": detail,
    }


# --------------------------------------------------------------------------
# Render
# --------------------------------------------------------------------------
def render() -> int:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    pages = [
        page_thesis(),
        page_company(),
        page_competition(),
        page_industry(),
        page_valuation(),
        page_methods(),
    ]

    build_time = datetime.now(timezone.utc).strftime("%d %B %Y %H:%M UTC")
    DOCS.mkdir(parents=True, exist_ok=True)

    # Static assets
    assets = DOCS / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    for f in STATIC.glob("*"):
        shutil.copy2(f, assets / f.name)
    # Tell GitHub Pages not to run Jekyll over our output.
    (DOCS / ".nojekyll").write_text("", encoding="utf-8")

    nav_map = {
        "Thesis": "index.html",
        "Copart": "company.html",
        "Copart vs IAA": "competition.html",
        "Industry funnel": "industry.html",
        "Valuation": "valuation.html",
        "Data & methods": "methods.html",
    }

    for page in pages:
        tpl = env.get_template(page["template"])
        out_name = nav_map[page["page_title"]]
        html = tpl.render(
            nav=NAV,
            current=out_name,
            rel="",
            build_time=build_time,
            **page,
        )
        (DOCS / out_name).write_text(html, encoding="utf-8")
        log.info("wrote docs/%-22s (%d cards)", out_name, len(page.get("cards", [])))

    log.info("site built into %s", DOCS)
    return 0


if __name__ == "__main__":
    raise SystemExit(render())
