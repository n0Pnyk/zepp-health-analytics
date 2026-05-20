"""Command-line interface for Amazfit Health API."""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from amazfit_cli.client import AmazfitClient, AmazfitClientError

console = Console()


def parse_date(date_str: str) -> datetime:
    """Parse date string in YYYY-MM-DD format."""
    return datetime.strptime(date_str, "%Y-%m-%d")


def resolve_date_range(args, require_end_date: bool) -> tuple[datetime | None, datetime | None]:
    """Resolve start/end dates using CLI args and defaults."""
    end_date = parse_date(args.end_date) if getattr(args, "end_date", None) else None
    start_date = parse_date(args.start_date) if getattr(args, "start_date", None) else None

    if require_end_date and end_date is None:
        end_date = datetime.now()

    days = getattr(args, "days", None)
    if days is not None and start_date is None:
        if end_date is None:
            end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

    return start_date, end_date


def print_date_range(prefix: str, start_date: datetime | None, end_date: datetime | None):
    """Print a consistent date range message."""
    if start_date and end_date:
        console.print(f"{prefix} [cyan]{start_date.date()}[/cyan] to [cyan]{end_date.date()}[/cyan]")
        return
    if start_date:
        console.print(f"{prefix} [cyan]{start_date.date()}[/cyan]")
        return
    if end_date:
        console.print(f"{prefix} up to [cyan]{end_date.date()}[/cyan]")
        return
    console.print(prefix)


def format_duration(minutes: int) -> str:
    """Format minutes as hours and minutes."""
    hours = minutes // 60
    mins = minutes % 60
    if hours > 0:
        return f"{hours}h {mins}m"
    return f"{mins}m"


def format_skin_temp(calibrated: float | None) -> str:
    """Format skin temp deviation from baseline."""
    if calibrated is None:
        return "-"
    if calibrated == 0:
        return "0°"
    return f"{calibrated / 10:+.1f}°"


def make_table(title: str, columns: list[tuple[str, str | None, str | None]]) -> Table:
    """Create a Rich table from column definitions."""
    table = Table(title=title)
    for name, style, justify in columns:
        table.add_column(name, style=style, justify=justify)
    return table


def require_token(args, *, extra_help: str | None = None):
    """Load env vars and require a token."""
    load_dotenv()
    token = args.token or os.getenv("AMAZFIT_TOKEN")
    user_id = getattr(args, "user_id", None) or os.getenv("AMAZFIT_USER_ID")
    if token and user_id:
        return token, user_id

    missing = []
    if not token:
        missing.append("AMAZFIT_TOKEN/--token")
    if not user_id:
        missing.append("AMAZFIT_USER_ID/--user-id")

    missing_str = ", ".join(missing)
    base_msg = (
        f"[red]Error:[/red] Missing required value(s): {missing_str}. "
        "Set env vars or pass flags. Run 'amazfit token help' for details."
    )

    if extra_help:
        console.print(base_msg + "\n" + extra_help)
    else:
        console.print(base_msg)
    sys.exit(1)


def resolve_time_zone(args) -> str | None:
    """Resolve time zone from CLI or environment variables."""
    time_zone = getattr(args, "time_zone", None)
    return time_zone or os.getenv("AMAZFIT_TIME_ZONE") or os.getenv("AMAZFIT_TIMEZONE")


def output_json(data: list, file_path: str | None = None):
    """Output JSON to stdout or a file."""
    output = [d.model_dump(mode="json") for d in data]
    if file_path:
        Path(file_path).write_text(json.dumps(output, indent=2, default=str))
        console.print(f"[green]Data saved to {file_path}[/green]")
    else:
        print(json.dumps(output, indent=2, default=str))


def cmd_daily(args):
    """Fetch daily health data from Amazfit."""
    token, user_id = require_token(
        args,
        extra_help="Use 'amazfit token help' to learn how to get your token.",
    )
    client_kwargs = {"app_token": token, "user_id": user_id}

    start_date, end_date = resolve_date_range(args, require_end_date=True)
    print_date_range("Fetching data from", start_date, end_date)

    try:
        with AmazfitClient(**client_kwargs) as client:
            console.print("Using provided token...", style="dim")

            if args.output == "summary":
                summaries = client.get_summary(start_date, end_date)
                display_summary_table(summaries)
            elif args.output == "json":
                daily_data = client.get_daily_data(start_date, end_date)
                output_json(daily_data, args.file)
            elif args.output == "raw":
                raw_data = client.get_band_data(start_date, end_date)
                if args.file:
                    Path(args.file).write_text(json.dumps(raw_data, indent=2))
                    console.print(f"[green]Raw data saved to {args.file}[/green]")
                else:
                    print(json.dumps(raw_data, indent=2))
            else:
                daily_data = client.get_daily_data(start_date, end_date)
                display_detailed(daily_data)

    except AmazfitClientError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


