# Amazfit CLI

**⚠️ DISCLAIMER: This tool is for educational and personal use only. It is not officially supported by Huami/Zepp and may violate their Terms of Service. Use at your own risk.**

Python CLI + client for accessing Amazfit/Zepp health data from the Huami cloud APIs.

## Features

- Daily health data (steps, sleep, heart rate, activities)
- Stress, SpO2, PAI, and readiness metrics
- Workout history with detailed stats
- JSON export for automation

## Installation

```bash
uv pip install git+https://github.com/Baitinq/amazfit-cli.git
```

## Authentication

You need an `apptoken` and `userid`. Here is the quickest manual extraction method:

1. Open the Zepp web portal and log in:

```text
https://user.huami.com/privacy2/index.html
```

2. Open Developer Tools → Network tab.
3. Refresh the page (or click any page action).
4. Find a request to `api-mifit.huami.com` or `api-mifit.zepp.com`.
5. In request headers, copy `apptoken`.
6. In the request URL or query params, copy `userid`.

Create a `.env` file:

```bash
AMAZFIT_TOKEN=your_app_token_here
AMAZFIT_USER_ID=your_user_id_here
```

Or pass them directly:

```bash
amazfit daily --token YOUR_TOKEN --user-id YOUR_USER_ID
```

## CLI

Available commands (examples below):
- `amazfit daily`
- `amazfit summary`
- `amazfit stress`
- `amazfit spo2`
- `amazfit pai`
- `amazfit readiness`
- `amazfit workouts`

### `amazfit daily`

```bash
amazfit daily -d 7
```

```text
Date       | Steps  | Distance | Sleep  | Deep  | Light | REM  | HR
2025-01-24 | 8,412  | 6,412m   | 6h 48m | 1h 12m| 4h 50m| 46m  | 55/132
2025-01-25 | 10,021 | 7,981m   | 7h 10m | 1h 03m| 5h 18m| 49m  | 54/140
```

### `amazfit summary`

```bash
amazfit summary -d 7
```

```text
Date       | Steps  | Sleep  | HR     | Stress | SpO2 | PAI
2025-01-24 | 8,412  | 6h 48m | 55/132 | 29     | 97   | 102.4
2025-01-25 | 10,021 | 7h 10m | 54/140 | 24     | 98   | 108.0
```

### `amazfit stress`

```bash
amazfit stress -d 7
```

```text
Date       | Avg | Min | Max | Relaxed | Normal | Medium | High
2025-01-24 | 29  | 10  | 68  | 58%     | 26%    | 12%    | 4%
2025-01-25 | 24  | 9   | 61  | 62%     | 24%    | 11%    | 3%
```

### `amazfit spo2`

```bash
amazfit spo2 -d 7
```

```text
Date       | ODI  | Events | Score | Readings | OSA
2025-01-24 | 3.10 | 7      | 86    | 4        | 1
2025-01-25 | 2.40 | 5      | 90    | 2        | 0
```

### `amazfit pai`

```bash
amazfit pai -d 7
```

```text
Date       | Total | Daily | Rest HR | Low | Med | High
2025-01-24 | 102.4 | +12.3 | 55      | 38m | 22m | 6m
2025-01-25 | 108.0 | +10.1 | 54      | 41m | 19m | 4m
```

### `amazfit readiness`

```bash
amazfit readiness -d 7
```

```text
Date       | Ready | HRV | Sleep HRV | RHR | Skin Temp | Mental | Physical
2025-01-24 | 78    | 62  | 52ms      | 55  | +0.2     | 74     | 81
2025-01-25 | 82    | 66  | 56ms      | 54  | +0.1     | 77     | 83
```

### `amazfit workouts`

```bash
amazfit workouts -d 30
```

```text
Date             | Type            | Duration | Calories | Avg HR | Max HR | TE
2025-01-25 07:12 | outdoor_running | 38m      | 420      | 138    | 165    | 3.2
2025-01-26 18:03 | cycling         | 52m      | 510      | 132    | 158    | 2.8
```

## Python API

```python
from datetime import datetime, timedelta
from amazfit_cli import AmazfitClient

with AmazfitClient(app_token="YOUR_TOKEN", user_id="YOUR_USER_ID") as client:
    start = datetime.now() - timedelta(days=7)
    end = datetime.now()
    summaries = client.get_summary(start, end)
    workouts = client.get_workouts(start, end)
```

## Notes

- Data comes from Zepp cloud servers, not directly from the device.
- You must sync your device with the Zepp app for data to appear.
- Tokens expire periodically; extract a new one when needed.

## License

MIT
