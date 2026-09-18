# Copart Alt-Data Project Menu
*Idea list for approval. Each item states what it would prove, what would falsify the thesis, the source, cost, and effort. Free-first. Nothing here fabricates data; every project ends in a chart with a stated source and method.*

Thesis pillars each project maps to:
- **P1** IAA's gains are one customer plus incentives; Copart's ex-Progressive book is growing.
- **P2** Copart's land, buyer liquidity and recoveries are superior, so allocation should stabilize or return.
- **P3** Operating leverage: cost per car is inflated by under-utilization and diesel; volume stabilization restores margin.
- **P4** Structural funnel: total-loss frequency, aging fleet, repair inflation.
- **P5** Valuation and positioning are washed out.

Effort: S = a day or two, M = a week, L = multi-week with ongoing collection.

---

## Tier 1 — build these first (highest evidence-per-hour)

### 1. Copart vs IAA live inventory tracker (flagship) — P1, P2, P3 — Effort L
**What:** Scrape both public lot-search sites daily. Copart's lot search and yard pages and IAA's vehicle search are browsable without login. Capture per lot: lot ID, VIN, year/make/model, damage type, title type, odometer, yard/state, first-seen date, sale date, current bid, and where visible the seller and final price. Roll up to weekly counts by platform, state, seller type (insurance vs dealer/fleet by title and damage codes), and yard.
**Proves:** Whether Copart's listing volume is stabilizing and whether IAA's growth is decelerating after the Progressive transition completed. This is a nowcast of the quarterly unit KPIs both companies report, and it lets us publish an estimate for FY27 Q1 before the November print.
**Bonus:** IAA lot detail pages historically display the seller name for many insurance lots (e.g. "Progressive"). If so, measure Progressive's share of IAA's inventory directly and detect any Progressive lots reappearing at Copart by state. Copart generally hides insurance seller names, so use title/damage codes and yard patterns instead.
**Falsifies if:** Copart listings keep declining after Jan 2027 with no IAA deceleration.
**Backtest:** Align weekly counts with the reported quarterly unit growth from FY24–FY26 (KPI panel, project 6). Barclays uses a third-party feed for the same purpose ("industry data shows CPRT −1.4%, RBA +14.9% in May–Jun"), so this replicates a sell-side input for free.
**Source and cost:** copart.com and iaai.com public pages; Python with Playwright or requests. Free. Paid shortcut: Apify Copart scrapers (~$20–50/month). Check robots.txt and terms; scrape slowly (a few requests per second), from a fixed IP, and only public pages. If blocked, a residential proxy is ~$15–30/month.
**You need to do:** Register free Basic accounts on both sites yourself (needed to view sold prices in some cases). Never put credentials in the repo.

### 2. Carrier-mix and addressable-volume model — P1 — Effort M
**What:** Build a monthly index of Copart-addressable total-loss units = Σ over carriers (policies in force × total-loss frequency × estimated Copart allocation). Inputs: NAIC premium market share by carrier (public), Progressive monthly PIF (free, monthly, next release 18 Sep 2026), GEICO from Berkshire 10-Q, Allstate/Travelers quarterly PIF, State Farm annual. Allocation estimates from public reporting (Progressive ~90% IAA) and expert calls (project 9).
**Proves:** How much of Copart's −7.5% is carrier mix (its customers growing slower) versus true allocation loss, and what happens to Copart's addressable volume if Progressive's growth keeps decelerating (10.2% → 8.8% Apr–Jun) while GEICO/State Farm re-accelerate. Directly answers your "carrier mix effect" question.
**Falsifies if:** Even ex-Progressive, Copart's carrier base is shrinking faster than the market.
**Source and cost:** SEC EDGAR (free, needs a User-Agent header), Progressive IR, NAIC market share reports (public PDFs). Free.