def display_summary_table(summaries: list, *, aggregate: bool = False):
    """Display summary data as a table."""
    if not summaries:
        console.print("[yellow]No data found for the specified date range.[/yellow]")
        return

    if aggregate:
        table = make_table(
            "Health Summary (Aggregated)",
            [
                ("Date", "cyan", None),
                ("Steps", None, "right"),
                ("Sleep", None, "right"),
                ("HR", None, "right"),
                ("Stress", None, "right"),
                ("SpO2", None, "right"),
                ("PAI", None, "right"),
            ],
        )
    else:
        table = make_table(
            "Health Summary",
            [
                ("Date", "cyan", None),
                ("Steps", None, "right"),
                ("Distance", None, "right"),
                ("Sleep", None, "right"),
                ("Deep", None, "right"),
                ("Light", None, "right"),
                ("REM", None, "right"),
                ("HR", None, "right"),
            ],
        )

    for day in summaries:
        hr_str = "-"
        if day.resting_heart_rate and day.max_heart_rate:
            hr_str = f"{day.resting_heart_rate}/{day.max_heart_rate}"
        elif day.resting_heart_rate:
            hr_str = f"{day.resting_heart_rate}"
        elif day.max_heart_rate:
            hr_str = f"-/{day.max_heart_rate}"

        if aggregate:
            stress_str = str(day.avg_stress) if day.avg_stress is not None else "-"
            spo2_str = str(day.avg_spo2) if day.avg_spo2 is not None else "-"
            pai_str = f"{day.total_pai:.1f}" if day.total_pai is not None else "-"

            table.add_row(
                day.date,
                f"{day.total_steps:,}",
                format_duration(day.sleep_minutes),
                hr_str,
                stress_str,
                spo2_str,
                pai_str,
            )
        else:
            table.add_row(
                day.date,
                f"{day.total_steps:,}",
                f"{day.total_distance_meters:,}m",
                format_duration(day.sleep_minutes),
                format_duration(day.deep_sleep_minutes),
                format_duration(day.light_sleep_minutes),
                format_duration(day.rem_sleep_minutes),
                hr_str,
            )

    console.print(table)

    if not aggregate:
        # Print totals for the standard summary view only
        total_steps = sum(d.total_steps for d in summaries)
        total_distance = sum(d.total_distance_meters for d in summaries)
        avg_sleep = sum(d.sleep_minutes for d in summaries) / len(summaries) if summaries else 0

        console.print()
        console.print(f"[bold]Total steps:[/bold] {total_steps:,}")
        console.print(f"[bold]Total distance:[/bold] {total_distance / 1000:.1f} km")
        console.print(f"[bold]Average sleep:[/bold] {format_duration(int(avg_sleep))}")


