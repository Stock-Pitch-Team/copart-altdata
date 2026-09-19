> Follow-up: historical validation is now implemented and published. On 15 test
> quarters, spread + trend MAE is 1.69 points versus 1.30 for last available actual.
**Version 2 update:** Six executable research workflows, public carrier comparisons, operating sensitivities and validated private imports are now implemented. See [RESEARCH_WORKFLOWS.md](RESEARCH_WORKFLOWS.md) for current status, limitations and commands; it supersedes earlier implementation-status notes below.

> This uses current revised data and assumed publication delay, not vintage data.
> See RESEARCH_NEXT_STEPS.md for the prioritized evidence plan and inventory access findings.

# Verified project review — 18 September 2026

This is a useful, shareable **research v1**, not a completed investment pitch.
The site is a static Python/Jinja/ECharts build: six pages, 19 charts with table
views, 11 manual CSVs and 12 processed datasets with provenance sidecars.

## Complete and reproduced

- SEC collector for CPRT, RBA, ACVA and PGR, with revenue-tag aliases and derived Q4 flows.
- BLS repair/used-vehicle and other CPI inputs through August 2026.
- TLF model: 28 observations, chosen lag 3 quarters, R² 0.656, adjusted R² 0.629.
  CY2026 Q3 fitted value 22.17%, residual band 20.10–24.24%; latest actual 23.3%.
- NOAA event aggregation: county/forecast-zone, state and year/type outputs.
- Six-page static site, theme switch, charts/tables and methods disclosure.
- Existing manual KPI, analyst-target, catalyst and scenario panels.

## Partial or not implemented

| Workstream | Actual state | Next concrete deliverable |
|---|---|---|
| KPI panel | Working, manually maintained segment metrics | Public URLs/page references and reconciliation checks for every key input |
| TLF nowcast | Reproduces; exploratory in-sample model | Expanding-window backtest against trend-only and last-actual baselines; consistent CCC definition |
| Carrier mix | Three Progressive observations; no model | Monthly PIF history plus carrier weights and allocation sensitivities |
| Storm advantage | NOAA rankings only | Normalize county/zone geography; geocode both yard networks; join capacity and exposure |
| Inventory tracker | No collector and no history | Resolve permitted data access; start timestamped daily snapshots and coverage diagnostics |
| Fee archaeology | No collector | Comparable dated fee schedules by buyer/payment/title class |
| Valuation | Assumed EPS, margins and probabilities | Units × revenue/unit × cost build; cash, ACV acquisition and buybacks; current peer estimates |
| Costs, exports, positioning, expert calls | Not implemented (targets chart exists) | Diesel/wages/unit bridge first; then selected corroborating studies |

`BUILD_PLAN.md` and `altdata_ideas.md` describe ambitions, not implemented features.
No inventory observations exist to backtest yet. Prospective observations cannot
be validated against earlier years without a separately acquired historical feed.

## Corrections made for this release

- Fixed a calendar-gap bug in CPI annual changes: October 2025 repair CPI is
  absent, so shifting 12 rows matched the wrong prior month. Annual changes now
  join the same month one year earlier without filling missing data. This corrects
  39 observations across affected series. August repair inflation is **5.24%**,
  not 7.8%; versus used vehicles at **-2.32%**, the spread is **7.56 points**,
  not 10.1. The nowcast is **22.17%**, still 22.2% rounded. Regression tests
  cover missing intervening months, missing prior-year observations and normal history.

