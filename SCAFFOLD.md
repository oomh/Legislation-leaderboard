# Data Pipeline Scaffold

## Overview

A scalable data pipeline tool that scrapes legislative data from nbaseurl, processes it through the MinerU API, and populates a Neon PostgreSQL database with transformed data.

## Architecture

### High-Level Flow

```
Scrapers → MinerU Extractors → Table Builders → Neon Database
```

## Directory Structure

```
src/
├── scrapers/
│   ├── scrape_bill_trackers.py
│   ├── scrape_member_lists.py
│   ├── scrape_committee_leadership.py
│   ├── scrape_house_leadership.py
│   ├── scrape_helpers.py
│   └── __pycache__/
├── minerU_extractors/
│   ├── api_client.py
│   ├── polling.py
│   └── __pycache__/
└── table_builders/
    ├── bill_trackers_builder.py
    ├── member_lists_builder.py
    ├── committee_leadership_builder.py
    ├── house_leadership_builder.py
    └── __pycache__/
```

## Module Responsibilities

### Scrapers (`src/scrapers/`)

Extracts raw data from nbaseurl website.

- **scrape_bill_trackers.py**: Scrapes bill tracking data for senate bills and for national assembly bills
- **scrape_member_lists.py**: Scrapes legislative member information
- **scrape_committee_leadership.py**: Scrapes committee leadership data
- **scrape_house_leadership.py**: Scrapes house leadership data, finds the <div class="isotope-items view-portfolio" ... element and extracts the a hrefs with the post and the name. for both the senate and the national assembly

- **scrape_helpers.py**: Shared utilities for web scraping (HTTP requests, parsing, etc.)

### MinerU Extractors (`src/minerU_extractors/`)

Manages asynchronous interaction with MinerU API for document processing.

- **api_client.py**: MinerU API client for submitting documents and retrieving results
- **polling.py**: Async polling logic to monitor job status and download results
- **Workflow**:
  1. Submit scraped data to MinerU API
  2. Poll API asynchronously for job completion
  3. Download processed results to temporary files
  4. Clean up temporary files after extraction

### Table Builders (`src/table_builders/`)

Transforms extracted data into structured formats for database insertion.

- **bill_trackers_builder.py**: Transforms bill tracker data for database schema
- **member_lists_builder.py**: Transforms member data for database schema
- **committee_leadership_builder.py**: Transforms committee leadership data for database schema
- **house_leadership_builder.py**: Transforms house leadership data for database schema
- **Responsibilities**:
  - Data validation
  - Schema transformation
  - Data normalization
  - Database-ready output

## Data Flow

1. **Scraping Phase**: Scrapers retrieve raw data from nbaseurl
2. **MinerU Processing Phase**: 
   - Submit raw data to MinerU API
   - Asynchronously poll for completion
   - Download results to temp directory
3. **Transformation Phase**: Table builders process MinerU output and transform to database schema
4. **Database Load**: Insert transformed data into Neon PostgreSQL database
5. **Cleanup Phase**: Remove temporary files

## Technology Stack

- **Web Scraping**: BeautifulSoup, Requests
- **Async Operations**: `asyncio`
- **API Client**: Custom MinerU API wrapper
- **Database**: Neon PostgreSQL
- **Data Processing**: Pandas (optional, for complex transformations)

## Configuration

Database connection strings and API credentials will be managed via:

- Environment variables
- Configuration files (to be defined)

## Next Steps

1. Implement scraper modules with extraction logic
2. Implement MinerU API client and async polling
3. Implement table builders with data transformation logic
4. Create main orchestration script to coordinate pipeline
5. Add error handling and logging throughout
6. Create database initialization scripts
7. Add testing framework