def display_detailed(daily_data: list):
    """Display detailed daily data."""
    if not daily_data:
        console.print("[yellow]No data found for the specified date range.[/yellow]")
        return

    for day in daily_data:
        console.print(f"\n[bold cyan]═══ {day.date} ═══[/bold cyan]")

        # Steps
        if day.steps:
            console.print(f"\n[bold]Steps:[/bold] {day.steps.steps:,}")
            console.print(f"  Distance: {day.steps.distance_meters:,} m")
            console.print(f"  Calories: {day.steps.calories:,}")

        # Sleep
        if day.sleep:
            score_str = f" (score: {day.sleep.sleep_score})" if day.sleep.sleep_score else ""
            console.print(f"\n[bold]Sleep:[/bold] {format_duration(day.sleep.total_minutes)}{score_str}")
            console.print(
                f"  {day.sleep.start_time.strftime('%H:%M')} - {day.sleep.end_time.strftime('%H:%M')}"
            )
            console.print(f"  Deep: {format_duration(day.sleep.deep_sleep_minutes)}")
            console.print(f"  Light: {format_duration(day.sleep.light_sleep_minutes)}")
            console.print(f"  REM: {format_duration(day.sleep.rem_sleep_minutes)}")
            if day.sleep.resting_heart_rate:
                console.print(f"  Resting HR: {day.sleep.resting_heart_rate} bpm")

            if day.sleep.phases:
                console.print("  [dim]Phases:[/dim]")
                for phase in day.sleep.phases:
                    console.print(
                        f"    {phase.start.strftime('%H:%M')}-{phase.end.strftime('%H:%M')}: "
                        f"{phase.phase_type} ({phase.duration_minutes}m)"
                    )

        # Heart rate
        if day.heart_rates:
            console.print(f"\n[bold]Heart Rate:[/bold]")
            for hr in day.heart_rates:
                if hr.activity_type == "resting":
                    console.print(f"  Resting: {hr.bpm} bpm")
                elif hr.activity_type == "max":
                    console.print(f"  Max: {hr.bpm} bpm (at {hr.timestamp.strftime('%H:%M')})")

        # Activities
        if day.activities:
            console.print(f"\n[bold]Activities:[/bold]")
            for act in day.activities:
                if act.mode_name not in ("light_sleep", "deep_sleep", "rem"):
                    console.print(
                        f"  {act.start.strftime('%H:%M')}-{act.end.strftime('%H:%M')}: "
                        f"{act.mode_name} ({act.steps} steps)"
                    )


def cmd_token_help(args):
    """Show instructions for manually obtaining the app token."""
    instructions = """
[bold cyan]How to Get Your Amazfit/Zepp App Token[/bold cyan]

The API may rate-limit automated login attempts. You can extract your token
manually using one of these methods:

[bold]Method 1: Browser Developer Tools (Easiest)[/bold]

1. Open [link=https://user.huami.com/privacy2/index.html]https://user.huami.com/privacy2/index.html[/link]
2. Log in with your Zepp/Amazfit credentials
3. Open Developer Tools (F12 or Cmd+Option+I)
4. Go to the Network tab
5. Click "Export Data" or refresh the page
6. Look for any request to api-mifit.huami.com
7. In the request headers, find "apptoken" - that's your token
8. In the request URL or parameters, find "userid" - that's your user ID

[bold]Method 2: Zepp App (Android with Root)[/bold]

The token is stored at:
  /data/data/com.huami.watch.hmwatchmanager/shared_prefs/hm_id_sdk_android.xml

Look for the "apptoken" value in this file.

[bold]Method 3: Network Proxy (Any Platform)[/bold]

1. Install a proxy like mitmproxy, Charles, or HTTP Toolkit
2. Configure your phone to use the proxy
3. Open the Zepp app and let it sync
4. Find any request with the "apptoken" header

[bold cyan]Using Your Token[/bold cyan]

Once you have your token and user ID, you can use them in two ways:

1. Set it in your .env file:
   [dim]AMAZFIT_TOKEN=your_token_here[/dim]
   [dim]AMAZFIT_USER_ID=your_user_id_here[/dim]

2. Pass them directly to commands:
   [dim]amazfit daily --token YOUR_TOKEN --user-id YOUR_USER_ID[/dim]

[bold yellow]Note:[/bold yellow] Tokens expire after ~90 days. You'll need to extract a new one
when it stops working.
"""
    console.print(Panel(instructions, title="Token Extraction Guide", border_style="blue"))


def cmd_summary(args):
    """Fetch aggregated health summary data from multiple endpoints."""
    token, user_id = require_token(args)
    time_zone = resolve_time_zone(args)

    start_date, end_date = resolve_date_range(args, require_end_date=True)
    print_date_range("Fetching aggregated summary from", start_date, end_date)

    try:
        with AmazfitClient(app_token=token, user_id=user_id, time_zone=time_zone) as client:
            summaries = client.get_aggregate_summary(start_date, end_date, time_zone=time_zone)

        if args.output == "json":
            output_json(summaries, args.file)
        else:
            display_summary_table(summaries, aggregate=True)

    except AmazfitClientError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