### 3. Total-loss frequency and salvage-supply nowcast — P4 — Effort M
**What:** Regress historical total-loss frequency (CCC quarterly data points from Crash Course releases, plus every TLF figure Copart has cited on calls) on: BLS CPI motor vehicle repair (series CUSR0000SETD), Manheim Used Vehicle Value Index (free monthly), average vehicle age (S&P Mobility releases), FHWA VMT (monthly), and collision frequency (ISS/Verisk press releases). Project TLF forward under used-price scenarios.
**Proves:** The funnel is still widening and quantifies the risk if Manheim falls (e.g. how far used prices must drop before TLF stops rising). Turns the qualitative "aging fleet, repair inflation" bullet into a forecast with sensitivities.
**Source and cost:** BLS API (free key), FRED API (free key), Manheim (free monthly PDF), FHWA Traffic Volume Trends (free), CCC/Verisk press releases. Free.

### 4. Weather and catastrophe exposure map: who owns the storm counties — P2 — Effort M
**What:** Pull NOAA Storm Events Database (free CSV, 1950–present) for hail, flood, hurricane, tornado by county. Geocode every Copart yard (~200+ US, addresses public on copart.com) and IAA branch (~200, public on iaai.com). Compute each company's owned-yard acreage and capacity within 100 miles of the highest historical salvage-generating counties. Overlay NOAA's current-season outlook.
**Proves:** Copart's yard network is closer to and larger in the counties that generate CAT volume; quantifies "IAA relies on temporary lots." Also shows this fiscal year's CAT leg is weak (NOAA 75% below-normal season), which keeps us honest and reframes CAT as optionality rather than base case. Hail belt (TX, CO, OK, MN) and flood events are not covered by the hurricane forecast and remain live.
**Falsifies if:** IAA's footprint is equally close to the high-loss counties.
**Source and cost:** NOAA NCEI Storm Events (free), company location pages (free), Nominatim/Census geocoder (free), GeoPandas. Free.

### 5. Fee-schedule archaeology and pricing power — P3 — Effort S
**What:** Use the Wayback Machine to pull every historical snapshot of Copart's and IAA's public buyer fee schedules and membership pricing (2015–2026). Build the implied buyer fee as % of sale price at multiple price points over time for both platforms. Track IAA seller-side or buyer-side fee cuts that would show up as take-rate concessions.
**Proves:** Copart has raised fees repeatedly (last increase Nov 2024, per JPM) without losing buyers; measures the fee gap between the two platforms and whether IAA has discounted. Directly informs the "can management raise price if volume is flat" question and the revenue-per-unit line in the model.
**Source and cost:** web.archive.org (free, has an API). Free.

### 6. Quarterly KPI panel from every earnings call since 2018 — all pillars — Effort M
**What:** Neither company publishes a clean KPI table. Pull transcripts (Motley Fool, company IR, SEC 8-K exhibits) for Copart and RBA/IAA (and legacy IAA 2019–2022) and extract every stated KPI with an LLM into a tidy quarterly panel: US insurance units, non-insurance units, international units, ASPs, revenue per unit, cost per car, inventory, TLF cited, CAT units and CAT cost, buyback dollars, RBA automotive lots, GTV, take rate, SLAs mentioned.
**Proves:** Foundation for the model and for backtesting projects 1–3. Also lets us show the take-rate versus volume trade-off at RBA over six quarters in one chart, which is the crux of P1.
**Source and cost:** Free transcripts; Claude API for extraction (a few dollars). Requires manual spot-checks against source text.

---

## Tier 2 — strong differentiation, more effort

### 7. Matched-lot net recovery study: Copart vs IAA — P2 — Effort L
**What:** From the tracker (project 1), match sold lots across platforms on year/make/model/trim, damage type, odometer band, title type, and region. Compare final sale price relative to the platform's stated pre-accident value (Copart "Est. Retail Value," IAA "ACV") and the rate of relisting (unsold, re-run) as a liquidity measure. Segment by international-export-prone models (Toyota Camry/Corolla, F-150, Honda Accord).
**Proves or disproves:** The core value proposition claim that Copart's buyer base delivers higher recoveries for insurers, which is the reason allocation should not be won on fee concessions alone. If IAA recoveries are equal, the thesis weakens and we should say so.
**Source and cost:** Requires sold-price visibility (free member accounts). Free.

