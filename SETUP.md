# Setup — do these in order

> **18 September 2026 release update:** The repository is `stock-pitch-team/copart-altdata`.
> Pages uses **GitHub Actions** via `.github/workflows/pages.yml`, not branch publishing.
> Weekly refresh is deferred; the refresh workflow is manually callable.
> See [PROJECT_REVIEW.md](PROJECT_REVIEW.md) for verified status and current instructions.

> **18 September 2026 release update:** The repository is `stock-pitch-team/copart-altdata`.
> Pages uses **GitHub Actions** via `.github/workflows/pages.yml`, not branch publishing.
> Weekly refresh is deferred; the refresh workflow is manually callable.
> See [PROJECT_REVIEW.md](PROJECT_REVIEW.md) for verified status and current instructions.

> **18 September 2026 release update:** The repository is `stock-pitch-team/copart-altdata`.
> Pages uses **GitHub Actions** via `.github/workflows/pages.yml`, not branch publishing.
> Weekly refresh is deferred; the refresh workflow is manually callable.
> See [PROJECT_REVIEW.md](PROJECT_REVIEW.md) for verified status and current instructions.

Written for someone who has never used an API key. Nothing here assumes prior
knowledge. Every step says exactly what to click and what to paste.

Total time: about 45 minutes, most of it waiting for signup emails. **You can
skip Part 3 entirely and the project still runs** — it just has less history.

---

## Part 0 — What is already done

I already did these, so you do not need to:

- Created a Python virtual environment at `.venv` using Python 3.12.
- Installed the packages the project needs.
- Built four working collectors and the website.
- Created a `.env` file with your email in it for the SEC.

You can verify it all works right now:

```bash
.venv/Scripts/python.exe -m src.site.build_site
```

Then open `docs/index.html` in your browser. If you see the site, you are fine.

---

## Part 1 — Understand the three folders

You only ever need to know about three:

| Folder | What is in it | Do you edit it? |
|---|---|---|
| `data/manual/` | Numbers I typed in by hand from earnings calls and broker notes. Every row has a `source` column. | **Yes** — this is where you and your team add new figures after each earnings call. |
| `data/processed/` | Numbers the code downloaded automatically. Never edit these; they get overwritten. | No |
| `docs/` | The finished website. Generated. Never edit by hand. | No |

The licensed broker PDFs now live in `research/`, which is **excluded from
git** — see Part 6 for why this matters.

---

## Part 2 — Running things

Open a terminal in the project folder. On Windows, the safest way to run Python
here is to use the project's own interpreter explicitly:

```bash
.venv/Scripts/python.exe -m src.collect.sec_financials
```

> **Why the long path?** Your computer has three different Pythons installed and
> `python` points at a different one than `pip` does. Using
> `.venv/Scripts/python.exe` guarantees you get the project's environment with
> the right packages. If you prefer, activate the environment once per terminal
> with `source .venv/Scripts/activate` (Git Bash) or
> `.venv\Scripts\Activate.ps1` (PowerShell), after which plain `python` works.

The four commands that rebuild everything, in order:

```bash
.venv/Scripts/python.exe -m src.collect.sec_financials
.venv/Scripts/python.exe -m src.collect.macro
.venv/Scripts/python.exe -m src.build.tlf_nowcast
.venv/Scripts/python.exe -m src.site.build_site
```

Or just run all of them at once:

```bash
.venv/Scripts/python.exe run_all.py
```

---

## Part 3 — API keys (all free, all optional)

An "API key" is just a long password that identifies you to a data provider so
they can rate-limit you fairly. You paste each one into a file called `.env`.

### First, create your .env file

There is a template called `.env.example`. Copy it:

```bash
cp .env.example .env
```

Now open `.env` in any text editor (Notepad is fine). You will see lines like
`FRED_API_KEY=`. You paste your key immediately after the `=` with no spaces and
no quotes:

```
FRED_API_KEY=abcdef1234567890abcdef1234567890
```

Save the file. **Never commit `.env` to git** — it is already blocked by
`.gitignore`, so this happens automatically.

---

### Key 1 — SEC (already done, no signup)

The SEC needs no key, but it **requires** you to identify yourself with a real
email or it blocks you with an error. I already set this. Verify your `.env`
contains:

```
SEC_USER_AGENT=Copart AltData Research (vetsajayaditya@gmail.com)
```

