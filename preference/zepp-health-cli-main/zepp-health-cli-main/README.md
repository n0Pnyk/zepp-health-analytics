# zepp-health

A tiny, single-file Python wrapper around the **Zepp (Huami) mobile API** so you can read your own health records from the command line: skin temperature, heart rate, HRV, body battery, daily activity, training load, and more.

> **Unofficial.** Not affiliated with or endorsed by Zepp Health. The endpoints used here are reverse-engineered from network traffic of the official Zepp iOS app and may change or break without notice.

## Requirements

- Python 3.9+
- `requests`
- A Zepp account and an **HTTPS proxy capture** of the official Zepp app's network traffic, exported as **HAR** or as a JSON session export (needed to obtain `apptoken` and regional `host`; password-based API login is not supported—see below).

## Install

```bash
git clone <your fork url> zepp-health
cd zepp-health
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Configure

There are two ways to provide credentials. The CLI reads them in this priority order:

1. `--config <path>`
2. `$ZEPP_CONFIG`
3. `./config.json`
4. `~/.config/zepp/config.json`
5. Individual env vars (`ZEPP_APP_TOKEN`, `ZEPP_USER_ID`, `ZEPP_HOST`, …) — these override values from the file.

### Option A — From an HTTPS proxy capture (easiest)

1. Use any HTTPS-decrypting proxy on your computer (mitmproxy, Proxyman, or similar). Install its CA on the phone and trust it so that traffic to `*.zepp.com` can be decrypted.
2. Open the Zepp app, scroll around, open the Health tab so the app makes some API calls.
3. Export the recorded session as **HAR** (universal format, supported by every major proxy) or as your tool's native **JSON session export**. Save it as e.g. `capture.har` (or `.json`) in the project folder.
4. Initialize the config:

   ```bash
   python3 zepp_health.py init capture.har
   ```

   This writes `./config.json` (chmod 600) with `app_token`, `user_id`, and the regional `host` extracted from the capture. Both HAR and JSON-array session exports are auto-detected.

### Option B — Manually create `config.json`

Copy `config.example.json` to `config.json` and fill in the values. The minimum fields are:

```json
{
  "app_token": "MQVBQE…",
  "user_id": "1234567890",
  "host": "api-mifit-us3.zepp.com"
}
```

You can find these in any captured request to `api-mifit*.zepp.com` (the `apptoken` header, the `/users/<id>/…` path segment, and the host).

**Why no email/password login:** Zepp’s current apps use encrypted or otherwise unsupported flows for `/v2/registrations/tokens`, and the older plaintext Huami login path is unreliable, often rate-limited (HTTP 429), and effectively deprecated for this tool. Use a proxy capture and `init` instead.

## Usage

Add **`--json`** to any data subcommand for **compact, single-line JSON** (easy to pipe to `jq`). Without it, JSON responses are **pretty-printed** (indented). `summary` defaults to plain text; use `summary --json` for a structured JSON document.

```bash
# Quick text snapshot
python3 zepp_health.py summary

# Skin temperature (delta from baseline)
python3 zepp_health.py temperature --days 14

# Heart rate samples
python3 zepp_health.py heart-rate --days 7

# Daily training load
python3 zepp_health.py sport-load --days 30

# Weight, VO2 max, workouts
python3 zepp_health.py weight --days 90
python3 zepp_health.py vo2 --days 30
python3 zepp_health.py run-history
python3 zepp_health.py run-history --sport walking   # if your app uses that segment

# Sleep / steps / band payload (large JSON; often base64-encoded blobs)
python3 zepp_health.py band-data --days 14
python3 zepp_health.py band-data --from-date 2026-04-01 --to-date 2026-04-18

# Manual sleep entries, profile, BP from the app
python3 zepp_health.py manual-data --type sleep
python3 zepp_health.py user-info
python3 zepp_health.py blood-pressure --bp-days 7

# User timeline (different from `events` — phone/account stream: stress, PAI, SpO₂ taps)
python3 zepp_health.py user-events --preset all-day-stress --days 7
python3 zepp_health.py user-events --preset pai --days 30
python3 zepp_health.py user-events --preset spo2 --days 1

# SpO₂ ODI/OSA windows (ISO times + timezone)
python3 zepp_health.py user-events-day --preset spo2-odi \
  --start "2026-04-18T00:00:00" --end "2026-04-18T23:59:59" --timezone Asia/Riyadh

# Per-second HR file manifest (points at COS zip blobs)
python3 zepp_health.py second-hr --days 2