- Removed false claim that inventory history is already accumulating.
- Added visible working-draft status to every page.
- Corrected FY26 Q4 revenue from a rounded headline entered as $1,200m to
  **$1,152.439m** and annual headline revenue to **$4.666209bn**, from the
  [SEC earnings statement](https://www.sec.gov/Archives/edgar/data/900075/000119312526387902/cprt-ex99_1.htm).
  Versus the stored ~$1,140m consensus, the revenue beat is only about **1.1%**, not 5.3%.
- Made scenario price equal EPS × P/E: $22.50, $28.875 (displayed $28.88),
  $37.38 and $47.50. Weighted displayed value is ~$31.70, about 7.2% above
  the stored $29.57 reference price; this does not establish compelling asymmetry.
- Corrected the false claim that CPRT is the largest historical peer discount.
  Peer multiples remain dated November 2025 and are not a current comparison.
- Distinguished consolidated RB Global take rate from IAA automotive economics.
  The [RB Global release](https://investor.rbglobal.com/news/news-details/2026/RB-Global-Reports-Second-Quarter-2026-Results/default.aspx)
  attributes its decline to both acquisition mix and automotive incentives; it
  does not quantify the share attributable to Progressive or prove incentives are unsustainable.
- Removed assertions that most unit-cost inflation is fixed-cost deleverage or
  that three margin points necessarily return. That decomposition is unbuilt.
- Labelled model uncertainty as an approximate residual band, with no held-out validation.
- Added explicit Pages deployment, including after a successful manual refresh.
  Bot commits alone do not trigger branch-based Pages builds.
- Excluded local assistant settings. Licensed reports, extracted report text,
  caches, raw payloads and .env remain outside Git.

## Remaining research and engineering risks

1. Lag selection maximizes in-sample adjusted R²; trend is not causal evidence of
   fleet ageing. The 28-point CCC panel is manually transcribed, with two missing
   recent quarters and a definition caveat. Audit the chart readings, then test
   forecasts with only data available at each historical forecast date.
2. A three-quarter lag means today's CPI does not directly drive today's nowcast.
   Quarterly CPI averages can be partial; add month counts. The model does not
   project beyond the CPI calendar, despite lagged features potentially allowing it.
3. Q1 RBA take rate was approximated by averaging H1 and Q2 rates; use GTV-weighted
   service-revenue arithmetic or the Q1 filing instead. Treat it as provisional.
4. NOAA property damage covers all property, not vehicles; event counts are not
   salvage units. CZ_NAME mixes counties and forecast zones. No capacity advantage
   for Copart has been demonstrated yet.
5. Many narrative statements, reference prices and dates are hard-coded. Rebuilding
   charts does not refresh the thesis. Automatic weekly refresh is deferred;
   `refresh.yml` remains manually callable after review and SEC secret setup.
6. Collectors can fall back to stale cache or partially overwrite company coverage;
   provenance currently records processing time rather than original fetch time.
   Add freshness/coverage gates and preserve last-good data before unattended refresh.
7. `run_all.py` returns success if the site builds even when another stage fails.
   CSV validation checks shape, not economic consistency. Add semantic checks for
   sources, dates, revenue bridges, scenario arithmetic and required company coverage.
8. SEC duration filtering does not derive Q2/Q3 cash-flow facts from year-to-date
   disclosures; weighted-average diluted shares are duration facts but currently
   classified as instant and omitted. Not blocking the current charts, but fix
   before using this panel for a three-statement model.
9. Dependencies use minimum versions rather than a lockfile. Chart runtime depends
   on a CDN, with table fallback. Some chart labels can become dense on phones.
10. Static research figures and selected public disclosures were checked; this is
    not a full independent certification of every historical manual datum.

## Where to pick up

1. **First: finish the evidence audit and valuation.** Reconcile all key reported
   figures to exact filing tables, refresh peer dates, and create the unit/RPU/cost
   bridge. Keep the existing long thesis conditional on those outputs.
2. **In parallel within the team: start the inventory dataset.** Access feasibility
   is the gating step. Publish coverage and first/last-seen logic; never equate
   disappearance with a sale or listings with reported unit volume.
3. **Next: validate TLF and extend carrier mix.** Compare out-of-sample forecast error
   and collect Progressive plus the other major carriers before claiming a mix effect.
4. **Then: join yards to storm exposure and build cost decomposition.** These test
   the two largest unproven advantages: capacity positioning and recoverable margin.
5. **After reliability work: enable scheduled refresh.** Add the SEC contact secret,
   freshness gates, explicit failure reporting and data-driven narrative updates.

## Reproduction and team publishing

- Validate inputs: `.venv/Scripts/python.exe run_all.py --check`
- Reproduce model + site offline: `.venv/Scripts/python.exe run_all.py --site`
- Serve: `.venv/Scripts/python.exe -m http.server 8765 --directory docs`
- NOAA is separate: `.venv/Scripts/python.exe -m src.collect.noaa_storms`
- Edit templates in `src/site/templates` and narratives in `src/site/build_site.py`,
  not generated HTML. Rebuild, review, commit and push to `main`.
- GitHub Pages uses **GitHub Actions**, publishing `docs/` with `pages.yml`.
- Repository: https://github.com/stock-pitch-team/copart-altdata
- Site: https://stock-pitch-team.github.io/copart-altdata/
