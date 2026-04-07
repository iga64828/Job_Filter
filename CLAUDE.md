# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Job Filter is a job scraping and filtering automation tool for Data Engineer roles in Taiwan. The goal is to:
1. Fetch job listings via API/scraping (currently targeting Yourator)
2. Extract per-job details: title, address, job description, requirements, salary
3. Use an LLM (Claude or local 8B model) to compare job requirements against a resume, identify skill gaps, and draft cover letters
4. Provide a conversational interface for discussing specific jobs with the LLM

**Tech Stack:** Python, Airflow (scheduling), LLM (Claude API or local model)

## Running the Script

```bash
python test.py
```

This hits the Yourator API for keywords `資料工程師`, `數據工程師`, `data engineer`, then scrapes each job detail page. It rate-limits at 1 second per job.

## Architecture

Currently a single-file prototype (`test.py`) with two functions:

- `main()` — queries `https://www.yourator.co/api/v4/jobs?term[]={keyword}` for each keyword, extracts job paths, then calls `scrape_job_detail()` for each
- `scrape_job_detail(url)` — fetches a job page and parses: address (2nd location block), 工作內容, 條件要求, 薪資範圍 via next-sibling heuristic

The planned pipeline (not yet implemented) is Airflow-orchestrated ETL → LLM comparison against resume → cover letter generation → chat interface.

## Dependencies

`requests`, `beautifulsoup4` — install via `pip install requests beautifulsoup4`