If you want your teammates to run it, each should put their own email there.

---

### Key 2 — BLS (Bureau of Labor Statistics)

**What it unlocks:** 20 years of repair-cost and used-vehicle price history
instead of 10, and 500 requests a day instead of 25. The project works without
it; you just get less history.

1. Go to <https://data.bls.gov/registrationEngine/>
2. Enter your email address, first name, last name, and organisation
   (put "University of Texas" or similar).
3. Tick the terms box, click **Register**.
4. Check your email. You get a message from BLS with a long code in it, roughly
   32 characters of letters and numbers.
5. Copy that code. In `.env`, set:
   ```
   BLS_API_KEY=<paste the code here>
   ```
6. Test it:
   ```bash
   .venv/Scripts/python.exe -m src.collect.macro
   ```
   Before the key, the log says `no BLS_API_KEY set - using keyless v1`. After,
   that line disappears and you get more rows.

---

### Key 3 — US Census (international trade)

**What it unlocks:** monthly used-vehicle export volumes by destination country
and by port. This is how we verify Copart's claim that Middle East shipments
rerouted to West Africa and Central Europe. Needed for the export-flows project.

1. Go to <https://api.census.gov/data/key_signup.html>
2. Enter organisation name and your email. Click **Submit**.
3. Check your email. There is a link you must click to **activate** the key —
   the key does not work until you click it. The email contains the key itself
   as a long hexadecimal string, about 40 characters.
4. In `.env`, set:
   ```
   CENSUS_API_KEY=<paste the key here>
   ```

> Note: the Census trade API also works without a key for small queries, so you
> can test the export collector before your key arrives.

---

### Key 4 — EIA (diesel prices)

**What it unlocks:** weekly on-highway diesel prices. This is what we use to
separate "Copart's costs rose because fuel got expensive" from "Copart's costs
rose because volumes fell". Needed for the cost-decomposition project. This one
genuinely requires a key — the API returns an error without it.

1. Go to <https://www.eia.gov/opendata/register.php>
2. Enter your name and email, click **Register**.
3. The key arrives by email immediately, a 32-character string.
4. In `.env`, set:
   ```
   EIA_API_KEY=<paste the key here>
   ```

---

### Key 5 — FRED (optional, lowest priority)

**What it unlocks:** a convenient mirror of many series we already get from BLS.
**We do not depend on it** — FRED was unreachable from this machine's network
during testing, so I built everything on BLS instead. Only bother if you want it.

1. Go to <https://fredaccount.stlouisfed.org/apikeys>
2. Create a free account, then click **Request API Key**.
3. Fill in the short form describing your use ("student research project").
4. Copy the 32-character lowercase key into `.env` as `FRED_API_KEY=`.

---

## Part 4 — Accounts that are not API keys

### Copart and IAA member accounts (for the inventory tracker)

The inventory tracker reads **public** search pages, which need no login. But
final sale prices are only visible to logged-in members on some lots. If we want
the matched-recovery study (comparing what Copart gets for a car versus what IAA
gets), you need free Basic accounts.

1. Copart: <https://www.copart.com/register> — choose the **Basic** (free)
   membership, not Premier. You need a name, email and phone.
2. IAA: <https://www.iaai.com/Registration> — choose the free buyer
   registration.

**Important:** create these in your own name. Do not put the passwords anywhere
in this repository. If we get to the point of needing logged-in scraping, we
will handle credentials separately and I will not store them.

### Satellite imagery (only if we do the yard-utilisation project)

Free, but needs an account:

- Copernicus Data Space for Sentinel-2: <https://dataspace.copernicus.eu/>
- Or Microsoft Planetary Computer for higher-resolution NAIP:
  <https://planetarycomputer.microsoft.com/account/request>

Skip these for now. They are a Tier 2 project.

---

## Part 5 — Putting it on GitHub with a website

This gets you a URL your whole team can open, with no software installed.

### Step 1 — Create the repository on GitHub

1. Go to <https://github.com/new>
2. **Repository name:** `copart-altdata`
3. **Description:** "Alt-data research on Copart (CPRT)"
4. Choose **Public**.
   > GitHub Pages on a *private* repo requires a paid plan. Public is what makes
   > the free website work. This is safe because the licensed PDFs are excluded
   > — see Part 6.
5. Do **not** tick "Add a README" — we already have files.
6. Click **Create repository**.

