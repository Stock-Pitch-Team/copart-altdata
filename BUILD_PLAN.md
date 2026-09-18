# Build plan — Tier 1 approved

Six projects, sequenced so each one produces a chart on the website rather than
a notebook only you can read. Audit update (18 September 2026): see PROJECT_REVIEW.md for verified status.
Two research projects have working implementations; the remaining projects are partial or unbuilt.

**The deliverable is the website**, not the code. Every project below ends in a
card on a page with a title a non-technical reader understands, a chart, a table
twin, and a source note. If a project cannot produce that, it is not done.

---

## Status right now

| # | Project | Thesis pillar | Status | On the site? |
|---|---|---|---|---|
| 6 | KPI panel from filings and calls | all | **Working** (SEC) + seeded (manual) | Yes, 6 charts |
| 3 | Total-loss-frequency nowcast | P4 | **Working**, R²=0.66 | Yes, 2 charts |
| 2 | Carrier-mix / addressable volume | P1 | Seeded, 3 data points | Yes, 1 chart, flagged thin |
| 5 | Fee-schedule archaeology | P3 | Not built; source rate-limited previously | Not yet |
| 4 | Storm-county exposure map | P2 | Partial: NOAA event rankings built; yard join missing | Yes, event chart only |
| 1 | Copart vs IAA inventory tracker | P1 P2 P3 | Not built; no history | Not yet |

Pillars: **P1** the loss is one customer and IAA bought its share ·
**P2** Copart's land and buyer liquidity are better · **P3** operating leverage ·
**P4** structural total-loss growth · **P5** valuation washed out.

---

## What already works, and what it proved

### Project 6 — the KPI panel (working)

`src/collect/sec_financials.py` pulls XBRL company facts for Copart, RB Global,
ACV Auctions and Progressive. No API key. Verified against the filings: Q3 FY26
operating income $464.3mn and revenue $1,237.1mn both match exactly.

Two things I had to solve that will bite you if you touch this file:

1. **Copart retagged revenue.** The concept `Revenues` stops in FY2020 and
   `RevenueFromContractWithCustomerIncludingAssessedTax` takes over. Without an
   alias chain, every recent quarter's revenue is silently blank. The collector
   now tries concepts in priority order.
2. **There is no Q4 10-Q.** Copart reports Q4 only inside the 10-K, so fiscal Q4
   is derived as full year minus the three reported quarters, and flagged
   `derived_fy_minus_q1q2q3` in the output.

**Known gap:** Copart stopped tagging `GrossProfit` after FY2020, and segment
detail (US vs international, insurance vs non-insurance units, ASPs) exists only
as XBRL dimensions, which the company-facts API strips out. So those come from
the hand-typed panel instead. That is why `data/manual` exists and is not
laziness.

### Project 3 — the nowcast (working, and this is the real edge)

The idea in one line: an insurer writes a car off when repair cost approaches the
car's value, so the driver of total-loss frequency is the **gap** between
repair-cost inflation and used-vehicle-value inflation.

From the August 2026 BLS release:

| Series | YoY |
|---|---|
| Motor vehicle maintenance and repair CPI | **+5.2%** |
| Used cars and trucks CPI | **−2.3%** |
| Spread ("the scissors") | **+7.6 points** |

Fitted on 28 quarters against the CCC total-loss-frequency series, with the
spread lagged three quarters plus a linear trend for the structural drift from
fleet ageing:

- R² 0.66, adjusted 0.63
- Spread coefficient +0.062 points per point of spread, p = 0.0002
- Structural trend +0.40 points per year, p = 0.0006
- 95% interval ±2.07 points

**Why it is an edge:** CCC publishes quarterly with a long lag and the sell side
quotes it months late — the J.P. Morgan note used data through calendar Q3 2025.
BLS CPI is monthly with a two-week lag. We get a read on salvage supply before
the authoritative number exists, from free public data.

**The honest finding, which you must not oversell:** the nowcast for calendar Q3
2026 is **22.2%** (interval 20.1 to 24.3), slightly *below* the 23.3% Copart
cited for Q2. The spread has narrowed from its peak because used-vehicle
declines moderated. So the correct claim is "total-loss frequency is at or near
record levels and structurally rising about 0.4 points a year", **not** "it is
accelerating". Saying the latter in the pitch would be wrong and a judge who
checks will catch it.

I added the trend term after the spread alone underpredicted recent levels by
about two points. That is defensible — every industry source attributes a
structural climb to fleet age and vehicle complexity — but you should be able to
explain in the room why the term is there.

---

