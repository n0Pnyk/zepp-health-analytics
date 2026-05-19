"""Zepp Health CLI entry point.

Usage:
    zepp-health report [--date YYYY-MM-DD] [--json]
    zepp-health briefing [--date YYYY-MM-DD]
    zepp-health snapshot [--date YYYY-MM-DD] [--json]
    zepp-health daily [--days N] [--json]
    zepp-health sleep [--days N] [--json]
    zepp-health stress [--days N] [--json]
    zepp-health spo2 [--days N] [--json]
    zepp-health readiness [--days N] [--json]
    zepp-health workouts [--days N] [--json]
    zepp-health hrv [--days N] [--json]
    zepp-health config --show|--path
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta

from zepp_health.analysis import generate_daily_report, generate_snapshot
from zepp_health.client import ZeppClient
from zepp_health.config import AppConfig, load_config
from zepp_health.report import to_json, to_json_compact, to_morning_briefing, to_terminal


def _load_config_from_args(args: argparse.Namespace) -> AppConfig:
    """Load configuration from CLI arguments."""
    return load_config(
        config_path=getattr(args, "config", None),
        cookie=getattr(args, "cookie", None),
        token=getattr(args, "token", None),
        user_id=getattr(args, "user_id", None),
        host=getattr(args, "host", None),
    )


def _emit(data: object, args: argparse.Namespace) -> None:
    """Output data. Compact JSON when --json is specified, otherwise pretty-print."""
    if getattr(args, "json", False):
        if isinstance(data, str):
            print(data)
        else:
            print(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    else:
        if isinstance(data, str):
            print(data)
        else:
            print(json.dumps(data, indent=2, ensure_ascii=False))


def cmd_report(args: argparse.Namespace) -> None:
    """Generate daily health report."""
    config = _load_config_from_args(args)
    target_date = date.fromisoformat(args.date) if args.date else None

    with ZeppClient(config) as client:
        report = generate_daily_report(client, target_date)

    if getattr(args, "json", False):
        output = to_json(report)
    else:
        output = to_terminal(report)

    # Output to file or stdout
    if hasattr(args, "output") and args.output:
        from pathlib import Path
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"Report saved to: {args.output}", file=sys.stderr)
    else:
        print(output)


def cmd_briefing(args: argparse.Namespace) -> None:
    """Generate morning briefing text."""
    config = _load_config_from_args(args)
    target_date = date.fromisoformat(args.date) if args.date else None

    with ZeppClient(config) as client:
        report = generate_daily_report(client, target_date)

    if getattr(args, "json", False):
        print(to_json(report))
    else:
        print(to_morning_briefing(report))


def cmd_daily(args: argparse.Namespace) -> None:
    """View daily raw data."""
    config = _load_config_from_args(args)
    end = date.today()
    start = end - timedelta(days=args.days - 1)

    with ZeppClient(config) as client:
        data = client.get_daily_data(start, end)

    result = []
    for day in data:
        entry: dict = {"date": day.date}
        if day.steps:
            entry["steps"] = day.steps.steps
            entry["distance_meters"] = day.steps.distance_meters
            entry["calories"] = day.steps.calories
        if day.sleep:
            entry["sleep_minutes"] = day.sleep.total_minutes
            entry["deep_sleep"] = day.sleep.deep_sleep_minutes
            entry["light_sleep"] = day.sleep.light_sleep_minutes
            entry["rem_sleep"] = day.sleep.rem_sleep_minutes
        if day.heart_rates:
            entry["heart_rates"] = [
                {"bpm": hr.bpm, "type": hr.activity_type}
                for hr in day.heart_rates
            ]
        result.append(entry)

    _emit(result, args)


def cmd_sleep(args: argparse.Namespace) -> None:
    """View sleep data."""
    config = _load_config_from_args(args)
    end = date.today()
    start = end - timedelta(days=args.days - 1)

    with ZeppClient(config) as client:
        data = client.get_daily_data(start, end)

    result = []
    for day in data:
        if day.sleep:
            s = day.sleep
            result.append({
                "date": day.date,
                "total_minutes": s.total_minutes,
                "deep_sleep": s.deep_sleep_minutes,
                "light_sleep": s.light_sleep_minutes,
                "rem_sleep": s.rem_sleep_minutes,
                "wake_count": s.wake_count,
                "sleep_score": s.sleep_score,
                "resting_hr": s.resting_heart_rate,
            })

    _emit(result, args)


def cmd_stress(args: argparse.Namespace) -> None:
    """View stress data."""
    config = _load_config_from_args(args)
    end = date.today()
    start = end - timedelta(days=args.days - 1)

    with ZeppClient(config) as client:
        data = client.get_stress_data(start, end)

    result = []
    for d in data:
        result.append({
            "date": d.date,
            "avg_stress": d.avg_stress,
            "min_stress": d.min_stress,
            "max_stress": d.max_stress,
            "relax_pct": d.relax_proportion,
            "normal_pct": d.normal_proportion,
            "medium_pct": d.medium_proportion,
            "high_pct": d.high_proportion,
        })

    _emit(result, args)


def cmd_spo2(args: argparse.Namespace) -> None:
    """View SpO2 data."""
    config = _load_config_from_args(args)
    end = date.today()
    start = end - timedelta(days=args.days - 1)

    with ZeppClient(config) as client:
        data = client.get_spo2_data(start, end)

    result = []
    for d in data:
        entry: dict = {"date": d.date}
        if d.readings:
            entry["readings"] = [
                {"spo2": r.spo2, "type": r.reading_type}
                for r in d.readings
            ]
            entry["avg_spo2"] = sum(r.spo2 for r in d.readings) // len(d.readings)
        if d.odi is not None:
            entry["odi"] = d.odi
        if d.osa_events:
            entry["osa_events"] = len(d.osa_events)
        result.append(entry)

    _emit(result, args)


def cmd_readiness(args: argparse.Namespace) -> None:
    """View readiness data."""
    config = _load_config_from_args(args)
    end = date.today()
    start = end - timedelta(days=args.days - 1)

    with ZeppClient(config) as client:
        data = client.get_readiness_data(start, end)

    result = []
    for d in data:
        entry = {
            "date": d.date,
            "readiness_score": d.readiness_score,
            "hrv_score": d.hrv_score,
            "hrv_baseline": d.hrv_baseline,
            "sleep_hrv": d.sleep_hrv,
            "rhr_score": d.rhr_score,
            "rhr_baseline": d.rhr_baseline,
            "sleep_rhr": d.sleep_rhr,
            "skin_temp_score": d.skin_temp_score,
            "skin_temp_delta": round(d.skin_temp_calibrated / 100, 1) if d.skin_temp_calibrated is not None else None,
            "mental_score": d.mental_score,
            "physical_score": d.physical_score,
        }
        result.append(entry)

    _emit(result, args)


def cmd_workouts(args: argparse.Namespace) -> None:
    """View workout records."""
    config = _load_config_from_args(args)
    end = date.today()
    start = end - timedelta(days=args.days - 1)

    with ZeppClient(config) as client:
        data = client.get_workouts(start, end)

    result = []
    for w in data:
        result.append({
            "date": w.start_time.strftime("%Y-%m-%d"),
            "type": w.workout_name,
            "duration_min": w.duration_seconds // 60,
            "distance_m": int(w.distance_meters),
            "calories": int(w.calories),
            "avg_hr": w.avg_heart_rate,
            "max_hr": w.max_heart_rate,
            "vo2_max": w.vo2_max,
            "training_effect": w.training_effect,
        })

    _emit(result, args)


def cmd_hrv(args: argparse.Namespace) -> None:
    """View HRV data."""
    config = _load_config_from_args(args)
    end = datetime.now()
    start = end - timedelta(days=args.days)

    start_ts = int(start.timestamp() * 1000)
    end_ts = int(end.timestamp() * 1000)

    with ZeppClient(config) as client:
        sdnn = client.get_hrv(start_ts, end_ts, hrv_type="sdnn")
        rmssd = client.get_hrv(start_ts, end_ts, hrv_type="rmssd")

    result = {
        "sdnn": [{"ts": r.timestamp.isoformat(), "value": r.hrv_value} for r in sdnn],
        "rmssd": [{"ts": r.timestamp.isoformat(), "value": r.hrv_value} for r in rmssd],
    }

    _emit(result, args)


def cmd_snapshot(args: argparse.Namespace) -> None:
    """Export data snapshot for LLM analysis."""
    config = _load_config_from_args(args)
    target_date = date.fromisoformat(args.date) if args.date else None

    with ZeppClient(config) as client:
        snapshot = generate_snapshot(client, target_date)

    _emit(snapshot, args)


def cmd_config(args: argparse.Namespace) -> None:
    """Show configuration info."""
    config = _load_config_from_args(args)

    if args.path:
        from zepp_health.config import _config_search_paths
        for p in _config_search_paths(getattr(args, "config", None)):
            exists = "✓" if p.is_file() else "✗"
            print(f"  {exists} {p}")
        return

    # Show configuration by default (hide token)
    data = config.model_dump()
    if data.get("app_token"):
        t = data["app_token"]
        data["app_token"] = t[:8] + "..." + t[-8:] if len(t) > 16 else "***"
    print(json.dumps(data, indent=2, ensure_ascii=False))


def main() -> None:
    """CLI main entry point."""
    p = argparse.ArgumentParser(
        prog="zepp-health",
        description="Zepp/Amazfit health data analysis tool",
    )

    # Global options
    p.add_argument("--config", help="Path to configuration file")
    p.add_argument("--cookie", help="Zepp web cookie string")
    p.add_argument("--token", help="App token")
    p.add_argument("--user-id", help="User ID")
    p.add_argument("--host", help="API host override")

    sub = p.add_subparsers(dest="cmd", required=True)

    # report
    sp = sub.add_parser("report", help="Generate daily health report")
    sp.add_argument("--date", help="Date YYYY-MM-DD (default: today)")
    sp.add_argument("--json", action="store_true", help="Output in JSON format")
    sp.add_argument("--output", "-o", help="Output to file")
    sp.set_defaults(func=cmd_report)

    # briefing
    sp = sub.add_parser("briefing", help="Generate morning briefing text")
    sp.add_argument("--date", help="Date YYYY-MM-DD (default: today)")
    sp.add_argument("--json", action="store_true", help="Output in JSON format")
    sp.set_defaults(func=cmd_briefing)

    # daily
    sp = sub.add_parser("daily", help="View daily raw data")
    sp.add_argument("--days", type=int, default=7, help="Number of days (default: 7)")
    sp.add_argument("--json", action="store_true", help="Output in JSON format")
    sp.set_defaults(func=cmd_daily)

    # sleep
    sp = sub.add_parser("sleep", help="View sleep data")
    sp.add_argument("--days", type=int, default=7, help="Number of days (default: 7)")
    sp.add_argument("--json", action="store_true", help="Output in JSON format")
    sp.set_defaults(func=cmd_sleep)

    # stress
    sp = sub.add_parser("stress", help="View stress data")
    sp.add_argument("--days", type=int, default=7, help="Number of days (default: 7)")
    sp.add_argument("--json", action="store_true", help="Output in JSON format")
    sp.set_defaults(func=cmd_stress)

    # spo2
    sp = sub.add_parser("spo2", help="View SpO2 data")
    sp.add_argument("--days", type=int, default=7, help="Number of days (default: 7)")
    sp.add_argument("--json", action="store_true", help="Output in JSON format")
    sp.set_defaults(func=cmd_spo2)

    # readiness
    sp = sub.add_parser("readiness", help="View readiness data")
    sp.add_argument("--days", type=int, default=7, help="Number of days (default: 7)")
    sp.add_argument("--json", action="store_true", help="Output in JSON format")
    sp.set_defaults(func=cmd_readiness)

    # workouts
    sp = sub.add_parser("workouts", help="View workout records")
    sp.add_argument("--days", type=int, default=30, help="Number of days (default: 30)")
    sp.add_argument("--json", action="store_true", help="Output in JSON format")
    sp.set_defaults(func=cmd_workouts)

    # hrv
    sp = sub.add_parser("hrv", help="View HRV data")
    sp.add_argument("--days", type=int, default=7, help="Number of days (default: 7)")
    sp.add_argument("--json", action="store_true", help="Output in JSON format")
    sp.set_defaults(func=cmd_hrv)

    # snapshot
    sp = sub.add_parser("snapshot", help="Export data snapshot for LLM analysis")
    sp.add_argument("--date", help="Date YYYY-MM-DD (default: today)")
    sp.add_argument("--json", action="store_true", help="Output in JSON format")
    sp.set_defaults(func=cmd_snapshot)

    # config
    sp = sub.add_parser("config", help="Show configuration info")
    sp.add_argument("--path", action="store_true", help="Show configuration file search paths")
    sp.set_defaults(func=cmd_config)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
