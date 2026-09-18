"""Project 6 (part 1) — authoritative financials straight from SEC XBRL.

Why this exists: the sell-side PDFs in research/ are licensed and cannot be
published, and Bloomberg exports cannot be redistributed either. SEC XBRL is
public domain, so every financial figure on our website can be sourced to a
filing rather than to a broker note. That makes the site publishable.

Pulls the "companyfacts" bundle for each company and flattens it into a tidy
quarterly and annual panel.

Requires no API key, but the SEC does require a descriptive User-Agent with a
real email address (set SEC_USER_AGENT in .env) or it returns HTTP 403.

Run:  python -m src.collect.sec_financials
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.common import RAW, fetch, get_logger, sec_user_agent, write_dataset  # noqa: E402

log = get_logger("sec_financials")

COMPANIES = {
    "CPRT": {"cik": "0000900075", "name": "Copart, Inc.", "fy_end_month": 7},
    "RBA": {"cik": "0001046102", "name": "RB Global, Inc.", "fy_end_month": 12},
    "ACVA": {"cik": "0001637873", "name": "ACV Auctions Inc.", "fy_end_month": 12},
    "PGR": {"cik": "0000080661", "name": "The Progressive Corporation", "fy_end_month": 12},
}

# Friendly metric name -> candidate XBRL concepts in PRIORITY ORDER.
#
# Alias chains matter: Copart retagged revenue when ASC 606 came in, so
# "Revenues" stops in FY2020 and "RevenueFromContractWithCustomerIncludingAssessedTax"
# takes over. Without the chain, every recent quarter's revenue is silently
# missing. We take the highest-priority concept available for each period.
CONCEPTS = {
    # Income statement (flow items - duration facts)
    "revenue": [
        "RevenueFromContractWithCustomerIncludingAssessedTax",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
    ],
    "gross_profit": ["GrossProfit"],
    "cost_of_revenue": ["CostOfGoodsAndServicesSold", "CostOfRevenue", "CostOfGoodsSold"],
    "operating_income": ["OperatingIncomeLoss"],
    "net_income": ["NetIncomeLoss", "ProfitLoss"],
    "eps_diluted": ["EarningsPerShareDiluted"],
    "pretax_income": [
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
    ],
    "diluted_shares": ["WeightedAverageNumberOfDilutedSharesOutstanding"],
    "buybacks": ["PaymentsForRepurchaseOfCommonStock"],
    "cash_from_ops": ["NetCashProvidedByUsedInOperatingActivities"],
    "capex": [
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "PaymentsToAcquireProductiveAssets",
    ],
    "d_and_a": [
        "DepreciationDepletionAndAmortization",
        "DepreciationAmortizationAndAccretionNet",
    ],
    "g_and_a": ["GeneralAndAdministrativeExpense"],
    # Balance sheet (stock items - instant facts)
    "cash": ["CashAndCashEquivalentsAtCarryingValue"],
    "ppe_net": ["PropertyPlantAndEquipmentNet"],
    "equity": ["StockholdersEquity"],
    "total_assets": ["Assets"],
    "total_liabilities": ["Liabilities"],
    "goodwill": ["Goodwill"],
    "accounts_receivable": ["AccountsReceivableNetCurrent"],
}

FLOW_CONCEPTS = {
    "revenue", "gross_profit", "operating_income", "net_income", "eps_diluted",
    "pretax_income", "buybacks", "cash_from_ops", "capex", "d_and_a", "g_and_a",
}


def _download(ticker: str, cik: str) -> dict | None:
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    txt = fetch(
        url,
        cache_name=f"sec_companyfacts_{ticker}.json",
        max_age_hours=24,
        headers={"User-Agent": sec_user_agent(), "Accept-Encoding": "gzip, deflate"},
        timeout=120,
    )
    if not txt:
        return None
    try:
        data = json.loads(txt)
    except json.JSONDecodeError:
        log.error("%s: companyfacts was not valid JSON", ticker)
        return None
    (RAW / f"sec_companyfacts_{ticker}.json").write_text(txt, encoding="utf-8")
    return data


def _flatten(ticker: str, data: dict) -> pd.DataFrame:
    rows = []
    pools = [
        data.get("facts", {}).get("us-gaap", {}),
        data.get("facts", {}).get("dei", {}),
    ]

    concept_pairs: list[tuple[str, str, int]] = []
    for friendly, candidates in CONCEPTS.items():
        for rank, concept in enumerate(candidates):
            concept_pairs.append((friendly, concept, rank))

    for friendly, concept, rank in concept_pairs:
        block = None
        for pool in pools:
            if concept in pool:
                block = pool[concept]
                break
        if block is None:
            continue

        for unit_key, facts in block.get("units", {}).items():
            for f in facts:
                end = f.get("end")
                start = f.get("start")
                val = f.get("val")
                if end is None or val is None:
                    continue

                # Duration in days tells us whether this is a quarter or a year.
                span = None
                if start:
                    span = (pd.Timestamp(end) - pd.Timestamp(start)).days

                if friendly in FLOW_CONCEPTS:
                    if span is None:
                        continue
                    if 60 <= span <= 120:
                        period_type = "Q"
                    elif 300 <= span <= 400:
                        period_type = "FY"
                    else:
                        continue  # half-years, nine-months, odd stubs
                else:
                    if start is not None:
                        continue  # balance-sheet items are point-in-time
                    period_type = "INSTANT"

                rows.append(
                    {
                        "ticker": ticker,
                        "metric": friendly,
                        "concept": concept,
                        "concept_rank": rank,
                        "unit": unit_key,
                        "period_type": period_type,
                        "start": start,
                        "end": end,
                        "value": val,
                        "fy": f.get("fy"),
                        "fp": f.get("fp"),
                        "form": f.get("form"),
                        "filed": f.get("filed"),
                        "frame": f.get("frame"),
                    }
                )

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    # Two layers of de-duplication:
    #  1. XBRL restates, so the same (metric, period, concept) appears in several
    #     filings. Keep the most recently filed value, which is the restated truth.
    #  2. Alias chains mean one period can be filled by two different concepts.
    #     Keep the highest-priority concept (lowest concept_rank).
    df = df.sort_values("filed").drop_duplicates(
        subset=["ticker", "metric", "concept", "period_type", "start", "end", "unit"],
        keep="last",
    )
    df = df.sort_values("concept_rank").drop_duplicates(
        subset=["ticker", "metric", "period_type", "start", "end", "unit"], keep="first"
    )
    return df


def _derive_q4(quarterly: pd.DataFrame, annual: pd.DataFrame) -> pd.DataFrame:
    """Most issuers never file a Q4 10-Q, so Q4 = FY minus the three quarters.

    Copart in particular reports Q4 only inside the 10-K, so without this step
    every fiscal Q4 is missing from the panel.
    """
    out = []
    for (ticker, metric), fy_rows in annual.groupby(["ticker", "metric"]):
        if metric == "eps_diluted":
            continue  # EPS does not sum cleanly; leave it to the reported value
        for _, fy in fy_rows.iterrows():
            fy_start, fy_end = pd.Timestamp(fy["start"]), pd.Timestamp(fy["end"])
            q = quarterly[
                (quarterly.ticker == ticker)
                & (quarterly.metric == metric)
                & (pd.to_datetime(quarterly.start) >= fy_start - pd.Timedelta(days=5))
                & (pd.to_datetime(quarterly.end) <= fy_end + pd.Timedelta(days=5))
            ]
            if len(q) != 3:
                continue
            already = quarterly[
                (quarterly.ticker == ticker)
                & (quarterly.metric == metric)
                & (pd.to_datetime(quarterly.end) == fy_end)
            ]
            if len(already):
                continue
            q4_val = fy["value"] - q["value"].sum()
            q4_start = pd.to_datetime(q["end"]).max() + pd.Timedelta(days=1)
            out.append(
                {
                    "ticker": ticker,
                    "metric": metric,
                    "concept": fy["concept"],
                    "unit": fy["unit"],
                    "period_type": "Q",
                    "start": q4_start.strftime("%Y-%m-%d"),
                    "end": fy_end.strftime("%Y-%m-%d"),
                    "value": q4_val,
                    "fy": fy["fy"],
                    "fp": "Q4",
                    "form": fy["form"],
                    "filed": fy["filed"],
                    "frame": "derived_fy_minus_q1q2q3",
                }
            )
    if not out:
        return quarterly
    log.info("derived %d fiscal-Q4 observations (FY minus Q1-Q3)", len(out))
    return pd.concat([quarterly, pd.DataFrame(out)], ignore_index=True)


def main() -> int:
    frames = []
    for ticker, info in COMPANIES.items():
        log.info("fetching %s (%s)", ticker, info["name"])
        data = _download(ticker, info["cik"])
        if data is None:
            log.warning("%s: skipped, could not download", ticker)
            continue
        df = _flatten(ticker, data)
        if df.empty:
            log.warning("%s: no usable facts", ticker)
            continue
        log.info("%s: %d facts across %d metrics", ticker, len(df), df.metric.nunique())
        frames.append(df)

    if not frames:
        log.error("no companies collected; is SEC_USER_AGENT set in .env?")
        return 1

    allf = pd.concat(frames, ignore_index=True)

    quarterly = allf[allf.period_type == "Q"].copy()
    annual = allf[allf.period_type == "FY"].copy()
    instant = allf[allf.period_type == "INSTANT"].copy()

    quarterly = _derive_q4(quarterly, annual)
    quarterly["end"] = pd.to_datetime(quarterly["end"]).dt.strftime("%Y-%m-%d")
    quarterly = quarterly.sort_values(["ticker", "metric", "end"])

    keep = [
        "ticker", "metric", "concept", "period_type", "start", "end",
        "value", "unit", "fy", "fp", "form", "frame",
    ]

    write_dataset(
        quarterly[keep],
        "sec_quarterly",
        source="SEC EDGAR XBRL company facts API (data.sec.gov), public domain",
        method=(
            "Downloaded the companyfacts bundle for CPRT, RBA, ACVA and PGR. Kept "
            "duration facts of 60-120 days as quarters. Where an issuer files no "
            "Q4 10-Q, fiscal Q4 is derived as the 10-K full year minus the three "
            "reported quarters (flagged frame=derived_fy_minus_q1q2q3). Where the "
            "same period appears in several filings the most recently filed "
            "restated value is kept."
        ),
        gaps=(
            "Diluted EPS is not derived for Q4 because per-share figures do not sum. "
            "Copart stopped tagging GrossProfit and cost of revenue after FY2020, so "
            "gross margin for recent quarters comes from the hand-curated panel in "
            "data/manual/cprt_quarterly_financials.csv instead. Segment detail (US vs "
            "International, insurance vs non-insurance units, ASPs) is reported only "
            "as XBRL dimensions, which the companyfacts API strips out, so that also "
            "comes from the manual panel. RB Global's gross transaction value is not "
            "an XBRL concept at all. The most recent fiscal quarter appears only "
            "after the 10-Q or 10-K is filed, which lags the earnings release by "
            "days to weeks."
        ),
        units="USD, or USD per share for eps_diluted, or share counts",
        frequency="quarterly",
    )

    write_dataset(
        annual[keep].sort_values(["ticker", "metric", "end"]),
        "sec_annual",
        source="SEC EDGAR XBRL company facts API (data.sec.gov), public domain",
        method="As sec_quarterly but keeping duration facts of 300-400 days as fiscal years.",
        gaps="Fiscal years differ across companies: Copart ends 31 July, the others 31 December.",
        units="USD, or USD per share for eps_diluted",
        frequency="annual",
    )

    write_dataset(
        instant[keep].sort_values(["ticker", "metric", "end"]),
        "sec_balance_sheet",
        source="SEC EDGAR XBRL company facts API (data.sec.gov), public domain",
        method="Point-in-time (instant) facts such as cash, PP&E, equity and goodwill.",
        gaps="Reported at each filing date, so the series is quarterly but irregular.",
        units="USD",
        frequency="quarterly (as filed)",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