## Week 1 — finish the quick wins

### 1. Project 5: fee-schedule archaeology (half a day)

**Question:** has Copart been able to raise buyer fees without losing buyers,
and has IAA discounted?

**How:** the Wayback Machine has snapshots of both companies' public fee
schedules going back years. Pull every snapshot from 2015 to 2026, parse the fee
tables, and compute the implied buyer fee as a percentage of sale price at
several price points for each company over time.

**Why it matters:** this is the cleanest available evidence on pricing power,
which is the revenue-per-unit line in the model. J.P. Morgan notes Copart's last
fee increase was November 2024. If we can show a decade of increases that stuck,
the "can they price?" question is answered with data rather than assertion.

**Status:** `src/collect/wayback_fees.py` does not exist yet. The Wayback API returned
HTTP 429 (rate limited) during testing, so it needs a slow, patient run with
backoff. Run it overnight.

**Output:** one line chart, two series (Copart, IAA), implied fee percentage over
time.

### 2. Project 2: extend the carrier-mix model (one day)

Right now the Progressive chart has **three data points**, which is too thin to
call a trend and is labelled as such on the site. Fix it:

- Write a collector for Progressive's monthly releases. They are published as
  8-K exhibits on EDGAR, which we already know how to read, so this reuses the
  SEC plumbing rather than scraping a website.
- Pull GEICO from Berkshire's 10-Q, Allstate and Travelers from their
  quarterlies, and NAIC market share tables for the carrier weights.
- Build the index: addressable total-loss units = Σ over carriers (policies in
  force × total-loss frequency × estimated Copart allocation).