def cmd_stress(args):
    """Fetch stress data from Amazfit."""
    token, user_id = require_token(args)

    start_date, end_date = resolve_date_range(args, require_end_date=True)
    print_date_range("Fetching stress data from", start_date, end_date)

    try:
        with AmazfitClient(app_token=token, user_id=user_id) as client:
            stress_data = client.get_stress_data(start_date, end_date)

            if args.output == "json":
                output_json(stress_data)
            else:
                if not stress_data:
                    console.print("[yellow]No stress data found.[/yellow]")
                    return

                table = make_table(
                    "Stress Data",
                    [
                        ("Date", "cyan", None),
                        ("Avg", None, "right"),
                        ("Min", None, "right"),
                        ("Max", None, "right"),
                        ("Relaxed", None, "right"),
                        ("Normal", None, "right"),
                        ("Medium", None, "right"),
                        ("High", None, "right"),
                    ],
                )

                for day in stress_data:
                    table.add_row(
                        day.date,
                        str(day.avg_stress),
                        str(day.min_stress),
                        str(day.max_stress),
                        f"{day.relax_proportion}%",
                        f"{day.normal_proportion}%",
                        f"{day.medium_proportion}%",
                        f"{day.high_proportion}%",
                    )

                console.print(table)

    except AmazfitClientError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


def cmd_spo2(args):
    """Fetch blood oxygen data from Amazfit."""
    token, user_id = require_token(args)
    time_zone = resolve_time_zone(args)

    start_date, end_date = resolve_date_range(args, require_end_date=True)
    print_date_range("Fetching SpO2 data from", start_date, end_date)

    try:
        with AmazfitClient(app_token=token, user_id=user_id, time_zone=time_zone) as client:
            spo2_data = client.get_spo2_data(start_date, end_date, time_zone=time_zone)

            if args.output == "json":
                output_json(spo2_data)
            else:
                if not spo2_data:
                    console.print("[yellow]No SpO2 data found.[/yellow]")
                    return

                table = make_table(
                    "Blood Oxygen (SpO2) Data",
                    [
                        ("Date", "cyan", None),
                        ("ODI", None, "right"),
                        ("Events", None, "right"),
                        ("Score", None, "right"),
                        ("Readings", None, "right"),
                        ("OSA", None, "right"),
                    ],
                )

                for day in spo2_data:
                    odi_str = f"{day.odi:.2f}" if day.odi else "-"
                    score_str = str(day.sleep_score) if day.sleep_score else "-"
                    readings_str = str(len(day.readings)) if day.readings else "-"
                    osa_str = str(len(day.osa_events)) if day.osa_events else "-"

                    table.add_row(
                        day.date,
                        odi_str,
                        str(day.odi_count),
                        score_str,
                        readings_str,
                        osa_str,
                    )

                console.print(table)
                console.print()
                console.print("[dim]ODI = Oxygen Desaturation Index (events per hour during sleep)[/dim]")
                console.print("[dim]OSA = sleep apnea events (from device detection)[/dim]")

    except AmazfitClientError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


def cmd_pai(args):
    """Fetch PAI (Personal Activity Intelligence) data from Amazfit."""
    token, user_id = require_token(args)

    start_date, end_date = resolve_date_range(args, require_end_date=True)
    print_date_range("Fetching PAI data from", start_date, end_date)

    try:
        with AmazfitClient(app_token=token, user_id=user_id) as client:
            pai_data = client.get_pai_data(start_date, end_date)

            if args.output == "json":
                output_json(pai_data)
            else:
                if not pai_data:
                    console.print("[yellow]No PAI data found.[/yellow]")
                    return

                table = make_table(
                    "PAI (Personal Activity Intelligence)",
                    [
                        ("Date", "cyan", None),
                        ("Total", None, "right"),
                        ("Daily", None, "right"),
                        ("Rest HR", None, "right"),
                        ("Low", None, "right"),
                        ("Med", None, "right"),
                        ("High", None, "right"),
                    ],
                )

                for day in pai_data:
                    rhr = str(day.resting_hr) if day.resting_hr else "-"
                    table.add_row(
                        day.date,
                        f"{day.total_pai:.1f}",
                        f"+{day.daily_pai:.1f}",
                        rhr,
                        f"{day.low_zone_minutes}m",
                        f"{day.medium_zone_minutes}m",
                        f"{day.high_zone_minutes}m",
                    )

                console.print(table)
                console.print()
                console.print("[dim]PAI = Personal Activity Intelligence (aim for 100+ weekly)[/dim]")

    except AmazfitClientError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


