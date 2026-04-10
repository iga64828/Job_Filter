# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Job Filter is a job scraping and filtering automation tool for Data Engineer roles in Taiwan. The goal is to:
1. Fetch job listings via API/scraping (currently targeting 104, with Yourator kept as an experiment)
2. Extract per-job details: title, address, job description, requirements, salary
3. Use an LLM (Claude or local 8B model) to compare job requirements against a resume, identify skill gaps, and draft cover letters
4. Provide a conversational interface for discussing specific jobs with the LLM

**Tech Stack:** Python, Airflow (scheduling), LLM (Claude API or local model)

## Running the Script

```bash
python scripts/104_list_jobs.py
python scripts/104_fetch_job_raw_json.py
python scripts/104_export_job_details_from_json.py
python scripts/104_fetch_job_details.py
```

The Yourator prototype is kept at `scripts/experiments/yourator_scrape.py`.

## Architecture

Current structure:

- `config/104.yaml` — 104 API query config
- `data/reference/104_area_codes.json` — area code mapping
- `data/raw/104/` — raw job detail payloads
- `data/processed/` — generated CSV outputs
- `scripts/` — runnable ETL entrypoints
- `scripts/experiments/yourator_scrape.py` — isolated prototype scraper

The planned pipeline (not yet implemented) is Airflow-orchestrated ETL → LLM comparison against resume → cover letter generation → chat interface.

## Dependencies

`requests`, `beautifulsoup4`, `pandas`, `pyyaml`