# Generic events stream — raw JSON
python3 zepp_health.py events --preset daily-health
python3 zepp_health.py events --preset body-battery
python3 zepp_health.py events --preset hrv
python3 zepp_health.py events --preset hrv-rmssd
python3 zepp_health.py events --preset respiratory
python3 zepp_health.py events --preset stress
python3 zepp_health.py events --preset blood-pressure
python3 zepp_health.py events --preset emotion
python3 zepp_health.py events --preset readiness

# Or any (eventType, subType) pair
python3 zepp_health.py events --type Charge --subtype insight_data --days 7

# Inspect / manage config
python3 zepp_health.py config --show          # token shown masked
python3 zepp_health.py config --path          # which paths are searched
python3 zepp_health.py --config /tmp/other.json temperature
```

`--days N` works either before or after the subcommand (e.g. both `--days 7 heart-rate` and `heart-rate --days 7` are accepted).

Examples:

```bash
python3 zepp_health.py heart-rate --days 7 --json | jq .
python3 zepp_health.py summary --json | jq '.training_load'
python3 zepp_health.py temperature --days 14 --json
```

## Endpoints used

All data requests are **GET**s to your regional `host`, with header `apptoken: <token>`:

| Subcommand | Endpoint |
|---|---|
| `sport-load` | `GET /v2/watch/users/{id}/WatchSportStatistics/SPORT_LOAD` |
| `vo2` | `GET /v2/watch/users/{id}/WatchSportStatistics/VO2_MAX` |
| `heart-rate` | `GET /users/{id}/heartRate` |
| `weight` | `GET /users/{id}/members/-1/weightRecords` |
| `run-history` | `GET /v1/sport/{sport}/history.json` (default `sport=run`) |
| `band-data` | `GET /v1/data/band_data.json` (sleep/steps sync payload; often large) |
| `manual-data` | `GET /v1/user/manualData.json` |
| `user-info` | `GET /huami.health.getUserInfo.json` |
| `blood-pressure` | `GET /users/me/bloodPressure` |
| `user-events` | `GET /users/{id}/events` (stress, PAI, SpO₂ clicks, …) |
| `user-events-day` | `GET /users/{id}/events/dateString` (e.g. SpO₂ ODI/OSA) |
| `second-hr` | `GET /users/me/fileInfo/events` (per-second HR file index) |
| `temperature`, `events` | `GET /v2/users/me/events?eventType=…&subType=…` (watch-centric stream) |

## A word on body temperature

Zepp/Huami expose **`skinTempCalibrated`** as a *delta from your personal baseline*, in **hundredths of a degree Celsius**, not as an absolute body temperature. Values like `+26` mean roughly **+0.26 °C** above baseline. The same payload includes `skinTempScore` (0–100) and `skinTempBaseLine`. This is consistent with how Apple Watch and most wrist sensors report skin temperature.

## Security notes

- Treat `app_token` like a password.
- `config.json` is written with permissions `600` and is gitignored.
- Proxy captures (`*.har`, `*.chlsj`, `*.saz`, `*.flow`, etc.) contain your token, user id, and sometimes your email — they are gitignored.
- If you suspect a token has leaked, log out in the Zepp app to invalidate the session, then capture a fresh session and run `init` again.

## Limitations / known issues

- **Region matters.** Use the host from your own capture (e.g. `api-mifit-us3.zepp.com`, `api-mifit-cn.zepp.com`, …). Calling the wrong regional host returns 403 or empty data.
- **Token expires.** Captured tokens have a TTL of ~30 days; after that, redo `init` with a fresh proxy capture.
- **Not every Zepp screen is covered.** New commands follow paths seen in HTTPS proxy captures. If an endpoint 404s (e.g. `run-history --sport hiking`), capture that screen in your proxy and check the real path segment.
- **No write operations.** This wrapper only reads.

## Contributing

Issues and pull requests are welcome. For **new endpoints**, prefer a short, focused change: capture traffic from the official app (path + query), add a `ZeppClient` method if needed, wire a subcommand or preset, and update this README’s endpoint table. Do not commit secrets, `config.json`, or raw capture files.

### Contributor contract

By submitting a pull request or other contribution to this repository, you agree that your contribution is licensed under the same terms as the project: the [MIT License](LICENSE). No separate contributor agreement is required. (This is sometimes shortened informally as “contribution contract” or “CLA-lite”; it is not a formal signed contract.)

## Disclaimer

Use at your own risk. This project is not endorsed by Zepp Health, Huami, or Xiaomi. Calling private/unsupported endpoints may violate the Zepp Terms of Service in some jurisdictions; review them before running this tool. The authors accept no liability for account suspensions or data loss.

## License

[MIT](LICENSE)