### 8. Satellite yard-utilization index — P2, P3 — Effort L
**What:** For the top ~60 yards by size on each platform, pull free imagery: NAIP (USDA, ~0.6 m, annual or biennial, via Microsoft Planetary Computer or USGS EarthExplorer) and Sentinel-2 (10 m, every 5 days, via Copernicus Data Space). Estimate vehicle-occupied area fraction per yard over time with simple thresholding or a small segmentation model. Supplement with county parcel records for acreage owned vs leased and recent land purchases.
**Proves:** Copart's spare capacity (utilization down as volumes fell) and IAA's strain (utilization up, more overflow lots). Utilization also converts directly into the operating-leverage argument: how many units Copart can absorb with no incremental land.
**Source and cost:** Free imagery; parcel data free in most counties (Regrid has a paid API, ~$100+ if we want it clean). Effort is the cost.

### 9. Structured channel checks — P1, P2 — Effort M (calendar time)
**What:** 10–15 short calls with: former IAA and Copart regional or account managers, insurer total-loss / salvage vendor managers (Progressive, Allstate, GEICO, USAA, regional carriers), independent tow operators who haul for both, and two or three professional rebuilders/exporters. Fixed 10-question script. Key questions: structure of volume incentives (tiered rebate vs flat fee cut), contract term and 90-day termination clause use, SLAs insurers actually score (days to pick up, days to title, days to sell), any service degradation at IAA since the volume surge, and what would trigger a re-allocation.
**Proves:** The mechanism behind P1. Without this we cannot say incentives are temporary.
**Source and cost:** LinkedIn outreach (free), In Practise summaries (some free), Tegus/AlphaSense are paid (skip unless the school has access). Free but takes weeks.

### 10. International buyer demand: export flows and search interest — P2 — Effort M
**What:** US Census International Trade API (free key): monthly exports of HS 8703 (passenger vehicles) and 8704 by destination country and by port (Savannah, Houston, Newark, Baltimore, Miami). Track the Middle East drop (UAE, Oman, Saudi) versus re-routing to Nigeria, Ghana, Georgia, Lithuania, Poland, Dominican Republic, Guatemala, Honduras. Add Google Trends (pytrends, free) for "copart" and "iaai" by country and Freightos/Drewry container indices for buyer landed cost.
**Proves:** Copart's claim that international buyers (38% of units, 46% of dollars) rerouted after the Middle East conflict, and that international bidder depth is intact; export demand supports ASPs independently of Manheim.
**Source and cost:** Census API (free key, instant), pytrends (free), Freightos FBX (free index). Free.

### 11. Cost-per-car decomposition — P3 — Effort S/M
**What:** Regress Copart's quarterly US facility cost per unit (project 6 panel) on EIA weekly on-highway diesel (free), BLS wages for transportation and warehousing, and unit volume. Decompose the +12.7% into fuel, wage, and fixed-cost deleverage. Forecast cost per car under stable volume and normalized diesel.
**Proves:** How much of the margin hit is reversible. This is the number that turns "operating leverage" from a slogan into a margin bridge.
**Source and cost:** EIA API (free key), BLS (free). Free.

### 12. Public-sector salvage contract awards — P1 — Effort M
**What:** State and municipal procurement portals (state DOT/DMV surplus, police fleets, GSA Fleet, county governments) publish salvage-auction contract awards, bidders, and often the fee terms. Search for Copart, IAA, Insurance Auto Auctions, and RB Global awards 2022–2026.
**Proves:** A rare public window into actual fee schedules and who is winning on price versus service. Non-obvious and nobody on the sell side cites it.
**Source and cost:** State procurement sites, SAM.gov (free), Bonfire/BidNet (free registration). Free.

---

## Tier 3 — sentiment, positioning, corroboration