**Why it matters:** this separates "Copart's customers are growing more slowly"
(carrier mix, largely out of Copart's control and partly self-correcting) from
"Copart is losing allocation within its customers" (a real competitive problem).
Your notes raise exactly this question and it is currently unanswered.

**Next action:** Progressive's August figures were due **18 September 2026**,
which is tomorrow. Add them the day they land.

### 3. Project 16 wrapper: positioning (two hours)

Short interest from FINRA, 13F holder changes from EDGAR, and the analyst target
history we already have. One chart showing ratings and targets at a trough
supports the "washed out" leg of the valuation argument. Low effort, and the
targets chart already exists so this is mostly extending it.

---

## Week 1–2 — start the two long-running projects immediately

These need to begin now because they accumulate value over time, not because
they are urgent.

### 4. Project 1: the inventory tracker (the flagship)

**Question:** is Copart's listing volume stabilising, and is IAA's growth
decelerating now that the Progressive transition has completed?

**How:** scrape both public lot-search sites daily. Capture per lot: lot ID, VIN,
year/make/model, damage type, title type, yard and state, first-seen date, sale
date, current bid, and where visible the seller. Roll up to weekly counts by
platform, state and seller type.

**Why it matters most:** Barclays quotes a third-party feed showing Copart −1.4%
and IAA +14.9% in May–June 2026. We cannot verify or extend that number, and it
is the single most important fact in the bear case. This project replicates it
for free and gives us a read on FY27 Q1 **before the November print**.

**The high-value extra:** IAA lot detail pages historically display the seller
name on many insurance lots. If that holds, we can measure Progressive's share
of IAA's inventory directly, and detect any Progressive lots reappearing at
Copart by state. Copart generally hides seller names, so there we infer seller
type from title and damage codes instead.

**Design constraints I have already established:**

- Both `copart.com` and `iaai.com` return HTTP 200 from this machine, so the
  sites are reachable. Neither needs a login for search pages.
- **Do not run this from GitHub Actions.** Datacenter IPs get blocked by both
  sites. It runs locally on a schedule; only the keyless API collectors are safe
  to automate in CI.
- Rate limit to a few requests per second, from one IP, public pages only, and
  honour `robots.txt`. Getting our IP banned costs us the whole dataset.
- Output is labelled **"listings observed"**, never "units sold". We are counting
  listings on a website, not company-reported units, and conflating the two in a
  pitch would be indefensible.

**Realistic expectation:** the tracker has **no history**. It starts producing a
usable trend after two to three weeks and a confident one after six. Start it
this week or it will not be ready for the pitch.

**Backtest plan:** once we have several weeks, align weekly listing counts
against the reported quarterly unit growth from FY24–FY26 in the KPI panel, and
report the correlation honestly. If listings do not track reported units, we say
so and use the tracker only for direction.

### 5. Project 4: storm-county exposure map (one to two days)

**Question:** is Copart's owned-yard network genuinely better placed for
catastrophe volume than IAA's?

**How:** NOAA's Storm Events database is a free bulk CSV back to 1950 and is
confirmed reachable. Geocode every Copart yard (roughly 200 US locations, public
on their site) and every IAA branch (roughly 200, public). Compute each company's
capacity within 100 miles of the counties that historically generate the most
hail, flood and hurricane damage.

**Why it matters:** it converts "Copart owns its land, IAA leases temporary lots"
from an assertion into a measurement. It is also a genuinely good-looking map,
which matters for a pitch.

**Be honest about the timing, though:** NOAA's August/September 2026 update puts
a **75% chance of a below-normal Atlantic hurricane season** under El Niño, and
CSU forecasts below-average landfall probability. So catastrophe upside is *not*
available as a base-case driver this fiscal year. Frame the land advantage as
durable optionality, and note that hail and flood events, which are not covered
by the hurricane forecast, remain live. Your original notes lean on a
catastrophe patch; the forecast does not currently support that, and the pitch
should say so before a judge does.

---

## Week 2–3 — if the above is on track

- **Project 11, cost decomposition.** Regress Copart's facility cost per unit on
  EIA diesel prices, transport wages and unit volume, to split the +12.7% cost
  per car into fuel, wages and volume deleverage. This directly sizes the
  operating-leverage claim, which is the weakest-evidenced part of the thesis
  today. Needs the EIA key.
- **Project 10, export flows.** Census trade API by HS code and destination, to
  verify the Middle East rerouting and international buyer depth. Works keyless
  for small queries, so it can start before the key arrives.
- **Project 9, expert calls.** Start outreach in week 1 because scheduling takes
  weeks. Ten to fifteen calls with former IAA and Copart account managers,
  insurer total-loss managers, and tow operators who haul for both. **The one
  question that matters most:** are IAA's volume incentives tiered rebates that
  step down, or permanent fee cuts? Nothing in public data answers that, and the
  whole "IAA cannot sustain this" argument rests on it.

---

## What I corrected in the thesis, and why it matters

Two substantive changes from your notes. Both make the pitch more defensible.

1. **The inflection is FY27 Q2–Q3, not Q1–Q2.** The Progressive shift began
   around January 2026, so FY27 Q1 (August to October 2026) still compares
   against a pre-loss base and will probably print another 6–8% decline. If you
   pitch Q1 as the inflection and it prints −7%, the thesis looks broken in
   November. Pitch Q2, and treat a weak Q1 as the entry point.

2. **The mechanism is not "Progressive comes back".** Copart *chose* to walk
   away from Progressive's pricing; Adair said on the call, "We don't need to
   play that game." So recovering that specific volume requires Copart to concede
   or Progressive to be poorly served. The durable argument is: the rest of the
   book is growing 2.3%, IAA's wins cost it 110 basis points of take rate, and
   Copart's idle fixed costs mean any stabilisation produces outsized margin
   recovery. That argument does not need Progressive to return.

---

## Rules this project holds itself to

These are enforced in code and stated on the website's methods page.

1. **No invented numbers.** If it is not in a filing, a transcript, a public
   dataset, or our own calculation from those, it does not appear.
2. **Derived is labelled derived.** RB Global's implied Q1 take rate of 20.6% is
   computed from the disclosed H1 and Q2 figures, and the table says so.
3. **Scraped counts are listings, not sales.**
4. **Models state their sample size.** Every regression reports n, R² and a
   confidence interval, and we say plainly when a sample is small.
5. **Every chart has a table twin.** No number is reachable only by hovering.
6. **Disconfirming evidence gets equal billing.** The competitive data supporting
   the bear case is the first chart on its own page, not buried.
7. **Licensed research is credited, never republished.** See Part 6 of
   `SETUP.md`. This is the rule most likely to cause real trouble if broken.

---

## Immediate next actions

1. **You:** get the BLS, Census and EIA keys (Part 3 of `SETUP.md`), about 15
   minutes.
2. **You:** create the GitHub repo and turn on Pages (Part 5), about 10 minutes.
   Run the PDF check before pushing.
3. **You:** start expert-call outreach on LinkedIn today, because it is the
   longest lead time in the whole plan.
4. **Me, on your go-ahead:** build the inventory tracker, the storm map, the
   Wayback fee collector, and the Progressive monthly collector.
5. **Tomorrow, 18 September:** add Progressive's August policy figures.
6. **Modelling lead:** replace the placeholder scenario EPS numbers with output
   from the three-statement model, driven by units × revenue per unit ×
   incremental margin, so the scenario table stops being labelled provisional.
