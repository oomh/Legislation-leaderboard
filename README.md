# Legislation Leaderboard — Kenya Parliament Data Pipeline

> *Who is really doing the legislating in Kenya? And how long does a bill actually take to become law?*
> This project is the data engineering foundation that makes those questions answerable.

---

## Background & Overview

A friend came to me with a simple question: **"Can we figure out which Kenyan MPs and Senators are actually sponsoring the most bills, and how long the whole journey from first reading to presidential assent takes?"**

The data to answer that is publicly available on the [Kenya Parliament website](https://www.parliament.go.ke) — bill trackers, member lists, committee memberships, and house leadership — but it lives across multiple pages and inside PDF documents that require a bit of muscle to extract cleanly.

This repository is **Part 1 of 2**: the full scrape-to-database pipeline. It collects, cleans, and structures the data so that a separate analytics layer (Part 2) can answer the actual questions.

**Specific goals of this phase:**

- Scrape bill trackers for both the Senate and the National Assembly
- Extract structured tables from the PDF committee membership documents using MinerU API
- Normalise sponsor names and split multi-sponsor rows so every bill row has exactly one sponsor
- Parse bill numbers, reading dates, and assent dates into typed fields
- Push four clean, query-ready tables to a hosted Neon PostgreSQL database

---

## Data Structure

All source data comes from the Kenya Parliament website. Here is what gets collected and how it ends up in the database:

| Table | Source | Key columns |
| --- | --- | --- |
| `senate_bills` | Senate bill tracker PDF | `bill_name`, `sponsor`, `bill_house`, `bill_number`, `bill_year`, `dated`, `first_reading`, `assent_date` |
| `assembly_bills` | National Assembly bill tracker PDF | same structure as above |
| `leadership` | House leadership pages (Senate + NA) | `chamber`, `office`, `person` |
| `members` | Member list pages (Senate + NA) | `chamber`, `name`, `county`, `constituency`, `party`, `status` |

The bill tracker PDFs are the most interesting and the most painful. They are published as formatted tables inside PDFs, OCR quality varies, and the same bill can appear with multiple sponsors listed in a single cell (e.g. `"Hon. Mwangi, Hon. Ouko and Chairperson Finance and Appropriation"`). A meaningful chunk of the pipeline is dedicated to untangling that.

---

## Executive Summary

Even before the analytics layer is built, the pipeline design already reveals a few things worth noting:

- **Sponsor attribution is messy by design.** Bills co-sponsored by multiple people, or sponsored by a committee office (e.g. "Chairperson, Finance and Appropriation Committee"), require different splitting logic. Getting this wrong would seriously skew any leaderboard.
- **OCR errors are systematic, not random.** Common patterns like collapsed spaces (`SenateBills`, `NationalAssembly`) and missing punctuation (`No.14of2023`) are handled with regex tolerant patterns rather than hand-fixes, so the pipeline stays robust as new documents are published.
- **The pipeline is designed to be re-run.** Every step saves its results to disk. Re-running any individual step picks up where the last one left off. The Neon push is a full truncate-and-reload, so the database always reflects the latest scrape.

---

## Technical Process

The pipeline runs in 7 sequential steps, each isolated in its own module under `src/pipeline/`:

### Step 1 — Scraping

Hits the parliament website with `requests` + `BeautifulSoup` to collect bill tracker PDF URLs, house leadership positions, member lists (paginated), and the committee membership PDF URL. All results go into the `PipelineStore`.

### Step 2 — MinerU Extraction

Sends the PDF URLs to the [MinerU](https://github.com/opendatalab/MinerU) API, which returns structured JSON representations of the table content. MinerU handles the hard part of reading the PDF table layout; we handle what comes out.

### Step 3 — Table Building

Takes the raw MinerU JSON output and reconstructs clean pandas DataFrames for senate bills, assembly bills, and committee membership. Column headers are normalised to lowercase at this stage.

### Step 4 — Transformations

Applies name parsing and text cleaning to the people tables (leadership, members, committee membership). Bill tracker DataFrames get light cleaning — whitespace, punctuation, encoding artefacts.

### Step 5 — Sponsor Normalisation

The most logic-heavy step. Bills are partitioned into three groups:

- *Office-sponsored* — e.g. "Chairperson, Budget and Appropriations Committee"
- *Multi-sponsored* — two or more named individuals
- *Single-sponsored* — everything else

Each group gets its own splitting strategy. `&` characters are normalised to `and`. The three groups are then reassembled so every row in the output has exactly one sponsor.

### Step 5.5 — Manual Corrections

A lightweight correction layer where known OCR-introduced name variations (e.g. a senator's name spelled two different ways across documents) can be stored as JSON and applied before the merge. Corrections survive pipeline re-runs.

### Step 6 — Merging & Final Cleaning

Merges the per-chamber people tables into single `leadership` and `members` DataFrames. For the bills tables: extracts the bill number from the bill name (it lives inside the last parenthetical, e.g. `The Finance Bill (Senate Bills No. 1 of 2024)`), splits it into `bill_house`, `bill_number`, and `bill_year`, parses all date columns, computes elapsed-days period columns, and replaces all null-ish string representations (`"nan"`, `"NaT"`, `""`, etc.) with proper SQL `NULL`.

### Step 7 — Neon Database Push

Reads DDL from `.sql` files in `src/database/sql/`, ensures each table exists, truncates it, and batch-inserts the Step 6 DataFrames using psycopg v3's `executemany`. The database is now ready for the analytics layer.

---

## Tools & Technologies

| Category | Tool |
| --- | --- |
| Language | Python 3.13 |
| Data manipulation | pandas 2.x (nullable `Int64`, `datetime64`) |
| Web scraping | requests, BeautifulSoup4, lxml |
| PDF extraction | MinerU API |
| Database | Neon (serverless PostgreSQL) |
| DB driver | psycopg v3 |
| App / UI | Streamlit |
| Logging | loguru |
| Testing | pytest |
| Package management | uv |

---

## Preliminary Findings

The data in Neon is already yielding some interesting patterns. Below are four SQL snapshots — two on bill timelines, two on sponsorship concentration.

Some context first before we continue, assent_period is time between first reading and assent. gazette_period is gazette_date and maturity_date. Bills Sponsored by certain Office holders tend to represent ruling party ideas/intents.

- Extremely short assent timelines appear in National Assembly records.
- I think that is a big red flag. A very short assent period does not allow for meaningful public participation.
- Bills passed in 1–2 days — The VAT Amendment Bill (2026) went from first reading to assent in a single day. The Supplementary Appropriations bills follow the same pattern, Come on 😒
- Majority leaders, in both houses, are sponsoring more than 6x more bills than everyone else. Criminal offensive side eye 👀

### National Assembly: Shortest Assent Periods (Top 10)

| serial_number | bill_name | sponsor | maturity_date | first_reading | assent_date | gazette_period_days | assent_period_days |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 291 | The Value Added Tax (Amendment) Bill, 2026 | Leader Of The Majority Party | 2026-04-15 | 2026-04-16 | 2026-04-17 | 5 | 1 |
| 112 | The Supplementary Appropriations(No.3) Bill, 2023 | Chairperson, Budget and Appropriations Committee | 2023-11-20 | 2023-11-21 | 2023-11-23 | 3 | 2 |
| 232 | The Supplementary Appropriation (No.2) Bill, 2025 | Chairperson, Budget And Appropriations Committee | 2025-06-24 | 2025-06-24 | 2025-06-26 | 1 | 2 |
| 64 | The Supplementary Appropriation (No.2) Bill, 2023 | Chairperson, Budget And Appropriations Committee | 2023-06-22 | 2023-06-22 | 2023-06-26 | 1 | 4 |
| 166 | The SupplementaryAppropriation Bill, 2024 | Chairperson, Budget Andappropriations Committee | 2024-06-06 | 2024-06-06 | 2024-06-10 | 1 | 4 |
| 35 | The Supplementary Appropriation Bill, 2023 | Chairperson, Budget And Appropriations Committee | 2023-02-28 | 2023-03-01 | 2023-03-06 | 0 | 5 |
| 58 | The Appropriation Bill, 2023 | Chairperson, Budget And Appropriations Committee | 2023-06-18 | 2023-06-20 | 2023-06-26 | 3 | 6 |
| 175 | The Supplementary Appropriation (No.2) Bill, 2024 | Chairperson, Budget And Appropriations Committee | 2024-07-29 | 2024-07-30 | 2024-08-05 | 4 | 6 |
| 210 | The Supplementary Appropriation Bill, 2025 | Chairperson, Liaison Committee | 2025-03-12 | 2025-03-13 | 2025-03-19 | 5 | 6 |
| 288 | The Supplementary Appropriation Bill, 2026 | Chairperson, Budget And Appropriations Committee | 2026-03-31 | 2026-04-01 | 2026-04-08 | 6 | 7 |

### Senate: Shortest Assent Periods (Top 10)

| serial_number | bill_name | sponsor | maturity_date | first_reading | assent_date | gazette_period_days | assent_period_days |
|---|---|---|---|---|---|---|---|
| 45 | The Climate Change (Amendment) Bill | The Senate Majority Leader | 2023-08-01 | 2023-08-29 | 2023-09-01 | 13 | 3 |
| 56 | The Digital Health Bill | The Senate Majority Leader | 2023-09-13 | 2023-10-03 | 2023-10-19 | 5 | 16 |
| 57 | The Social Health Insurance Bill | The Senate Majority Leader | 2023-09-13 | 2023-10-03 | 2023-10-19 | 2 | 16 |
| 71 | The Affordable Housing Bill | The Senate Majority Leader | 2023-12-06 | 2024-02-22 | 2024-03-19 | 2 | 26 |
| 54 | The Facilities Improvement Financing Bill | The Senate Majority Leader | 2023-09-18 | 2023-09-19 | 2023-10-19 | 3 | 30 |
| 55 | The Primary Health Care Bill | The Senate Majority Leader | 2023-09-18 | 2023-09-19 | 2023-10-19 | 3 | 30 |
| 2 | The County Governments Additional Allocation Bill | Chairperson, Standing Committee On Finance And Budget | 2022-11-08 | 2022-11-08 | 2022-12-12 | 13 | 34 |
| 23 | The Division of Revenue Bill | The Senate Majority Leader | 2023-03-20 | 2023-03-23 | 2023-04-27 | 0 | 35 |
| 6 | The Independent Electoral and Boundaries Commission (Amendment) Bill, | The Senate Majority Leader | 2022-11-15 | 2022-12-08 | 2023-01-23 | 13 | 46 |
| 135 | The County Allocation of Revenue Bill | The Chairperson, Standing Committee On Finance And Budget | 2025-07-07 | 2025-06-27 | 2025-08-13 | 13 | 47 |

### National Assembly: Sponsor Leaderboard (Top 10)

| sponsor | total_bills_sponsored |
|---|---|
| Leader Of The Majority Party | 83 |
| Chairperson, Budget And Appropriations Committee | 12 |
| Chairperson, Standing Committee On Finance And Budget | 9 |
| Didmus Barasa | 7 |
| The Senate Majority Leader | 6 |
| Crystal Asige | 6 |
| Owen Baya | 5 |
| Leader Of The Minority Party | 5 |
| Deputy Speaker | 5 |
| Irene Mayaka | 4 |

### Senate: Sponsor Leaderboard (Top 10)

| sponsor | total_bills_sponsored |
|---|---|
| The Senate Majority Leader | 58 |
| Crystal Asige | 7 |
| The Chairperson, Standing Committee On Finance And Budget | 7 |
| The Senate Minority Leader | 7 |
| Samson Cherarkey | 6 |
| Chairperson, Standing Committee On Finance And Budget | 4 |
| Karen Nyamu | 3 |
| Hamida Kibwana | 3 |
| Eddy Oketch | 3 |
| Danson Mungatana | 3 |

## SQL Used For These Extracts

```sql
    SELECT
      serial_number,
      bill_name,
      sponsor,
      maturity_date,
      first_reading,
      assent_date,
      CAST(gazette_period_days AS BIGINT),
      CAST(assent_period_days AS BIGINT)
    FROM ##relevant table##
    WHERE assent_period_days NOT LIKE '%NaN%'
    ORDER BY assent_period_days
    LIMIT 10;

    SELECT sponsor, COUNT(bill_name) AS total_bills_sponsored
    FROM ##relevant table##
    GROUP BY sponsor
    ORDER BY total_bills_sponsored DESC
    LIMIT 15;

---


## Running the Pipeline

**Prerequisites:** Python 3.13+, a MinerU API key, and a Neon database connection string.

```bash
# Install dependencies
uv sync

# Set environment variables (or add to Streamlit secrets)
export NEON_DATABASE_URL="postgresql://..."
export MINERU_API_KEY="..."

# Launch the Streamlit app
uv run streamlit run app.py
```

Each pipeline step has its own **Run** button in the UI. Steps can be run individually or all at once with **Run Full Pipeline**. Results from each step are cached to disk in `src/pipeline/pipeline_data/` so you can re-run individual steps without re-scraping from scratch.

> **Note:** The current Streamlit interface is a pipeline monitoring tool; a public-facing analytics dashboard is in development as Part 2.

---

## Project Structure

```tex
src/
  pipeline/          # 7-step pipeline (one file per step + orchestrator)
  scrapers/          # requests + BeautifulSoup scrapers
  minerU_extractors/ # MinerU API client and orchestration
  table_builders/    # Raw JSON → pandas DataFrames
  transformations/   # Name parsing, sponsor splitting, text cleaning
  database/          # psycopg connection management + SQL DDL files
app_py/              # Streamlit UI (display only — no pipeline logic)
tests/               # pytest test suite
data/                # MinerU output cache (gitignored)
```
---

## What's Next (Part 2)

With the data in Neon, Part 2 will query it to build:

- A **sponsor leaderboard** — ranked count of bills per MP/Senator, filterable by year, chamber, or party
- A **bill lifecycle analysis** — distribution of days from first reading to assent, broken down by sponsor type, chamber, and bill category
- A public-facing dashboard to make the findings explorable for non-technical readers

### The hard problem: joining bills to members

This is the interesting unsolved piece. The `sponsor` field in the bill trackers and the `name` field in the members table use completely different naming conventions. The bill tracker might say `"Oduya"`, `"Hon. Oduya K."`, or `"Kevin Oduya Otieno"` for the same person. The members table has the full registered name. A straight join is not possible.

The current plan:

1. **Normalise `members` to 1NF** — split the full name into up to 5 individual name-part columns (`name_1` through `name_5`), one token per column, stripping titles and honorifics.
2. **Match token by token** — for each sponsor string, extract its name tokens and score each member against them by counting how many tokens match. The member with the highest token overlap above a confidence threshold wins.
3. **Fuzzy fallback** — for cases where exact token matching doesn't find a confident winner, apply fuzzy string matching (RapidFuzz was trialled but gave inconsistent results on short names; the token-overlap approach is more predictable for this dataset).
4. **Manual override** — any match the algorithm gets wrong can be corrected through the Step 5.5 corrections mechanism already in the pipeline.

This is still a work in progress and will be implemented as a Step 8 before the analytics queries are written.
