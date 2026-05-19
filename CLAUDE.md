# Zepp Health Data Analysis Project

Fetch health data from the Zepp/Amazfit API, normalize it, and compute health scores.

## Tech Stack

- Python >= 3.10
- httpx — HTTP client
- pydantic v2 — Data models and validation
- rich — Terminal formatting
- python-dotenv — Environment variable management

## Directory Structure

- `zepp_health/` — Main package
  - `config.py` — Configuration loading + cookie parsing
  - `client.py` — API client
  - `models.py` — Pydantic data models
  - `scoring.py` — Health scoring algorithm
  - `analysis.py` — Analysis pipeline
  - `report.py` — Output formatting
  - `cli.py` — CLI entry point

## Naming Conventions

- Functions: snake_case
- Classes: PascalCase
- Constants: UPPER_SNAKE_CASE

## API Authentication

Parse apptoken/userid from cookie string. China region default host: api-mifit-cn3.zepp.com

## Scoring Algorithm

Inspired by Athlytic app. Recovery score based on HRV/RHR z-score comparison against 60-day rolling baseline.
