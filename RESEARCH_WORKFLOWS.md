# Research workflows (version 2, 18 September 2026)

The six studies now have executable workflows, tests and a Research lab page. **Implementation is not the same as validated evidence.** The public carrier panel and reported financial baseline are measured; the allocation, supply and earnings extensions are scenarios. Sold-lot, daily inventory and geographic comparisons have no real imported sample yet.

## Run and publish

```powershell
.venv/Scripts/python.exe -m unittest discover -s tests -v
.venv/Scripts/python.exe run_all.py --site
.venv/Scripts/python.exe -m src.site.validate_site
.venv/Scripts/python.exe -m http.server 8765 --bind 127.0.0.1 --directory docs
```

Open `http://127.0.0.1:8765/research.html`. GitHub Pages repeats tests, rebuild and link/JSON validation before deployment. A failed pipeline step now yields a nonzero exit code. Public carrier inputs are manually sourced snapshots, not a live collector; refresh those CSV rows from the linked releases. Automatic refresh remains disabled while older site narratives require editorial review.

## Imports

Header-only CSV templates are in `data/templates`. Import complete files using:

```powershell
.venv/Scripts/python.exe -m src.analysis.imports sales path/to/sales.csv
.venv/Scripts/python.exe -m src.analysis.imports inventory path/to/inventory.csv
.venv/Scripts/python.exe -m src.analysis.imports manifests path/to/manifests.csv
.venv/Scripts/python.exe -m src.analysis.imports yards path/to/yards.csv
.venv/Scripts/python.exe -m src.analysis.imports storms path/to/storms.csv
.venv/Scripts/python.exe run_all.py --site
```

Each command validates first, then replaces that dataset in `data/private`, which is excluded from Git. Keep cumulative inventory history in each replacement. Never put private files into `data/manual` or `docs`. Do not enter VINs, addresses of individuals, account tokens or names; extra columns are rejected. Publishable aggregates appear in `data/processed/research_import_results.json`. Raw identifiers and source URLs from private imports do not appear there. GitHub refresh uses --public-only to preserve published imported aggregates, since private source rows are intentionally absent in CI. Local full builds recalculate from local private files; rebuilding a fresh clone without those files resets imported studies to awaiting data. Review aggregates before a public push, especially when samples are small; aggregation alone does not guarantee confidentiality.

All fields are required, dates are ISO YYYY-MM-DD, platforms are exactly Copart or IAA, numbers must be finite, and source_url must identify a public source or authorized provider. Blank unknown costs are rejected: zero means verified no cost, not unknown. Identifier uniqueness is enforced at the keys below. Source URLs document provenance, not permission; use only data you are entitled to analyze and share.

| File | Key | Interpretation |
|---|---|---|
| sales | platform + lot_id | One final confirmed sale per lot; USD price and seller fees/transport/storage, mileage in miles. Use consistent make/model/damage/title/region classifications. Do not load bids, reserves, cancelled auctions, estimated prices or repeated sales. |
| inventory | platform + lot_id + date | One daily status: active, sold or withdrawn. Stable IDs; consistent market coverage. Sold must mean confirmed sale. |
| manifests | platform + date | complete = 1 only when the entire intended, consistent sample was collected; 0 for outages/partial collection. Include successful empty days. Every inventory row needs a manifest. |
| yards | platform + yard_id | Decimal latitude/longitude; acres and ownership (owned, leased, unknown). Unknown acreage cannot be replaced with zero; keep incomplete yards out and disclose coverage. Acreage is retained privately but not used as a capacity estimate. |
| storms | event_id | Unique normalized event with decimal coordinates. Use a stable event ID, not each location row of a multi-location event. County/forecast-zone centroid approximations must be declared when interpreting results. |

## How calculations work

**Recovery:** deterministic greedy nearest-mileage matching without replacement, exact year/make/model/damage/title/region/sale-week and 10,000-mile caliper. Net proceeds = sale price minus seller fees, transport and storage. Outputs include matched fraction, signed and absolute mileage gaps, mean paired USD advantage, and seeded percentile bootstrap interval (2,000 resamples; withheld below ten pairs). Order can affect matches; bootstrap treats pairs as independent, so carrier/yard clustering and unobserved condition remain limitations. No causal or population claim is justified by this exploratory estimator.