def cmd_workouts_list(args):
    """Fetch workout history from Amazfit."""
    token, user_id = require_token(args)

    start_date, end_date = resolve_date_range(args, require_end_date=False)
    print_date_range("Fetching workout history...", start_date, end_date)

    try:
        with AmazfitClient(app_token=token, user_id=user_id) as client:
            workouts = client.get_workouts(start_date, end_date)

            if args.output == "json":
                output_json(workouts)
            else:
                if not workouts:
                    console.print("[yellow]No workouts found.[/yellow]")
                    return

                table = make_table(
                    "Workout History",
                    [
                        ("Date", "cyan", None),
                        ("Type", None, None),
                        ("Duration", None, "right"),
                        ("Calories", None, "right"),
                        ("Avg HR", None, "right"),
                        ("Max HR", None, "right"),
                        ("TE", None, "right"),
                    ],
                )

                for w in workouts:
                    duration = format_duration(w.duration_seconds // 60)
                    avg_hr = str(w.avg_heart_rate) if w.avg_heart_rate else "-"
                    max_hr = str(w.max_heart_rate) if w.max_heart_rate else "-"
                    te = f"{w.training_effect:.1f}" if w.training_effect else "-"

                    table.add_row(
                        w.start_time.strftime("%Y-%m-%d %H:%M"),
                        w.workout_name,
                        duration,
                        f"{w.calories:.0f}",
                        avg_hr,
                        max_hr,
                        te,
                    )

                console.print(table)
                console.print()
                console.print(f"[dim]Total workouts: {len(workouts)}[/dim]")

    except AmazfitClientError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


def cmd_readiness(args):
    """Fetch readiness/recovery data including HRV and skin temperature."""
    token, user_id = require_token(args)

    start_date, end_date = resolve_date_range(args, require_end_date=True)
    print_date_range("Fetching readiness data from", start_date, end_date)

    try:
        with AmazfitClient(app_token=token, user_id=user_id) as client:
            readiness_data = client.get_readiness_data(start_date, end_date)

            if args.output == "json":
                output_json(readiness_data)
            else:
                if not readiness_data:
                    console.print("[yellow]No readiness data found.[/yellow]")
                    return

                table = make_table(
                    "Readiness & Recovery Data",
                    [
                        ("Date", "cyan", None),
                        ("Ready", None, "right"),
                        ("HRV", None, "right"),
                        ("Sleep HRV", None, "right"),
                        ("RHR", None, "right"),
                        ("Skin Temp", None, "right"),
                        ("Mental", None, "right"),
                        ("Physical", None, "right"),
                    ],
                )

                for day in readiness_data:
                    readiness = str(day.readiness_score) if day.readiness_score else "-"
                    hrv_score = str(day.hrv_score) if day.hrv_score else "-"
                    sleep_hrv = f"{day.sleep_hrv}ms" if day.sleep_hrv else "-"
                    rhr = f"{day.sleep_rhr}" if day.sleep_rhr else "-"

                    mental = str(day.mental_score) if day.mental_score else "-"
                    physical = str(day.physical_score) if day.physical_score else "-"

                    table.add_row(
                        day.date,
                        readiness,
                        hrv_score,
                        sleep_hrv,
                        rhr,
                        format_skin_temp(day.skin_temp_calibrated),
                        mental,
                        physical,
                    )

                console.print(table)
                console.print()
                console.print("[dim]Ready = Readiness score, HRV = Heart Rate Variability score[/dim]")
                console.print("[dim]Skin Temp = deviation from personal baseline[/dim]")

    except AmazfitClientError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


def main():
    """Main entry point for CLI."""
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument("-t", "--token", help="App token (from manual extraction)")
    common_parser.add_argument("-u", "--user-id", help="User ID (from manual extraction, required)")

    parser = argparse.ArgumentParser(
        description="Amazfit Health API - Access your health data programmatically",
        parents=[common_parser],
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands", required=True)

    daily_parser = subparsers.add_parser(
        "daily", help="Daily health data (steps, sleep, HR)", parents=[common_parser]
    )
    daily_parser.add_argument(
        "-d", "--days", type=int, default=7, help="Number of days to fetch (default: 7)"
    )
    daily_parser.add_argument("--start-date", help="Start date (YYYY-MM-DD)")
    daily_parser.add_argument("--end-date", help="End date (YYYY-MM-DD)")
    daily_parser.add_argument(
        "-o",
        "--output",
        choices=["summary", "detailed", "json", "raw"],
        default="summary",
        help="Output format (default: summary)",
    )
    daily_parser.add_argument("-f", "--file", help="Output file path for json/raw formats")
    daily_parser.set_defaults(func=cmd_daily)

    summary_parser = subparsers.add_parser(
        "summary", help="Aggregated summary (steps, sleep, stress, SpO2, PAI)", parents=[common_parser]
    )
    summary_parser.add_argument(
        "-d", "--days", type=int, default=7, help="Number of days to fetch (default: 7)"
    )
    summary_parser.add_argument("--start-date", help="Start date (YYYY-MM-DD)")
    summary_parser.add_argument("--end-date", help="End date (YYYY-MM-DD)")
    summary_parser.add_argument(
        "--time-zone",
        help="IANA time zone for SpO2 grouping (default: Europe/Berlin)",
    )
    summary_parser.add_argument("-o", "--output", choices=["summary", "json"], default="summary")
    summary_parser.add_argument("-f", "--file", help="Output file path for json format")
    summary_parser.set_defaults(func=cmd_summary)

    stress_parser = subparsers.add_parser("stress", help="Daily stress data", parents=[common_parser])
    stress_parser.add_argument("-d", "--days", type=int, default=7, help="Number of days (default: 7)")
    stress_parser.add_argument("--start-date", help="Start date (YYYY-MM-DD)")
    stress_parser.add_argument("--end-date", help="End date (YYYY-MM-DD)")
    stress_parser.add_argument("-o", "--output", choices=["summary", "json"], default="summary")
    stress_parser.set_defaults(func=cmd_stress)

    spo2_parser = subparsers.add_parser("spo2", help="Blood oxygen (SpO2) data", parents=[common_parser])
    spo2_parser.add_argument("-d", "--days", type=int, default=7, help="Number of days (default: 7)")
    spo2_parser.add_argument("--start-date", help="Start date (YYYY-MM-DD)")
    spo2_parser.add_argument("--end-date", help="End date (YYYY-MM-DD)")
    spo2_parser.add_argument(
        "--time-zone",
        help="IANA time zone for SpO2 grouping (default: Europe/Berlin)",
    )
    spo2_parser.add_argument("-o", "--output", choices=["summary", "json"], default="summary")
    spo2_parser.set_defaults(func=cmd_spo2)

    pai_parser = subparsers.add_parser(
        "pai", help="PAI (Personal Activity Intelligence) data", parents=[common_parser]
    )
    pai_parser.add_argument("-d", "--days", type=int, default=7, help="Number of days (default: 7)")
    pai_parser.add_argument("--start-date", help="Start date (YYYY-MM-DD)")
    pai_parser.add_argument("--end-date", help="End date (YYYY-MM-DD)")
    pai_parser.add_argument("-o", "--output", choices=["summary", "json"], default="summary")
    pai_parser.set_defaults(func=cmd_pai)

    readiness_parser = subparsers.add_parser(
        "readiness", help="Readiness/recovery data (HRV, skin temp)", parents=[common_parser]
    )
    readiness_parser.add_argument("-d", "--days", type=int, default=7, help="Number of days (default: 7)")
    readiness_parser.add_argument("--start-date", help="Start date (YYYY-MM-DD)")
    readiness_parser.add_argument("--end-date", help="End date (YYYY-MM-DD)")
    readiness_parser.add_argument("-o", "--output", choices=["summary", "json"], default="summary")
    readiness_parser.set_defaults(func=cmd_readiness)

    workouts_parser = subparsers.add_parser("workouts", help="Workout history", parents=[common_parser])
    workouts_parser.add_argument("-d", "--days", type=int, help="Limit to last N days")
    workouts_parser.add_argument("--start-date", help="Start date (YYYY-MM-DD)")
    workouts_parser.add_argument("--end-date", help="End date (YYYY-MM-DD)")
    workouts_parser.add_argument("-o", "--output", choices=["summary", "json"], default="summary")
    workouts_parser.set_defaults(func=cmd_workouts_list)

    token_parser = subparsers.add_parser("token", help="Token utilities")
    token_parser.set_defaults(func=cmd_token_help)
    token_subparsers = token_parser.add_subparsers(dest="token_command")

    token_help_parser = token_subparsers.add_parser("help", help="How to get your app token")
    token_help_parser.set_defaults(func=cmd_token_help)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
