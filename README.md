# Zepp Health CLI

Fetch health data from Zepp/Amazfit API, normalize it, and compute health scores.

## Features

- Full health data: steps, sleep, heart rate, stress, SpO2, body battery, readiness, HRV, respiratory rate, workouts
- Data normalization aligned with the Zepp app display values
- Independent health scoring algorithm (inspired by Athlytic)
- Multi-dimensional analysis: recovery, sleep quality, training load
- Three output formats: JSON, terminal, natural language briefing

## Installation

```bash
cd zepp-health
pip install -e .
```

## Configuration

Get your cookie from the Zepp web portal (app.zepp.com) via browser developer tools (F12 → Network).

**Option 1: config.json**

```bash
cp config.example.json config.json
# Edit config.json with your app_token and user_id
```

**Option 2: Environment variables**

```bash
cp .env.example .env
# Edit .env
```

**Option 3: CLI arguments**

```bash
zepp-health --cookie "your_cookie_string" report
```

Priority: CLI args > cookie parsing > config.json > environment variables

## CLI Usage

```bash
# Daily health report
zepp-health report [--date YYYY-MM-DD] [--json] [-o file]

# Morning briefing (natural language, good for push notifications)
zepp-health briefing [--date YYYY-MM-DD] [--json]

# LLM analysis snapshot (includes 7-day trends)
zepp-health snapshot [--date YYYY-MM-DD] [--json]

# Raw data
zepp-health daily [--days N] [--json]      # Daily summary
zepp-health sleep [--days N] [--json]      # Sleep
zepp-health stress [--days N] [--json]     # Stress
zepp-health spo2 [--days N] [--json]       # SpO2
zepp-health readiness [--days N] [--json]  # Readiness
zepp-health workouts [--days N] [--json]   # Workouts
zepp-health hrv [--days N] [--json]        # HRV

# Config
zepp-health config         # Show current config
zepp-health config --path  # Show config file search paths
```

## Scoring Algorithm

### Recovery Score

Based on z-score comparison of HRV and resting heart rate (RHR) against a 60-day rolling baseline.

- HRV weight 0.6: above baseline = good recovery
- RHR weight 0.4: below baseline = good recovery
- Fatigue detection: 3 consecutive days of HRV below baseline and RHR above baseline
- Trend analysis: 7-day linear regression slope

### Sleep Quality Score

Multi-dimensional weighted evaluation:

| Dimension | Weight | Target |
|-----------|--------|--------|
| Duration | 0.25 | 7-9 hours |
| Deep sleep % | 0.25 | 15-20% |
| REM % | 0.20 | 20-25% |
| Sleep efficiency | 0.15 | ≥85% |
| Interruption penalty | 0.15 | Wake count + awake duration |

### Exertion Score (Training Load)

Based on acute (7-day) / chronic (28-day) training load ratio:

| Zone | Ratio | Meaning |
|------|-------|---------|
| detraining | <0.8 | Under-training |
| maintaining | 0.8-1.0 | Maintaining |
| productive | 1.0-1.3 | Effective progression |
| overreaching | 1.3-1.5 | High load |
| high_risk | >1.5 | Overtraining risk |

### Overall Health Score

Weighted combination: Recovery 0.35 + Sleep 0.30 + Exertion 0.15 + Stress 0.10 + SpO2 0.10

## Data Validation

| Data Point | vs Zepp App |
|------------|-------------|
| Steps / distance / calories | Exact match |
| Sleep (deep/light/REM/wake count) | Exact match |
| Sleep score | Exact match |
| Resting heart rate | Exact match |
| Stress | Minor rounding difference |
| SpO2 | Avg differs by 1 (calculation method) |
| Body battery | Exact match (+3 offset correction) |
| Readiness | Exact match |
| HRV | Exact match |
| Skin temperature | Exact match (calibrated/100) |
| Continuous HR | API limitation, unavailable |

## Tech Stack

- Python >= 3.10
- httpx — HTTP client
- pydantic v2 — Data models and validation
- rich — Terminal formatting
- python-dotenv — Environment variable management

## Skill Version

For LLM-driven personalized health analysis (for OpenClaw / hermes-agent), see [zepp-health-skill](https://github.com/n0Pnyk/zepp-health-skill).

## Disclaimer

This tool is for informational purposes only and does not constitute medical advice. Consult a healthcare professional for any health concerns.

## License

[MIT License](LICENSE)