**Inventory:** use complete days only, count explicit confirmed sales, unresolved/withdrawn lots, first-observed-active to first-confirmed-sale duration, and active reappearances after absence on an intervening complete snapshot. A source outage is neither a sale nor a relisting. The reported sale fraction has unequal observation windows and is not a standardized 30-day sell-through rate. Sold-only median has selection bias; first observation is left truncated. A survival model and matched duration comparison require reliable original listing dates and richer cohort fields; they are not implemented in this version.

**Carrier mix:** June 2026 versus June 2025 auto policy growth is 8.82% for Progressive (agency plus direct) and 2.80% for Allstate Protection. Progressive August update is 8.13%. These are exposure indicators, not claims or Copart assignments. Allocation sensitivity normalizes the starting book to 100; Progressive weight and retained allocation are assumptions, and Allstate growth is only a proxy for the other book. Claims and TLF are held flat. GEICO/Travelers and actual carrier allocations remain unmeasured.

**Geography:** nearest-yard great-circle distance using Earth radius 3,958.7613 miles; union coverage within 50/100/150 miles counts an event once per platform. Identical storms must be used for both platforms. No full network is populated. This does not model road distance, vehicle concentration, event severity, spare capacity, yard openings over time, or post-storm clearance. A partial network must never be described as national coverage.

**Supply:** start volume 100 and TLF 22%; five years of compounded exposure growth and claims-frequency change multiplied by ending/starting TLF. Outputs include break-even ending TLF. All assumptions are explicit; this is a sensitivity analysis, not a forecast calibrated to the CPI model.

**Earnings:** FY2026 SEC baseline, USD millions: service 3,969.520; vehicle sales 696.689; facility operations 1,755.747; purchased-vehicle costs 616.463; other operating costs 641.409; interest 181.923; other income .464; noncontrolling loss 3.873; effective tax 354.580 / 1,834.977; diluted shares 956.860 million. Other operating costs aggregate depreciation, stock compensation and G&A. Zero growth reconciles to operating income 1,652.590 and EPS 1.5512 (reported rounded 1.55). Facility variable share is an assumed 60%; volume and service RPU are separate. Cost inflation bundles fuel/wages; no disclosed split is invented. Scenario interest and share changes are visible. ACV, purchase accounting, capex and working capital are excluded; this is not a three-statement valuation model. Interactive controls keep interest/shares flat, unlike the Recovery/Expansion table's assumed 1% share reduction.

## Where to pick up

1. Obtain a modest authorized sold-lot panel with actual seller costs; normalize categories and inspect matching coverage before enlarging the sample.
2. Collect cumulative inventory snapshots with completeness manifests and original listing dates; add cohort-aware survival analysis once censoring assumptions can be checked.
3. Source complete dated Copart/IAA yard networks and normalized NOAA coordinates; manually audit locations before interpreting coverage.
4. Extend public exposure histories and carrier breadth. Keep allocation ranges until there is actual evidence for the weights.
5. Replace assumed fixed/variable costs with defensible disclosure-based bounds; add fuel/wage data only when an exposure split is justified, and reconcile acquisition effects separately.
6. Require TLF predictive improvement over the last-observation baseline before using the nowcast as a pitch catalyst. Review the legacy valuation placeholders before calling the pitch complete.

## Three findings for the pitch

Progressive's June auto policy book grew 8.82% against Allstate Protection's 2.80%, making carrier allocation a potentially larger driver of Copart's volumes than a single industry growth rate suggests. In the five-year sensitivity, 1% annual exposure growth and 5% annual claims-frequency declines require TLF to rise from 22% to roughly 27.05% just to hold salvage supply flat. The historical spread-plus-trend TLF model has 1.69-point MAE against 1.30 for the last-actual baseline, so the repair-cost mechanism is economically plausible but is not yet a demonstrated forecasting edge.