### Step 2 — Push your files

Copy the commands GitHub shows you, or use these. Replace `YOUR-USERNAME`:

```bash
git init
git add .
git commit -m "Copart alt-data research: collectors, models and site"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/copart-altdata.git
git push -u origin main
```

If git asks who you are, run these once first:

```bash
git config --global user.name "Jayaditya Vetsa"
git config --global user.email "vetsajayaditya@gmail.com"
```

**Before you push, run this check.** It confirms no licensed PDF is about to be
uploaded:

```bash
git status --short | grep -iE "\.pdf|research/" || echo "CLEAN - no PDFs staged"
```

You want to see `CLEAN - no PDFs staged`.

### Step 3 — Turn on the website

1. On your repository page, click **Settings** (top right).
2. In the left sidebar, click **Pages**.
3. Under **Source**, choose **Deploy from a branch**.
4. Under **Branch**, choose `main`, and for the folder choose **`/docs`**.
   This matters — the website lives in `docs/`.
5. Click **Save**.
6. Wait two to three minutes. Refresh the page and GitHub shows your URL:

   ```
   https://YOUR-USERNAME.github.io/copart-altdata/
   ```

Send that link to your team. It works on phones. Nobody needs Python.

### Step 3b — Optional: let GitHub refresh the data weekly

There is a workflow at `.github/workflows/refresh.yml` that re-pulls the SEC and
BLS data, re-runs the model and rebuilds the site every Monday. To let it
identify itself to the SEC properly:

1. On your repository, go to **Settings → Secrets and variables → Actions**.
2. Click **New repository secret**.
3. Name: `SEC_USER_AGENT`, value: `Copart AltData Research (your.email@example.com)`.
4. Click **Add secret**. Optionally add `BLS_API_KEY` the same way.

You can also trigger it by hand from the **Actions** tab, which is a good way to
confirm it works.

> The workflow deliberately does **not** run any scraper. GitHub's servers use
> datacenter IP addresses, which both auction sites block, and getting banned
> would cost us the dataset. Scrapers run on your own machine only.

### Step 4 — Updating the site later

Every time you add data or after each earnings call:

```bash
.venv/Scripts/python.exe run_all.py
git add .
git commit -m "Update through FY27 Q1 results"
git push
```

The website updates itself about a minute after the push.

---

## Part 6 — The copyright rule, which matters

The `research/` folder holds Barclays, J.P. Morgan, Freedom Broker and Bloomberg
documents. Every one of them says, in the document itself, that it may not be
reproduced or redistributed. The J.P. Morgan note is stamped as licensed to a
named individual at UT.

**Putting those files in a public GitHub repo would republish them.** That is a
licence breach and a copyright problem, and it is the kind of thing that gets a
team disqualified.

So:

- `research/`, `*.pdf`, `*.xlsx` are all in `.gitignore`. They will not upload.
- Individual **facts and figures** from those reports are fine to use. Facts are
  not copyrightable. We cite them — "per Barclays F3Q26 review, 22 May 2026" —
  and that is both legal and better research practice.
- The website never quotes long passages from them.
- If you are ever unsure, the rule is: a number with attribution is fine, a
  paragraph copied verbatim is not, and the file itself never goes public.

Run the check in Step 2 before every push and you will not have a problem.

---

## Part 7 — Troubleshooting

**"No module named pandas"**
You used the wrong Python. Use `.venv/Scripts/python.exe`, not `python`.

**SEC collector returns 403**
Your `SEC_USER_AGENT` in `.env` is missing or has no email in it. The SEC
requires a real contact address.

**`macro.py` says "REQUEST_NOT_PROCESSED" or returns nothing**
You hit the keyless BLS limit of 25 requests per IP per day. Either wait until
tomorrow or get the free key in Part 3.

**The website shows empty boxes where charts should be**
Your browser could not reach the chart library CDN. The page automatically falls
back to table view; click **Table** on any card. If you are offline this is
expected.

**Charts look wrong after I edited a CSV by hand**
Most likely you put a comma inside a text field without quotes. Run:
```bash
.venv/Scripts/python.exe run_all.py --check
```
It validates every manual CSV and names the bad line.

**GitHub Pages shows a 404**
Check Settings → Pages says branch `main` and folder `/docs`. Also confirm
`docs/index.html` exists and was committed.