### 13. Buyer sentiment across social and forums — P2 — Effort M
**What:** Reddit (r/Copart, r/Flipping, r/askcarsales, r/Justrolledintotheshop, r/mechanicadvice), YouTube rebuilder channel comments, Facebook groups, IAA and Copart buyer forums, and app-store reviews for the Copart and IAA apps (review counts as an active-buyer proxy; sentiment on fees, app reliability, title delays). Classify with an LLM and trend monthly. Compare buyer complaints about IAA post-volume surge.
**Source and cost:** Reddit API (free app registration, rate limited), YouTube Data API (free key), app-store scrapers (free Python libs). Free.

### 14. Job postings and employee reviews as an operating-strain gauge — P2, P3 — Effort S
**What:** Weekly counts of Copart vs IAA postings on Indeed/LinkedIn/company career pages by role (yard, drivers, CAT response, title clerks) and location; Glassdoor/Indeed reviews mentioning overflow lots, overtime, backlog. Copart hiring in CAT regions ahead of a storm would also be a leading signal.
**Source and cost:** Career pages and Indeed (free scrape, careful rate), Glassdoor (free read). Free.

### 15. Web traffic and app downloads — P2 — Effort S
**What:** copart.com vs iaai.com monthly visits and country mix from SimilarWeb free tier and Cloudflare Radar domain rankings; app download estimates from free tiers of AppFigures/Sensor Tower. Registered-member growth proxy.
**Source and cost:** Free tiers. Limited history without a paid plan.

### 16. Positioning and sentiment washout — P5 — Effort S
**What:** FINRA bi-monthly short interest (free), 13F holder changes (SEC, free), analyst rating and PT history, options skew if available via free sources. Show that ratings are at a trough and shorts are elevated, which supports the asymmetry argument.
**Source and cost:** SEC, FINRA, Nasdaq short-interest pages. Free.

### 17. State salvage-title issuance — P4 — Effort M
**What:** Some DMVs publish counts of salvage/rebuilt titles issued (Texas DMV open data, Florida HSMV, others via public-records request). A direct measure of total-loss supply by state, independent of both companies.
**Source and cost:** State open-data portals (free); FOIA-style requests take weeks.

### 18. SEC filing text analytics — P1 — Effort S
**What:** Diff RBA 10-Q/10-K language on "pricing incentives," "volume-based," "service level agreements," and Copart's risk-factor changes quarter to quarter. Also check the ACV merger proxy background section when filed for anything about Copart's strategy and buyback intent.
**Source and cost:** EDGAR full-text search (free).

### 19. ACV deal monitoring — new — Effort S
**What:** ACV publishes quarterly units, GMV, and dealer counts. Track its listing volume and buyer activity on acvauctions.com after the announcement, and Copart's dealer-unit growth. Lower priority for the 3–12 month thesis, but the judges will ask about the deal.

---

## Suggested sequencing if approved
1. Week 1: projects 6 (KPI panel), 5 (fee archaeology), 3 (TLF nowcast), 16 (positioning). These produce charts immediately and feed the model.
2. Week 1–2: start project 1 (tracker) so it accumulates history; start project 9 outreach because calls take time to schedule.
3. Week 2–3: projects 2 (carrier mix), 4 (storm map), 10 (exports), 11 (cost decomposition).
4. Week 3+: projects 7 (matched recoveries) and 8 (satellite) once the tracker has data.

## What you need to set up (all free unless noted)
- API keys: Census International Trade API, FRED, BLS v2, EIA, YouTube Data API, Reddit app credentials, NOAA CDO token (optional; Storm Events is bulk CSV). Each is a web form and instant.
- Accounts: Copernicus Data Space (Sentinel-2) and/or Microsoft Planetary Computer for NAIP; USGS EarthExplorer as fallback.
- Free Basic memberships on copart.com and iaai.com in your own name for sold-price visibility. You create these; the scraper for public pages does not need them.
- Optional paid: Apify Copart/IAA scrapers ($20–50/month) if we do not want to maintain our own; a residential proxy ($15–30/month) only if the sites block us; Regrid parcel API if county records are messy.
- Claude API budget of a few dollars for transcript and review classification.
- Data hygiene rule for the pitch: every chart carries source, collection dates, method, and known gaps. Scraped counts are labeled "listings observed," never "units sold," unless we captured sale events.
