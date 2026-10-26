# AI DataScout — Prompt Documentation

This file is a template for documenting the prompts actually used during development. Keep it honest: replace the status/notes with the real tools, prompts, outputs, and revisions you used. Do not claim a prompt was run if it was not.

## Prompt 1 — Project planning
**Prompt:**  
Act as a Python data engineer and AI product developer. Design an intermediate-level Streamlit project named AI DataScout for analyzing publicly listed Australian GP clinic directory information. Include data ingestion, cleaning, deduplication, data-quality metrics, filtering, charts, CSV export, an optional AI summary, tests, and deployment instructions. Respect website terms, robots.txt, privacy, rate limits, and source attribution. Do not assume scraping is permitted.

**Evaluation / revision:**  
Check that the plan has a working end-to-end demo, not only a mockup. Explicitly separate a fictional sample dataset from real sourced records.

## Prompt 2 — Data pipeline
**Prompt:**  
Write testable Python functions to normalize common clinic CSV column names, standardize text fields, preserve phone numbers as strings, remove duplicate clinics using name/suburb/state, and calculate missing-field metrics. Do not invent missing data. Add tests for aliases, duplicates, blanks, and quality reporting.

**Revision:**  
Add explicit source URL and last-verified fields so data provenance can be reviewed.

## Prompt 3 — Responsible one-page extraction
**Prompt:**  
Create an optional single-page JSON-LD extractor for structured clinic/business entities. Require explicit permission confirmation, validate HTTP(S) URLs, check robots.txt before fetching, use a clear user agent, apply a delay, set timeouts, avoid following links, and fail closed if robots.txt cannot be checked. Explain that robots.txt is not legal permission and source terms still govern use.

**Revision:**  
Stop extraction when permission is not confirmed or robots.txt blocks the request. Do not build a broad crawler or bypass access restrictions.

## Prompt 4 — AI and analytics
**Prompt:**  
Create a hybrid insights module: first calculate transparent local statistics from a pandas dataframe; optionally send a small bounded sample to an LLM API if a key is configured. Instruct the model not to invent facts, assess clinical quality, or provide medical advice. Fall back to local insights if the API is unavailable.

**Revision:**  
Make the app useful without an API key and keep secrets out of source control.

## Prompt 5 — Dashboard
**Prompt:**  
Build a Streamlit dashboard with CSV upload, a clearly labeled fictional sample option, state filters, text search, metrics, a state bar chart, missing-value metrics, AI summary, and cleaned CSV download. Show a disclaimer that the sample data is fictional and real data must be authorized.

**Revision:**  
Ensure an empty filtered dataset does not crash the charts or metrics.

## Prompt 6 — Test and deployment review
**Prompt:**  
Review the project for common failures: missing columns, null values, duplicate rows, malformed URLs, unavailable AI API, blocked robots.txt, missing API keys, and accidental exposure of secrets. Provide local test and deployment instructions.

**Revision:**  
Run `pytest -q`, fix failures, and record actual test output before submitting.
