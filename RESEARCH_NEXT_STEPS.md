# Research tests and next deliverables

**Version 2 update:** Six executable research workflows, public carrier comparisons, operating sensitivities and validated private imports are now implemented. See [RESEARCH_WORKFLOWS.md](RESEARCH_WORKFLOWS.md) for current status, limitations and commands; it supersedes earlier implementation-status notes below.

## What we are trying to establish

Separate three questions: does Copart deliver better economics than IAA; does
its addressable market grow; and can those economics produce enough earnings
upside to justify the stock price? Industry growth alone benefits both platforms.
A superior business can still be a poor investment at the wrong price.

| Priority | Test | Evidence supporting Copart | Evidence against | Data and next deliverable |
|---|---|---|---|---|
| 1 | Matched net recovery | Higher insurer proceeds after seller fees, transport and storage for comparable vehicles | Premium vanishes after controlling for vehicle/claim mix and fees | Authorized sold-lot data; match year, make, model, mileage, damage, title, geography and sale week; report balance, sample size and uncertainty |
| 1 | Throughput and relistings | Shorter observed listing duration, fewer repeats and stronger confirmed sale completion | Persistent backlog or equal/better IAA outcomes | Daily authorized snapshots with platform/lot ID, timestamps, yard, sale date and explicit outcome; distinguish removal from sale and censored observations |
| 2 | Carrier mix and allocation | Remaining carriers grow and Copart allocation stabilizes | Other customers also reduce allocation | Monthly Progressive/Allstate, quarterly GEICO/Travelers and annual carrier weights; separate policies, claim frequency, TLF and uncertain allocation |
| 2 | Yard capacity near storms | More usable owned capacity near historical vehicle-loss exposure and faster post-event normalization | IAA has equivalent coverage or Copart's spare capacity stays idle | Yard addresses, acreage/ownership and NOAA events; normalize counties/zones, avoid double-counting overlapping catchments and compare several travel radii |
| 2 | Long-term total-loss supply | TLF gains outweigh falling claim frequency across realistic vehicle-value scenarios | Fewer insured claims overwhelm higher TLF | Policies/exposure × claims per exposure × total-loss fraction; validate against simple baselines before making forecast claims |
| 2 | Recoverable unit costs | Volume normalization produces material incremental profit after fuel and wage adjustments | Input inflation/capex absorbs gains | Quarterly consistent unit/cost panel, diesel, transport wages; bridge to EBIT, tax, shares and EPS |
| 3 | Buyer demand and pricing | Deeper buyer participation and higher net recovery despite fees | Fee increases reduce participation or seller recovery | Permitted bidder/export data, comparable fee schedules and destination-level export flows; exports are not Copart-specific and final bids are not sale prices |

Matched recoveries and throughput are the strongest direct competitive tests.
The supply and cost models test durability and earnings. Historical fees alone
cannot prove pricing power: observed retention and net outcomes are also needed.

## Completed in this follow-up

Built `src/build/tlf_backtest.py` and integrated it into the offline/site pipeline
and manual refresh workflow. The industry page now shows the comparison with a
table twin and full caveats. Five total unit tests cover CPI gaps and forecast
leakage protections.

- 15 identical held-out target quarters for three forecast rules.
- At each quarter-start origin, TLF training stops at Q-2, assuming a one-quarter
  publication delay. CPI features use completed earlier quarters, lags 1–3.
- The lag is selected afresh on training rows only. Candidate models use identical
  observations. Training expands; there is no random time-series split.
- MAE: spread + trend **1.69 points**; trend only **1.81**; last available actual **1.30**.
- RMSE: **2.02**, **2.04**, **1.61**, respectively.
- Conclusion: no demonstrated forecasting edge yet. Do not pitch the 0.66 in-sample
  R² as evidence that the model forecasts better than a simple baseline.
- Limitation: current revised data, assumed release delay and mixed CCC definitions;
  not a true real-time vintage backtest. Do not tune repeatedly on these 15 quarters
  and then call them untouched validation data.

## Inventory access findings

Checked official source pages during this follow-up:

- https://www.copart.com/robots.txt excludes `/public/data/` and sales-download
  endpoints while allowing the bare lot-search page; this does not establish a
  usable or complete public feed.
- https://www.iaai.com/robots.txt disallows `/Search` and `/Marketing/Search`.
- https://www.copart.com/content/us/en/terms-of-use describes use restrictions;
  source-specific license and publication rights still need checking.

Because this project explicitly requires respecting robots.txt, a production
IAA search scraper is not ready to implement against the blocked route.
Next: identify an authorized export/provider covering BOTH platforms, inspect its
field definitions and permitted research/aggregate publication use, then build an
import adapter and begin comparable daily snapshots. No access request, account
creation, subscription or third-party outreach has been sent.

Required fields: snapshot UTC, platform, stable lot ID, source URL, year/make/model,
mileage, damage, title, yard/state, scheduled sale date and confirmed outcome where
available. Each snapshot also needs requested scope, pages/records returned,
errors and completeness. A source outage must never look like a volume collapse.
Do not expose VINs or seller identities on the public site; aggregate results.

## Next implementation order

1. Collect a consistent monthly carrier-policy panel and add allocation scenarios.
2. Build the cost/valuation bridge with reported totals, explicit assumptions and
   sensitivity ranges; do not invent unavailable unit levels or seller fees.
3. Start inventory imports as soon as a suitable authorized source is available.
4. Join yard locations/capacity to normalized storm geography.
5. Extend TLF inputs with claim frequency; seek true release dates/vintages before
   asserting predictive performance or changing models based on the test results.
