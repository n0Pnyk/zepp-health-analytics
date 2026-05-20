#!/usr/bin/env python3
"""Minimal Zepp (Huami) API wrapper.

Reverse-engineered from HTTPS proxy captures of the official Zepp mobile app.
Not affiliated with Zepp Health. See README.md for setup and caveats.

Credentials are read from (highest priority first):
  1. --config <path>
  2. $ZEPP_CONFIG
  3. ./config.json
  4. ~/.config/zepp/config.json
  5. Individual env vars: ZEPP_APP_TOKEN, ZEPP_USER_ID, ZEPP_HOST, ...
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests

DEFAULT_HOST = "api-mifit-us3.zepp.com"

# Resolved at parse time from --config or $ZEPP_CONFIG; falls back to search list below.
_CONFIG_PATH_OVERRIDE: str | None = None

CONFIG_KEYS = (
    "app_token",
    "user_id",
    "host",
    "app_platform",
    "lang",
    "country",
    "timezone",
    "app_version",
    "user_agent",
    "cv",
    "vb",
)
ENV_BY_KEY = {
    "app_token": "ZEPP_APP_TOKEN",
    "user_id": "ZEPP_USER_ID",
    "host": "ZEPP_HOST",
    "app_platform": "ZEPP_APP_PLATFORM",
    "lang": "ZEPP_LANG",
    "country": "ZEPP_COUNTRY",
    "timezone": "ZEPP_TIMEZONE",
    "app_version": "ZEPP_APP_VERSION",
    "user_agent": "ZEPP_USER_AGENT",
    "cv": "ZEPP_CV",
    "vb": "ZEPP_VB",
}


def _config_search_paths() -> list[Path]:
    paths: list[Path] = []
    if _CONFIG_PATH_OVERRIDE:
        paths.append(Path(_CONFIG_PATH_OVERRIDE).expanduser())
    env_path = os.environ.get("ZEPP_CONFIG", "").strip()
    if env_path:
        paths.append(Path(env_path).expanduser())
    paths.append(Path.cwd() / "config.json")
    paths.append(Path.home() / ".config" / "zepp" / "config.json")
    seen: set[Path] = set()
    out: list[Path] = []
    for p in paths:
        rp = p.resolve() if p.exists() else p
        if rp not in seen:
            seen.add(rp)
            out.append(p)
    return out


def load_config() -> dict[str, Any]:
    """Load config from JSON, with env vars overriding individual keys."""
    cfg: dict[str, Any] = {}
    for p in _config_search_paths():
        if p.is_file():
            try:
                cfg = json.loads(p.read_text())
                cfg["_loaded_from"] = str(p)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"Invalid JSON in {p}: {exc}")
            break
    for key, env in ENV_BY_KEY.items():
        v = os.environ.get(env, "").strip()
        if v:
            cfg[key] = v
    return cfg


def save_config(data: dict[str, Any], path: Path | None = None) -> Path:
    target = path or (Path.cwd() / "config.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    clean = {k: v for k, v in data.items() if k in CONFIG_KEYS and v}
    target.write_text(json.dumps(clean, indent=2) + "\n")
    try:
        os.chmod(target, 0o600)
    except OSError:
        pass
    return target


def _r() -> str:
    return str(uuid.uuid4()).upper()


def _today_utc() -> date:
    return datetime.now(timezone.utc).date()


class ZeppClient:
    def __init__(
        self,
        apptoken: str,
        user_id: str,
        host: str = DEFAULT_HOST,
        app_platform: str = "ios_phone",
        timeout: float = 30.0,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        self.apptoken = apptoken
        self.user_id = user_id
        self.base = f"https://{host}"
        self.session = requests.Session()
        self.timeout = timeout
        self.session.headers.update(self._headers(app_platform, extra_headers or {}))

    def _headers(
        self, app_platform: str, extra: dict[str, str]
    ) -> dict[str, str]:
        defaults = {
            "apptoken": self.apptoken,
            "appname": "com.huami.midong",
            "appplatform": app_platform,
            "accept": "*/*",
            "accept-encoding": "gzip, deflate, br",
            "v": "2.0",
            "vn": "10.2.5",
            "cv": "1722_10.2.5",
            "vb": "202604132257",
            "user-agent": "Zepp/10.2.5 (iPhone; iOS 26.3.1; Scale/3.00)",
            "lang": "en",
            "country": "",
            "timezone": "UTC",
        }
        defaults.update({k: v for k, v in extra.items() if v})
        return defaults

    def get_json(self, path: str, params: dict[str, Any]) -> Any:
        q = {"r": _r(), **params}
        url = f"{self.base}{path}"
        r = self.session.get(url, params=q, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def sport_load(self, start_day: date, end_day: date) -> Any:
        return self.get_json(
            f"/v2/watch/users/{self.user_id}/WatchSportStatistics/SPORT_LOAD",
            {
                "startDay": start_day.isoformat(),
                "endDay": end_day.isoformat(),
                "limit": 900,
                "isReverse": "true",
            },
        )

    def vo2_max(self, start_day: date, end_day: date) -> Any:
        return self.get_json(
            f"/v2/watch/users/{self.user_id}/WatchSportStatistics/VO2_MAX",
            {
                "startDay": start_day.isoformat(),
                "endDay": end_day.isoformat(),
                "limit": 900,
                "isReverse": "true",
            },
        )

    def heart_rate(
        self,
        start_ts: int,
        end_ts: int,
        *,
        limit: int = 1000,
        hr_type: int = 2,
    ) -> Any:
        return self.get_json(
            f"/users/{self.user_id}/heartRate",
            {
                "startTime": start_ts,
                "endTime": end_ts,
                "limit": limit,
                "type": hr_type,
            },
        )

    def weight_records(self, from_ts: int, to_ts: int, *, limit: int = 300) -> Any:
        return self.get_json(
            f"/users/{self.user_id}/members/-1/weightRecords",
            {
                "fromTime": from_ts,
                "toTime": to_ts,
                "limit": limit,
                "isForward": 0,
            },
        )

    def sport_history(
        self,
        sport: str,
        start_track_id: int,
        stop_track_id: int,
        *,
        need_sub_data: int = 1,
    ) -> Any:
        """Workout history. `sport` is the URL segment (e.g. run, walking, ride, swimming)."""
        return self.get_json(
            f"/v1/sport/{sport}/history.json",
            {
                "userid": self.user_id,
                "startTrackId": start_track_id,
                "stopTrackId": stop_track_id,
                "need_sub_data": need_sub_data,
                "type": "",
            },
        )

    def run_history(
        self,
        start_track_id: int,
        stop_track_id: int,
        *,
        need_sub_data: int = 1,
    ) -> Any:
        return self.sport_history(
            "run", start_track_id, stop_track_id, need_sub_data=need_sub_data
        )

    def band_data(
        self,
        from_date: date,
        to_date: date,
        *,
        query_type: str = "detail",
        byte_length: int = 8,
        device_type: int = 0,
    ) -> Any:
        """Raw band sync bucket (sleep segments, steps, etc.) — `query_type` detail|summary."""
        return self.get_json(
            "/v1/data/band_data.json",
            {
                "userid": self.user_id,
                "from_date": from_date.isoformat(),
                "to_date": to_date.isoformat(),
                "query_type": query_type,
                "byteLength": byte_length,
                "device_type": device_type,
            },
        )

    def manual_data(self, manual_type: str) -> Any:
        """Manual entries (e.g. sleep sessions logged in app)."""
        return self.get_json(
            "/v1/user/manualData.json",
            {"userid": self.user_id, "type": manual_type},
        )

    def get_user_info(self) -> Any:
        return self.get_json(
            "/huami.health.getUserInfo.json",
            {"userid": self.user_id},
        )

    def blood_pressure_me(
        self,
        *,
        days: int = 7,
        to_date: date | None = None,
        source: str = "com.huami.midong.associated,com.huami.midong",
    ) -> Any:
        td = to_date or _today_utc()
        return self.get_json(
            "/users/me/bloodPressure",
            {
                "days": days,
                "sourceArrayStr": source,
                "toDate": td.isoformat(),
            },
        )

    def events_user(
        self,
        event_type: str,
        from_ms: int,
        to_ms: int,
        *,
        sub_type: str | None = None,
        limit: int = 2000,
        reverse: bool = False,
    ) -> Any:
        """User-scoped timeline (`/users/{id}/events`) — stress, PAI, SpO₂ clicks, etc."""
        params: dict[str, Any] = {
            "eventType": event_type,
            "from": from_ms,
            "to": to_ms,
            "limit": limit,
            "reverse": 1 if reverse else 0,
            "userId": self.user_id,
        }
        if sub_type:
            params["subType"] = sub_type
        return self.get_json(f"/users/{self.user_id}/events", params)

    def events_user_date_string(
        self,
        event_type: str,
        sub_type: str,
        from_iso: str,
        to_iso: str,
        *,
        tz: str,
        limit: int = 999,
        reverse: bool = False,
    ) -> Any:
        """Same as events_user but with ISO date bounds (used for SpO₂ ODI/OSA, etc.)."""
        return self.get_json(
            f"/users/{self.user_id}/events/dateString",
            {
                "eventType": event_type,
                "subType": sub_type,
                "from": from_iso,
                "to": to_iso,
                "timeZone": tz,
                "limit": limit,
                "reverse": 1 if reverse else 0,
                "userId": self.user_id,
            },
        )

    def file_info_events(
        self,
        event_type: str,
        sub_type: str,
        from_ms: int,
        to_ms: int,
        *,
        limit: int = 200,
    ) -> Any:
        """Per-second HR file index (`/users/me/fileInfo/events`)."""
        return self.get_json(
            "/users/me/fileInfo/events",
            {
                "eventType": event_type,
                "subType": sub_type,
                "from": from_ms,
                "to": to_ms,
                "limit": limit,
            },
        )

    def events(
        self,
        event_type: str,
        sub_type: str,
        from_ms: int,
        to_ms: int,
        *,
        limit: int = 200,
        reverse: bool = True,
    ) -> Any:
        """Generic /v2/users/me/events query (millisecond epochs)."""
        return self.get_json(
            "/v2/users/me/events",
            {
                "eventType": event_type,
                "subType": sub_type,
                "from": from_ms,
                "to": to_ms,
                "limit": limit,
                "reverse": 1 if reverse else 0,
            },
        )


def _load_client() -> ZeppClient:
    cfg = load_config()
    token = (cfg.get("app_token") or "").strip()
    uid = str(cfg.get("user_id") or "").strip()
    if not token or not uid:
        searched = "\n  ".join(str(p) for p in _config_search_paths())
        print(
            "Missing app_token or user_id.\n\n"
            "Set them by either:\n"
            "  1. Run:  python3 zepp_health.py init <proxy-capture>\n"
            "     (accepts an HTTPS proxy export: HAR, or the JSON session\n"
            "      format used by common HTTPS proxy/inspection tools)\n"
            "  2. Or create config.json (paths searched, in order):\n"
            f"     {searched}\n"
            '     {{ "app_token": "...", "user_id": "...", "host": "api-mifit-us3.zepp.com" }}\n'
            "  3. Or export env vars: ZEPP_APP_TOKEN, ZEPP_USER_ID, ZEPP_HOST",
            file=sys.stderr,
        )
        sys.exit(1)
    host = (cfg.get("host") or DEFAULT_HOST).strip()
    platform = (cfg.get("app_platform") or "ios_phone").strip()
    extra = {
        "lang": cfg.get("lang") or "",
        "country": cfg.get("country") or "",
        "timezone": cfg.get("timezone") or "",
        "vn": cfg.get("app_version") or "",
        "user-agent": cfg.get("user_agent") or "",
        "cv": cfg.get("cv") or "",
        "vb": cfg.get("vb") or "",
    }
    return ZeppClient(token, uid, host=host, app_platform=platform, extra_headers=extra)


_USER_ID_RE = __import__("re").compile(r"/users/(\d+)/")


def _normalize_entries(raw: Any) -> list[dict[str, Any]]:
    """Normalize a proxy capture into a list of {host, path, headers}.

    Supports two common JSON exports:
      - HAR (HTTP Archive):  {"log": {"entries": [{"request": {...}}, ...]}}
      - Generic proxy JSON session:  [ {"host": "...", "path": "...",
          "request": {"header": {"headers": [{"name": .., "value": ..}]}}}, ... ]
    """
    out: list[dict[str, Any]] = []
    if isinstance(raw, dict) and isinstance(raw.get("log"), dict):
        for e in raw["log"].get("entries") or []:
            req = e.get("request") or {}
            url = req.get("url") or ""
            try:
                parsed = urllib.parse.urlparse(url)
                host = parsed.hostname or ""
                path = parsed.path or ""
            except ValueError:
                host, path = "", ""
            headers = [
                {"name": h.get("name", ""), "value": h.get("value", "")}
                for h in (req.get("headers") or [])
            ]
            out.append({"host": host, "path": path, "headers": headers})
        return out
    if isinstance(raw, list):
        for e in raw:
            headers = (
                e.get("request", {}).get("header", {}).get("headers") or []
            )
            out.append(
                {
                    "host": e.get("host") or "",
                    "path": e.get("path") or "",
                    "headers": headers,
                }
            )
        return out
    raise SystemExit(
        "Unrecognized capture format. Expected HAR ({log:{entries:[...]}}) or "
        "a JSON array of session entries."
    )


def _extract_from_capture(path: Path) -> dict[str, Any]:
    """Pull app_token, user_id, and regional host from a proxy capture file."""
    raw = json.loads(path.read_text())
    entries = _normalize_entries(raw)

    token: str | None = None
    uid: str | None = None
    for e in entries:
        for h in e["headers"]:
            if (h.get("name") or "").lower() == "apptoken":
                token = token or h.get("value")
        m = _USER_ID_RE.search(e["path"])
        if m and not uid:
            uid = m.group(1)
        if token and uid:
            break

    with_token_hosts: list[str] = []
    for e in entries:
        host = e["host"]
        if not host or "zepp.com" not in host:
            continue
        if any((h.get("name") or "").lower() == "apptoken" for h in e["headers"]):
            with_token_hosts.append(host)
    seen: set[str] = set()
    ordered = [h for h in with_token_hosts if not (h in seen or seen.add(h))]
    host = next((h for h in ordered if "api-mifit" in h), None) or (
        ordered[0] if ordered else None
    )
    if not host:
        host = next(
            (e["host"] for e in entries if "zepp.com" in (e["host"] or "")),
            None,
        )

    if not (token and uid):
        raise SystemExit(
            f"Could not find apptoken / user id in {path}. "
            "Make sure the capture includes authenticated requests to api-mifit*.zepp.com."
        )
    return {"app_token": token, "user_id": uid, "host": host or DEFAULT_HOST}


def cmd_init(args: argparse.Namespace) -> None:
    src = Path(args.capture).expanduser()
    if not src.is_file():
        sys.exit(f"Capture file not found: {src}")
    extracted = _extract_from_capture(src)
    target = Path(args.output).expanduser() if args.output else (Path.cwd() / "config.json")
    if target.exists() and not args.force:
        existing = {}
        try:
            existing = json.loads(target.read_text())
        except json.JSONDecodeError:
            pass
        existing.update(extracted)
        merged = existing
    else:
        merged = extracted
    saved = save_config(merged, target)
    print(f"Wrote {saved} (mode 600)")
    print(f"  user_id: {merged.get('user_id')}")
    print(f"  host:    {merged.get('host')}")
    masked = (merged.get("app_token") or "")[:6] + "…" + (merged.get("app_token") or "")[-6:]
    print(f"  token:   {masked}  ({len(merged.get('app_token') or '')} chars)")


def cmd_config(args: argparse.Namespace) -> None:
    cfg = load_config()
    if args.show:
        out = dict(cfg)
        if out.get("app_token"):
            t = out["app_token"]
            out["app_token"] = t[:6] + "…" + t[-6:]
        print(json.dumps(out, indent=2))
        return
    if args.path:
        for p in _config_search_paths():
            print(p, "(exists)" if p.is_file() else "")
        return
    sys.exit("Use --show or --path")


def cmd_sport_load(args: argparse.Namespace) -> None:
    c = _load_client()
    end = _today_utc()
    start = end - timedelta(days=args.days - 1)
    data = c.sport_load(start, end)
    _emit_json(data, args)


def cmd_vo2(args: argparse.Namespace) -> None:
    c = _load_client()
    end = _today_utc()
    start = end - timedelta(days=args.days - 1)
    data = c.vo2_max(start, end)
    _emit_json(data, args)


def cmd_heart_rate(args: argparse.Namespace) -> None:
    c = _load_client()
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=args.days)
    data = c.heart_rate(int(start.timestamp()), int(end.timestamp()))
    _emit_json(data, args)


def cmd_weight(args: argparse.Namespace) -> None:
    c = _load_client()
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=args.days)
    data = c.weight_records(int(start.timestamp()), int(end.timestamp()))
    _emit_json(data, args)


def cmd_run_history(args: argparse.Namespace) -> None:
    c = _load_client()
    # Window around "today" in UTC — adjust if you track by local midnight.
    day = _today_utc()
    start_of_day = int(
        datetime(day.year, day.month, day.day, tzinfo=timezone.utc).timestamp()
    )
    sport = getattr(args, "sport", "run") or "run"
    data = c.sport_history(sport, start_of_day, start_of_day)
    _emit_json(data, args)


def cmd_band_data(args: argparse.Namespace) -> None:
    c = _load_client()
    if args.from_date and args.to_date:
        start = date.fromisoformat(args.from_date)
        end = date.fromisoformat(args.to_date)
    else:
        end = _today_utc()
        start = end - timedelta(days=args.days - 1)
    data = c.band_data(start, end, query_type=args.query_type)
    _emit_json(data, args)


def cmd_manual_data(args: argparse.Namespace) -> None:
    c = _load_client()
    data = c.manual_data(args.type)
    _emit_json(data, args)


def cmd_user_info(args: argparse.Namespace) -> None:
    c = _load_client()
    data = c.get_user_info()
    _emit_json(data, args)


def cmd_blood_pressure(args: argparse.Namespace) -> None:
    c = _load_client()
    to_d = date.fromisoformat(args.to_date) if args.to_date else None
    data = c.blood_pressure_me(days=args.bp_days, to_date=to_d)
    _emit_json(data, args)


# /users/{id}/events — different from /v2/users/me/events (watch-centric stream).
USER_EVENT_PRESETS: dict[str, tuple[str, str | None]] = {
    "all-day-stress": ("all_day_stress", None),
    "pai": ("PaiHealthInfo", None),
    "spo2": ("blood_oxygen", "click"),
    "single-stress": ("single_stress", None),
    # subType seen in proxy captures for this stream:
    "health-data": ("health_data", "blood_pressure"),
}

# /users/{id}/events/dateString — ISO window + timezone.
USER_EVENT_DAY_PRESETS: dict[str, tuple[str, str]] = {
    "spo2-odi": ("blood_oxygen", "odi"),
    "spo2-osa": ("blood_oxygen", "osa_event"),
}


def cmd_user_events(args: argparse.Namespace) -> None:
    c = _load_client()
    from_ms, to_ms = _ms_window(args.days)
    et = args.type
    st: str | None = args.subtype
    if args.preset:
        et, pst = USER_EVENT_PRESETS[args.preset]
        st = pst
    if not et:
        sys.exit("Provide --preset or --type (and --subtype if required).")
    data = c.events_user(
        et, from_ms, to_ms, sub_type=st, limit=args.limit, reverse=args.reverse
    )
    _emit_json(data, args)


def cmd_user_events_day(args: argparse.Namespace) -> None:
    c = _load_client()
    et = args.type
    st = args.subtype
    if args.preset:
        et, st = USER_EVENT_DAY_PRESETS[args.preset]
    if not et or not st:
        sys.exit("Provide --preset or both --type and --subtype.")
    tz = args.timezone or load_config().get("timezone") or "UTC"
    data = c.events_user_date_string(
        et,
        st,
        args.start,
        args.end,
        tz=tz,
        limit=args.limit,
        reverse=args.reverse,
    )
    _emit_json(data, args)


def cmd_second_hr(args: argparse.Namespace) -> None:
    c = _load_client()
    from_ms, to_ms = _ms_window(args.days)
    data = c.file_info_events(
        "second_heart_rate",
        "real_data",
        from_ms,
        to_ms,
        limit=args.limit,
    )
    _emit_json(data, args)


_EVENT_PRESETS: dict[str, tuple[str, str]] = {
    "temperature": ("readiness", "watch_score"),
    "readiness": ("readiness", "watch_score"),
    "daily-health": ("DailyHealth", "summary"),
    "body-battery": ("Charge", "real_data"),
    "stress": ("Charge", "stress_data"),
    "hrv": ("hrv_sdnn", "real_data"),
    "hrv-rmssd": ("HRVRMSSD", "real_data"),
    "respiratory": ("RespiratoryRate", "real_data"),
    "blood-pressure": ("blood_pressure", "real_data"),
    "emotion": ("Emotion", "real_data"),
    "lactate-threshold": ("LactateThreshold", "summary"),
}


def _ms_window(days: int) -> tuple[int, int]:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    return int(start.timestamp() * 1000), int(end.timestamp() * 1000)


def _emit_json(data: Any, args: argparse.Namespace) -> None:
    """Print JSON; --json uses compact one-line output (good for jq / scripts)."""
    if getattr(args, "json", False):
        print(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    else:
        print(json.dumps(data, indent=2, ensure_ascii=False))


def cmd_events(args: argparse.Namespace) -> None:
    c = _load_client()
    from_ms, to_ms = _ms_window(args.days)
    data = c.events(args.type, args.subtype, from_ms, to_ms, limit=args.limit)
    _emit_json(data, args)


def cmd_temperature(args: argparse.Namespace) -> None:
    c = _load_client()
    et, st = _EVENT_PRESETS["temperature"]
    from_ms, to_ms = _ms_window(args.days)
    data = c.events(et, st, from_ms, to_ms, limit=args.limit)
    if args.raw or getattr(args, "json", False):
        _emit_json(data, args)
        return
    items = data.get("items") or []
    if not items:
        print(f"No skin-temperature samples in the last {args.days} day(s).")
        return
    print("Skin temperature (calibrated delta from baseline, hundredths of \u00b0C):\n")
    print(f"  {'date (UTC)':<19}  {'delta':>7}  {'score':>5}  {'baseline':>8}  device")
    for it in items:
        ts = it.get("timestamp", 0) / 1000
        v = it.get("value") or {}
        cal = v.get("skinTempCalibrated")
        score = v.get("skinTempScore")
        base = v.get("skinTempBaseLine")
        dev = v.get("deviceId", "?")
        when = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        cal_disp = "—" if cal in (None, 255) else f"{cal/100:+.2f}\u00b0C"
        score_disp = "—" if score in (None, 255) else str(score)
        base_disp = "—" if base in (None, -10, 255) else str(base)
        print(f"  {when:<19}  {cal_disp:>7}  {score_disp:>5}  {base_disp:>8}  {dev}")
    print(
        "\nNote: Zepp/Huami report skin temperature as a calibrated delta from your "
        "personal baseline, not absolute body temperature."
    )


def cmd_summary(args: argparse.Namespace) -> None:
    """Short human-readable snapshot: training load + empty checks for HR/weight."""
    c = _load_client()
    end = _today_utc()
    start = end - timedelta(days=args.days - 1)
    load = c.sport_load(start, end)
    items = load.get("items") or []
    hr = c.heart_rate(
        int((datetime.now(timezone.utc) - timedelta(days=7)).timestamp()),
        int(datetime.now(timezone.utc).timestamp()),
    )
    w = c.weight_records(
        int((datetime.now(timezone.utc) - timedelta(days=30)).timestamp()),
        int(datetime.now(timezone.utc).timestamp()),
    )
    if getattr(args, "json", False):
        payload = {
            "training_load": load,
            "training_load_range_days": args.days,
            "heart_rate_last_7_days": hr,
            "weight_last_30_days": w,
        }
        _emit_json(payload, args)
        return
    print(f"Training load ({len(items)} days in range)\n")
    for row in items:
        day = row.get("dayId", "?")
        wtl = row.get("wtlSum")
        train = row.get("currnetDayTrainLoad")
        print(f"  {day}  load={wtl}  day_train_load={train}")
    print()
    print(f"Heart rate samples (last 7d): {len((hr.get('items') or []))} items")
    print(f"Weight records (last 30d): {len((w.get('items') or []))} items")


def main() -> None:
    p = argparse.ArgumentParser(description="Zepp health API helper")
    p.add_argument(
        "--days",
        type=int,
        default=None,
        help="Default days of history (overridable per subcommand)",
    )
    p.add_argument(
        "--config",
        help="Path to config.json (default: ./config.json or ~/.config/zepp/config.json)",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    def _add_days(parser: argparse.ArgumentParser) -> None:
        # SUPPRESS keeps the parent's --days when the user only sets it globally.
        parser.add_argument(
            "--days",
            type=int,
            default=argparse.SUPPRESS,
            help="Days of history (default 14)",
        )

    def _add_json(parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--json",
            action="store_true",
            help="Output compact JSON on one line (easy to pipe to jq)",
        )

    sp = sub.add_parser("sport-load", help="Daily training load (WatchSportStatistics)")
    _add_days(sp)
    _add_json(sp)
    sp.set_defaults(func=cmd_sport_load)

    sp = sub.add_parser("vo2", help="VO2 max series (may be empty)")
    _add_days(sp)
    _add_json(sp)
    sp.set_defaults(func=cmd_vo2)

    sp = sub.add_parser("heart-rate", help="Heart rate samples")
    _add_days(sp)
    _add_json(sp)
    sp.set_defaults(func=cmd_heart_rate)

    sp = sub.add_parser("weight", help="Weight records")
    _add_days(sp)
    _add_json(sp)
    sp.set_defaults(func=cmd_weight)

    sp = sub.add_parser(
        "band-data",
        help="Sleep/steps raw band sync (/v1/data/band_data.json)",
    )
    _add_days(sp)
    _add_json(sp)
    sp.add_argument(
        "--query-type",
        dest="query_type",
        choices=("detail", "summary"),
        default="detail",
        help="detail = per-day data; summary = yearly chunks (can be huge)",
    )
    sp.add_argument(
        "--from-date",
        help="Start date YYYY-MM-DD (use with --to-date instead of --days)",
    )
    sp.add_argument("--to-date", help="End date YYYY-MM-DD")
    sp.set_defaults(func=cmd_band_data)

    sp = sub.add_parser("manual-data", help="Manual entries (/v1/user/manualData.json)")
    _add_json(sp)
    sp.add_argument(
        "--type",
        default="sleep",
        help="Record type (default sleep)",
    )
    sp.set_defaults(func=cmd_manual_data)

    sp = sub.add_parser("user-info", help="Profile blob (huami.health.getUserInfo.json)")
    _add_json(sp)
    sp.set_defaults(func=cmd_user_info)

    sp = sub.add_parser("blood-pressure", help="Blood pressure (/users/me/bloodPressure)")
    _add_json(sp)
    sp.add_argument(
        "--bp-days",
        type=int,
        default=7,
        dest="bp_days",
        metavar="N",
        help="Days to include (default 7)",
    )
    sp.add_argument(
        "--to-date",
        help="Anchor date YYYY-MM-DD (default today UTC)",
    )
    sp.set_defaults(func=cmd_blood_pressure)

    sp = sub.add_parser(
        "user-events",
        help="User timeline (/users/{id}/events): stress, PAI, SpO₂, …",
    )
    _add_days(sp)
    _add_json(sp)
    sp.add_argument("--type", help="eventType (if no --preset)")
    sp.add_argument("--subtype", help="subType (optional)")
    sp.add_argument(
        "--preset",
        choices=sorted(USER_EVENT_PRESETS.keys()),
        help="Shortcut for common eventType/subType pairs",
    )
    sp.add_argument("--limit", type=int, default=2000)
    sp.add_argument(
        "--reverse",
        action="store_true",
        help="reverse=1 (newest first)",
    )
    sp.set_defaults(func=cmd_user_events)

    sp = sub.add_parser(
        "user-events-day",
        help="User events with ISO window (/users/{id}/events/dateString), e.g. SpO₂ ODI",
    )
    _add_json(sp)
    sp.add_argument("--start", required=True, help="from ISO datetime, e.g. 2026-04-18T00:00:00")
    sp.add_argument("--end", required=True, help="to ISO datetime")
    sp.add_argument(
        "--timezone",
        help="IANA zone (default: config timezone or UTC)",
    )
    sp.add_argument("--type", help="eventType (if no --preset)")
    sp.add_argument("--subtype", help="subType (if no --preset)")
    sp.add_argument(
        "--preset",
        choices=sorted(USER_EVENT_DAY_PRESETS.keys()),
        help="spo2-odi or spo2-osa",
    )
    sp.add_argument("--limit", type=int, default=999)
    sp.add_argument("--reverse", action="store_true")
    sp.set_defaults(func=cmd_user_events_day)

    sp = sub.add_parser(
        "second-hr",
        help="Per-second HR file index (/users/me/fileInfo/events)",
    )
    _add_days(sp)
    _add_json(sp)
    sp.add_argument("--limit", type=int, default=200)
    sp.set_defaults(func=cmd_second_hr)

    sp = sub.add_parser(
        "run-history",
        help="Workout history for UTC midnight window (/v1/sport/{sport}/history.json)",
    )
    _add_json(sp)
    sp.add_argument(
        "--sport",
        default="run",
        help="URL segment: run, walking, ride, swimming, … (default run)",
    )
    sp.set_defaults(func=cmd_run_history)

    sp = sub.add_parser("summary", help="Brief text summary")
    _add_days(sp)
    _add_json(sp)
    sp.set_defaults(func=cmd_summary)

    sp = sub.add_parser(
        "temperature",
        help="Skin temperature (delta from baseline) from readiness/watch_score",
    )
    _add_days(sp)
    _add_json(sp)
    sp.add_argument("--limit", type=int, default=200)
    sp.add_argument(
        "--raw",
        action="store_true",
        help="Same as --json: raw API response JSON (alias for backwards compatibility)",
    )
    sp.set_defaults(func=cmd_temperature)

    sp = sub.add_parser(
        "events",
        help="Generic /v2/users/me/events (use --type and --subtype, or --preset)",
    )
    _add_days(sp)
    _add_json(sp)
    sp.add_argument("--type", help="eventType (e.g. readiness, Charge, hrv_sdnn)")
    sp.add_argument("--subtype", help="subType (e.g. watch_score, real_data)")
    sp.add_argument(
        "--preset",
        choices=sorted(_EVENT_PRESETS.keys()),
        help="convenience shortcut that fills --type/--subtype",
    )
    sp.add_argument("--limit", type=int, default=200)

    def _events_dispatch(a: argparse.Namespace) -> None:
        if a.preset:
            a.type, a.subtype = _EVENT_PRESETS[a.preset]
        if not a.type or not a.subtype:
            sys.exit("Provide --preset, or both --type and --subtype.")
        cmd_events(a)

    sp.set_defaults(func=_events_dispatch)

    init_p = sub.add_parser(
        "init",
        help="Extract apptoken/user_id/host from a proxy capture (HAR or JSON) into config.json",
    )
    init_p.add_argument("capture", help="Path to a proxy capture (HAR or JSON session export)")
    init_p.add_argument("-o", "--output", help="Where to write config.json (default ./config.json)")
    init_p.add_argument("-f", "--force", action="store_true", help="Overwrite without merging")
    init_p.set_defaults(func=cmd_init)

    cfg_p = sub.add_parser("config", help="Show current config (token masked) or search paths")
    cfg_p.add_argument("--show", action="store_true", help="print resolved config (default)")
    cfg_p.add_argument("--path", action="store_true", help="print config search paths")
    cfg_p.set_defaults(func=cmd_config)

    args = p.parse_args()
    global _CONFIG_PATH_OVERRIDE
    _CONFIG_PATH_OVERRIDE = args.config
    if getattr(args, "days", None) is None:
        args.days = 14
    if args.cmd == "config" and not (args.show or args.path):
        args.show = True
    args.func(args)


if __name__ == "__main__":
    main()
