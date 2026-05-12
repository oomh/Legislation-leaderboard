# Legislation Leaderboard — Kenya Parliament Data Pipeline

> *Who is really doing the legislating in Kenya? And how long does a bill actually take to become law?*
> 
> This project is the data engineering foundation that makes those questions answerable.

---

## Background & Overview

A friend came to me with a deceptively simple question: **"Can we figure out which Kenyan MPs and Senators are actually sponsoring the most bills, and how long the whole journey from first reading to presidential assent takes?"**

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
|---|---|---|
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

#### Step 1 — Scraping

Hits the parliament website with `requests` + `BeautifulSoup` to collect bill tracker PDF URLs, house leadership positions, member lists (paginated), and the committee membership PDF URL. All results go into the `PipelineStore`.

#### Step 2 — MinerU Extraction

Sends the PDF URLs to the [MinerU](https://github.com/opendatalab/MinerU) API, which returns structured JSON representations of the table content. MinerU handles the hard part of reading the PDF table layout; we handle what comes out.

#### Step 3 — Table Building

Takes the raw MinerU JSON output and reconstructs clean pandas DataFrames for senate bills, assembly bills, and committee membership. Column headers are normalised to lowercase at this stage.

#### Step 4 — Transformations

Applies name parsing and text cleaning to the people tables (leadership, members, committee membership). Bill tracker DataFrames get light cleaning — whitespace, punctuation, encoding artefacts.

#### Step 5 — Sponsor Normalisation

The most logic-heavy step. Bills are partitioned into three groups:

- *Office-sponsored* — e.g. "Chairperson, Budget and Appropriations Committee"
- *Multi-sponsored* — two or more named individuals
- *Single-sponsored* — everything else

Each group gets its own splitting strategy. `&` characters are normalised to `and`. The three groups are then reassembled so every row in the output has exactly one sponsor.

#### Step 5.5 — Manual Corrections

A lightweight correction layer where known OCR-introduced name variations (e.g. a senator's name spelled two different ways across documents) can be stored as JSON and applied before the merge. Corrections survive pipeline re-runs.

#### Step 6 — Merging & Final Cleaning

Merges the per-chamber people tables into single `leadership` and `members` DataFrames. For the bills tables: extracts the bill number from the bill name (it lives inside the last parenthetical, e.g. `The Finance Bill (Senate Bills No. 1 of 2024)`), splits it into `bill_house`, `bill_number`, and `bill_year`, parses all date columns, computes elapsed-days period columns, and replaces all null-ish string representations (`"nan"`, `"NaT"`, `""`, etc.) with proper SQL `NULL`.

#### Step 7 — Neon Database Push

Reads DDL from `.sql` files in `src/database/sql/`, ensures each table exists, truncates it, and batch-inserts the Step 6 DataFrames using psycopg v3's `executemany`. The database is now ready for the analytics layer.

---

## Tools & Technologies

| Category | Tool |
|---|---|
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

## Results & Visualizations

This phase produces four tables in the Neon database. Below is a representative preview of what the final bill tables look like once the pipeline has run.

**`senate_bills` (sample columns)**

| serial_number | bill_name | sponsor | bill_house | bill_number | bill_year | first_reading | assent_date | assent_period |
|---|---|---|---|---|---|---|---|---|
| 1 | The Statute Law (Misc. Amendments) Bill | Sen. Cheruiyot | Sen. Bill | 1 | 2024 | 2024-02-06 | null | null |
| 2 | The Affordable Housing (Amendment) Bill | Chairperson Housing and Urban Planning | Sen. Bill | 2 | 2024 | 2024-02-13 | 2024-11-20 | 281 days |

**`assembly_bills` (sample columns)**

| serial_number | bill_name | sponsor | bill_house | bill_number | bill_year | first_reading | assent_date | assent_period |
|---|---|---|---|---|---|---|---|---|
| 1 | The Finance Bill | National Treasury (CS) | NA Bill | 3 | 2023 | 2023-05-04 | 2023-10-26 | 175 days |

The `assent_period` column directly feeds the "how long does a bill take?" question. The `sponsor` column, once the analytics layer groups and counts it, answers the leaderboard question.

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

> **Note:** The Streamlit app is a personal development tool — it gives me visibility into each step's output while I'm building and debugging the pipeline. It isn't intended for public use at this stage. Once Part 2 (the analytics layer) is complete, a proper public-facing dashboard will replace it.

---

## Project Structure

```
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
