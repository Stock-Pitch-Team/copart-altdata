# Copart (CPRT) — alt-data research

**Version 2 update:** Six executable research workflows, public carrier comparisons, operating sensitivities and validated private imports are now implemented. See [RESEARCH_WORKFLOWS.md](RESEARCH_WORKFLOWS.md) for current status, limitations and commands; it supersedes earlier implementation-status notes below.

Long-thesis research on Copart for the Citadel / Point72 stock-pitch
competition. The output is a website your whole team can read, backed by
collectors that pull from public sources and models whose assumptions are
written down.

**Review and next steps:** [PROJECT_REVIEW.md](PROJECT_REVIEW.md). This is a working research draft, not a completed pitch.

**Team website:** https://stock-pitch-team.github.io/copart-altdata/

**Current research tests:** [RESEARCH_NEXT_STEPS.md](RESEARCH_NEXT_STEPS.md), including the baseline comparison and inventory access findings.

**Start here:**

| File | What it is |
|---|---|
| [`SETUP.md`](SETUP.md) | Step-by-step setup, API keys, and how to publish the website. Written for a non-programmer. |
| [`BUILD_PLAN.md`](BUILD_PLAN.md) | The six approved projects, current status, and what happens next. |
| [`master.md`](master.md) | The thesis and the state of the company, with every fact sourced. |
| [`altdata_ideas.md`](altdata_ideas.md) | The full menu of 19 alt-data project ideas, tiered. |
| `docs/index.html` | The generated website. |

---

## The thesis in five lines

Copart's US insurance volumes fell 7.5% in fiscal Q4 2026, and the market is
pricing a structural share-loss spiral. Management disclosed that **excluding one
lost customer, domestic insurance assignments would have risen 2.3%**. That
customer is reported to be Progressive, which moved most of its salvage volume to
IAA from around January 2026, so the comparison stops hurting in **FY27 Q2**.
Meanwhile RB Global's take rate fell 110 basis points while it won that volume,
and Copart's cost per car rose 12.7% on idle fixed capacity that reverses when
units return.

---

## Quick start

```bash
# refresh everything and rebuild the website
.venv/Scripts/python.exe run_all.py

# just check the hand-entered CSVs are valid
.venv/Scripts/python.exe run_all.py --check

# rebuild the website only, no network
.venv/Scripts/python.exe run_all.py --site
```

Then open `docs/index.html`, or serve it:

```bash
.venv/Scripts/python.exe -m http.server 8765 --directory docs
```

---

## What works today

| Collector / model | Source | Key needed | Status |
|---|---|---|---|
| `src/collect/sec_financials.py` | SEC EDGAR XBRL | No (email in User-Agent) | Working — CPRT, RBA, ACVA, PGR |
| `src/collect/macro.py` | BLS public API | No (key raises limits) | Working — through August 2026 |
| `src/collect/noaa_storms.py` | NOAA Storm Events | No | Working — 184k events, 3,730 county/forecast-zone labels |
| `src/build/tlf_nowcast.py` | Derived | No | Working — R² 0.66, n=28 |
| `src/site/build_site.py` | Local CSVs | No | Working — 19 charts, 6 pages |

Verified against the filings: fiscal Q3 2026 operating income of $464.3mn and
revenue of $1,237.1mn both match exactly.

---

## Repository layout

```
├── SETUP.md            setup, keys, publishing — read this first
├── BUILD_PLAN.md       approved projects and status
├── master.md           the thesis and company state
├── altdata_ideas.md    all 19 project ideas
├── run_all.py          one command to refresh everything
├── src/
│   ├── common.py       shared HTTP, caching, and dataset provenance
│   ├── collect/        one module per data source
│   ├── build/          models that turn collected data into findings
│   └── site/           the website generator, templates and chart specs
├── data/
│   ├── manual/         hand-typed figures, every row individually cited
│   ├── processed/      collector output, plus a .meta.json per dataset
│   └── raw/            cached payloads (not committed)
├── docs/               the generated website (GitHub Pages serves this)
└── research/           licensed broker PDFs — NEVER COMMITTED
```

Every dataset in `data/processed/` has a `.meta.json` sidecar recording its
source, method, known gaps and collection time. The website reads those and
prints them under each chart, so no figure appears without provenance.

---

## Two things to know before you touch anything

**1. Licensed research stays out of git.** `research/` holds Barclays, J.P.
Morgan, Freedom Broker and Bloomberg documents. Each states it may not be
reproduced or redistributed, and the J.P. Morgan note is licensed to a named
individual. They are excluded by `.gitignore`. Figures from them are cited with
attribution, which is fine; the files themselves never go public. Before any
push:

```bash
git status --short | grep -iE "\.pdf|research/" || echo "CLEAN"
```

**2. Copart's website blocks automated requests.** `copart.com` sits behind
Imperva bot protection and returns a JavaScript challenge instead of content, so
the planned inventory tracker cannot use plain HTTP requests against it.
`iaai.com` does serve normal HTML. This is unresolved and is discussed in
`BUILD_PLAN.md`. Do not run any scraper from GitHub Actions — datacenter IPs get
blocked, and an IP ban costs us the dataset.

---

## Standards

1. No invented numbers. Filing, transcript, public dataset, or our own
   calculation from those.
2. Derived values are labelled derived.
3. Scraped counts are "listings observed", never "units sold".
4. Models state sample size, R² and confidence intervals.
5. Every chart has a table twin, so nothing is hover-only.
6. Disconfirming evidence gets equal billing — the bear-case data is the first
   chart on the competition page.

---

*Student research for a pitch competition. Not investment advice. The authors
hold no position and are not licensed advisers.*
