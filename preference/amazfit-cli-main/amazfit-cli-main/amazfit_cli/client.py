"""Amazfit/Huami API client for health data retrieval."""

import base64
import json
from datetime import datetime, timedelta
from typing import Optional

import httpx

from amazfit_cli.models import (
    ActivityData,
    ActivitySummary,
    Credentials,
    DaySummary,
    HeartRateData,
    HeartRateZone,
    OSAEvent,
    PAIData,
    ReadinessData,
    SleepData,
    SleepPhase,
    SpO2Data,
    SpO2Reading,
    StepData,
    StrengthTrainingGroup,
    StressData,
    StressReading,
    Workout,
    WORKOUT_TYPES,
)

# API endpoints
BAND_DATA_URL = "https://api-mifit.huami.com/v1/data/band_data.json"
EVENTS_URL = "https://api-mifit.zepp.com/users/{user_id}/events"
WORKOUT_HISTORY_URL = "https://api-mifit.huami.com/v1/sport/run/history.json"
DEFAULT_TIME_ZONE = "Europe/Berlin"



# Activity mode codes
ACTIVITY_MODES = {
    1: "slow_walking",
    3: "fast_walking",
    4: "light_sleep",
    5: "deep_sleep",
    6: "running",
    7: "normal_activity",
    9: "cycling",
    11: "rem_sleep",  # REM sleep on newer devices
    80: "outdoor_running",
    81: "walking",
    82: "hiking",
    83: "treadmill",
    84: "cycling",
    85: "stationary_bike",
}


class AmazfitClientError(Exception):
    """Base exception for Amazfit client errors."""

    pass


class AmazfitClient:
    """Client for accessing Amazfit/Zepp health data via Huami API."""

    def __init__(
        self,
        credentials: Optional[Credentials] = None,
        app_token: Optional[str] = None,
        user_id: Optional[str] = None,
        time_zone: Optional[str] = None,
    ):
        """
        Initialize the client.

        Args:
            credentials: Pre-existing credentials (skips authentication)
            app_token: App token (from manual extraction)
            user_id: User ID (from manual extraction, required)
        """
        self.credentials = credentials
        self._http = httpx.Client(timeout=30.0, follow_redirects=False)
        self.time_zone = time_zone

        # If app_token provided, create minimal credentials
        if app_token and not credentials:
            self.credentials = Credentials(
                user_id=user_id or "",
                app_token=app_token,
                login_token="",
            )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        """Close the HTTP client."""
        self._http.close()

    def _ensure_authenticated(self):
        """Ensure we have valid credentials."""
        if not self.credentials:
            raise AmazfitClientError("App token required. Provide app_token or credentials.")

        if not self.credentials.user_id:
            raise AmazfitClientError("User ID required. Provide user_id explicitly.")

    def _get_headers(self) -> dict:
        """Get headers for API requests."""
        return {
            "apptoken": self.credentials.app_token,
            "appname": "com.xiaomi.hm.health",  # Required for Mi Fit/Zepp data
            "lang": "en",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
            "Accept": "application/json",
        }

    @staticmethod
    def _normalize_timestamp(ts: int | float) -> float:
        """Normalize timestamps that may be in milliseconds to seconds."""
        if ts and ts > 1000000000000:
            return ts / 1000
        return float(ts)

    @staticmethod
    def _date_str_from_ts(ts: int | float) -> str:
        """Convert a timestamp (s or ms) into YYYY-MM-DD."""
        return datetime.fromtimestamp(AmazfitClient._normalize_timestamp(ts)).strftime("%Y-%m-%d")

    @staticmethod
    def _safe_json_loads(raw: str, default):
        """Safely parse JSON with a fallback."""
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return default

    @staticmethod
    def _float_list(values) -> list[float]:
        """Convert a list of values into floats, or return empty on failure."""
        if not isinstance(values, list):
            return []
        try:
            return [float(v) for v in values]
        except (ValueError, TypeError):
            return []

    @staticmethod
    def _date_range_to_ms(start_date: datetime, end_date: datetime) -> tuple[str, str]:
        """Convert a date range into millisecond timestamps as strings."""
        start_ts = int(datetime.combine(start_date, datetime.min.time()).timestamp())
        end_ts = int(datetime.combine(end_date, datetime.max.time()).timestamp())
        return f"{start_ts}000", f"{end_ts}000"

    @staticmethod
    def _resolve_end_date(end_date: Optional[datetime]) -> datetime:
        """Return end_date or default to now."""
        return end_date or datetime.now()

    def _resolve_time_zone(self, time_zone: Optional[str]) -> str:
        """Return time zone or default for endpoints that require it."""
        return time_zone or self.time_zone or DEFAULT_TIME_ZONE

    def _get_events(
        self,
        event_type: str,
        start_date: datetime,
        end_date: datetime,
        *,
        error_label: str,
        extra_params: Optional[dict] = None,
    ) -> list[dict]:
        """Fetch event items from the events API."""
        url = EVENTS_URL.format(user_id=self.credentials.user_id)
        start_ts, end_ts = self._date_range_to_ms(start_date, end_date)
        start_ms = int(start_ts)
        end_ms = int(end_ts)

        params = {
            "eventType": event_type,
            "limit": 1000,
        }
        if extra_params:
            params.update(extra_params)

        items: list[dict] = []
        cursor = start_ms
        while cursor <= end_ms:
            params["from"] = str(cursor)
            params["to"] = str(end_ms)

            response = self._http.get(url, params=params, headers=self._get_headers())
            if response.status_code != 200:
                raise AmazfitClientError(
                    f"Failed to get {error_label} data: {response.status_code} - {response.text}"
                )

            result = response.json()
            batch = result.get("items", [])
            if not batch:
                break

            items.extend(batch)

            if len(batch) < params["limit"]:
                break

            # Advance cursor to the last timestamp seen to avoid truncation.
            max_ts = 0
            for item in batch:
                ts = self._normalize_timestamp(item.get("timestamp", 0))
                if ts:
                    max_ts = max(max_ts, int(ts * 1000))

            if max_ts <= cursor or max_ts >= end_ms:
                break

            cursor = max_ts + 1

        return items

    def get_band_data(
        self,
        start_date: datetime,
        end_date: Optional[datetime] = None,
    ) -> list[dict]:
        """
        Get raw band data for a date range.

        Args:
            start_date: Start date for data retrieval
            end_date: End date (defaults to today)

        Returns:
            List of raw data entries from the API
        """
        self._ensure_authenticated()

        end_date = self._resolve_end_date(end_date)

        # Format dates as expected by API (timestamp in seconds)
        from_date = start_date.strftime("%Y-%m-%d")
        to_date = end_date.strftime("%Y-%m-%d")

        params = {
            "query_type": "summary",
            "device_type": "ios_phone",
            "userid": self.credentials.user_id,
            "from_date": from_date,
            "to_date": to_date,
        }

        headers = self._get_headers()

        response = self._http.get(BAND_DATA_URL, params=params, headers=headers)

        if response.status_code != 200:
            raise AmazfitClientError(
                f"Failed to get band data: {response.status_code} - {response.text}"
            )

        result = response.json()

        if result.get("code") != 1:
            raise AmazfitClientError(f"API error: {result.get('message', 'Unknown error')}")

        return result.get("data", [])

    def get_daily_data(
        self,
        start_date: datetime,
        end_date: Optional[datetime] = None,
    ) -> list[ActivityData]:
        """
        Get parsed daily activity data for a date range.

        Args:
            start_date: Start date
            end_date: End date (defaults to today)

        Returns:
            List of ActivityData objects for each day
        """
        raw_data = self.get_band_data(start_date, end_date)
        return [self._parse_day_data(day) for day in raw_data]

    def _decode_summary(self, summary_b64: str) -> Optional[dict]:
        """Decode base64 summary payload into a dict."""
        try:
            decoded = base64.b64decode(summary_b64)
            data = json.loads(decoded)
            if isinstance(data, list):
                return data[0] if data else None
            if isinstance(data, dict):
                return data
        except Exception:
            return None

    def _parse_day_data(self, raw: dict) -> ActivityData:
        """Parse raw API response into ActivityData model."""
        date_str = raw.get("date_time", raw.get("dateTime", ""))

        activity = ActivityData(date=date_str)

        # Parse summary data (base64 encoded) - contains steps, sleep, and HR
        summary_b64 = raw.get("summary", "")
        summary = self._decode_summary(summary_b64) if summary_b64 else None
        if summary:
            activity.steps = self._parse_step_summary(summary, date_str)
            # Sleep data is also in summary under 'slp' key
            activity.sleep = self._parse_sleep_from_summary(summary, date_str)
            # Activities/stages are also in summary under 'stp.stage'
            activity.activities = self._parse_activities_from_summary(summary, date_str)
            # Heart rate data is in summary under 'hr' and 'slp.rhr'
            activity.heart_rates = self._parse_heart_rate_from_summary(summary, date_str)

        return activity

    def _parse_step_summary(self, summary: dict, date_str: str) -> Optional[StepData]:
        """Parse step summary from decoded summary data."""
        try:
            # The step data is nested under 'stp' key
            stp = summary.get("stp", {})
            if isinstance(stp, dict):
                return StepData(
                    timestamp=datetime.strptime(date_str, "%Y-%m-%d") if date_str else datetime.now(),
                    steps=stp.get("ttl", 0),  # total steps
                    distance_meters=stp.get("dis", 0),
                    calories=stp.get("cal", 0),
                    run_distance=stp.get("runDist", 0),
                    walking_minutes=stp.get("wk", 0),  # minutes spent walking
                    running_calories=stp.get("runCal", 0),  # calories from running
                    running_steps=stp.get("rn", 0),  # steps from running
                )
            else:
                # Fallback for old format
                return StepData(
                    timestamp=datetime.strptime(date_str, "%Y-%m-%d") if date_str else datetime.now(),
                    steps=summary.get("stp", 0),
                    distance_meters=summary.get("dis", 0),
                    calories=summary.get("cal", 0),
                    run_distance=summary.get("runDis", 0),
                )
        except Exception:
            return None

    def _parse_sleep_from_summary(self, summary: dict, date_str: str) -> Optional[SleepData]:
        """Parse sleep data from decoded summary data."""
        try:
            slp = summary.get("slp", {})
            if not slp or not isinstance(slp, dict):
                return None

            deep_sleep = slp.get("dp", 0)
            light_sleep = slp.get("lt", 0)
            rem_sleep = slp.get("dt", 0)  # REM sleep is stored in 'dt' field
            total = deep_sleep + light_sleep + rem_sleep

            if total == 0:
                return None

            # Parse timestamps
            start_ts = slp.get("st", 0)
            end_ts = slp.get("ed", 0)

            base_date = datetime.strptime(date_str, "%Y-%m-%d") if date_str else datetime.now()

            if start_ts > 1000000000:
                start_time = datetime.fromtimestamp(start_ts)
                end_time = datetime.fromtimestamp(end_ts)
            else:
                start_time = base_date + timedelta(minutes=start_ts)
                end_time = base_date + timedelta(minutes=end_ts)

            # Parse sleep phases
            phases = []
            for stage in slp.get("stage", []):
                phase_start = stage.get("start", 0)
                phase_end = stage.get("stop", phase_start)
                mode = stage.get("mode", 4)

                # Convert minutes from midnight to datetime
                phase_start_dt = base_date + timedelta(minutes=phase_start)
                phase_end_dt = base_date + timedelta(minutes=phase_end)

                phase_type = "deep" if mode == 5 else "light" if mode == 4 else "rem" if mode in (8, 11) else "awake"

                phases.append(
                    SleepPhase(
                        start=phase_start_dt,
                        end=phase_end_dt,
                        phase_type=phase_type,
                        duration_minutes=phase_end - phase_start,
                    )
                )

            return SleepData(
                date=date_str,
                start_time=start_time,
                end_time=end_time,
                total_minutes=total,
                deep_sleep_minutes=deep_sleep,
                light_sleep_minutes=light_sleep,
                rem_sleep_minutes=rem_sleep,
                sleep_score=slp.get("ss"),  # Sleep score
                resting_heart_rate=slp.get("rhr"),  # Resting heart rate during sleep
                sleep_onset_latency=slp.get("lb") or None,  # Time to fall asleep
                wake_count=slp.get("wc", 0),  # Number of times woken up
                wake_minutes=slp.get("wk", 0),  # Minutes awake during sleep
                total_bed_time=slp.get("ebt") or None,  # Total time in bed
                out_of_bed_time=slp.get("obt") or None,  # Time out of bed
                interruption_score=slp.get("is") or None,  # Interruption score
                phases=phases,
            )
        except Exception:
            return None

    def _parse_heart_rate_from_summary(self, summary: dict, date_str: str) -> list[HeartRateData]:
        """Parse heart rate data from decoded summary data."""
        heart_rates = []
        try:
            base_date = datetime.strptime(date_str, "%Y-%m-%d") if date_str else datetime.now()

            # Get max HR from 'hr' field
            hr_data = summary.get("hr", {})
            max_hr = hr_data.get("maxHr", {})
            if max_hr and max_hr.get("hr", 0) > 0:
                hr_ts = max_hr.get("ts", 0)
                if hr_ts > 1000000000:
                    hr_time = datetime.fromtimestamp(hr_ts)
                else:
                    hr_time = base_date
                heart_rates.append(
                    HeartRateData(
                        timestamp=hr_time,
                        bpm=max_hr["hr"],
                        activity_type="max",
                    )
                )

            # Get resting HR from sleep data
            slp = summary.get("slp", {})
            rhr = slp.get("rhr", 0)
            if rhr > 0:
                heart_rates.append(
                    HeartRateData(
                        timestamp=base_date,
                        bpm=rhr,
                        activity_type="resting",
                    )
                )
        except Exception:
            pass

        return heart_rates

    def _parse_activities_from_summary(self, summary: dict, date_str: str) -> list[ActivitySummary]:
        """Parse activity stages from decoded summary data."""
        activities = []
        try:
            stp = summary.get("stp", {})
            if not isinstance(stp, dict):
                return activities

            base_date = datetime.strptime(date_str, "%Y-%m-%d") if date_str else datetime.now()

            for stage in stp.get("stage", []):
                start = stage.get("start", 0)
                stop = stage.get("stop", start)
                mode = stage.get("mode", 0)

                start_dt = base_date + timedelta(minutes=start)
                stop_dt = base_date + timedelta(minutes=stop)

                activities.append(
                    ActivitySummary(
                        start=start_dt,
                        end=stop_dt,
                        mode=mode,
                        mode_name=ACTIVITY_MODES.get(mode, f"unknown_{mode}"),
                        steps=stage.get("step", 0),
                        distance=stage.get("dis", 0),
                        calories=stage.get("cal", 0),
                    )
                )
        except Exception:
            pass

        return activities

    def get_summary(
        self,
        start_date: datetime,
        end_date: Optional[datetime] = None,
    ) -> list[DaySummary]:
        """
        Get summarized daily data for a date range.

        Args:
            start_date: Start date
            end_date: End date (defaults to today)

        Returns:
            List of DaySummary objects
        """
        daily_data = self.get_daily_data(start_date, end_date)

        summaries = []
        for day in daily_data:
            # Extract resting and max HR from heart_rates list
            resting_hr = None
            max_hr = None
            for hr in day.heart_rates:
                if hr.activity_type == "resting":
                    resting_hr = hr.bpm
                elif hr.activity_type == "max":
                    max_hr = hr.bpm

            # Also check sleep data for resting HR
            if not resting_hr and day.sleep and day.sleep.resting_heart_rate:
                resting_hr = day.sleep.resting_heart_rate

            summary = DaySummary(
                date=day.date,
                total_steps=day.steps.steps if day.steps else 0,
                total_distance_meters=day.steps.distance_meters if day.steps else 0,
                total_calories=day.steps.calories if day.steps else 0,
                sleep_minutes=day.sleep.total_minutes if day.sleep else 0,
                deep_sleep_minutes=day.sleep.deep_sleep_minutes if day.sleep else 0,
                light_sleep_minutes=day.sleep.light_sleep_minutes if day.sleep else 0,
                rem_sleep_minutes=day.sleep.rem_sleep_minutes if day.sleep else 0,
                resting_heart_rate=resting_hr,
                max_heart_rate=max_hr,
                min_heart_rate=resting_hr,  # Use resting as min
            )
            summaries.append(summary)

        return summaries

    def get_aggregate_summary(
        self,
        start_date: datetime,
        end_date: Optional[datetime] = None,
        *,
        time_zone: Optional[str] = None,
    ) -> list[DaySummary]:
        """
        Get aggregated daily data combining summary, stress, SpO2, and PAI.

        Args:
            start_date: Start date
            end_date: End date (defaults to today)

        Returns:
            List of DaySummary objects with aggregated fields
        """
        end_date = self._resolve_end_date(end_date)

        summaries = self.get_summary(start_date, end_date)
        stress = self.get_stress_data(start_date, end_date)
        spo2 = self.get_spo2_data(start_date, end_date, time_zone=time_zone)
        pai = self.get_pai_data(start_date, end_date)

        stress_by_date = {d.date: d for d in stress}
        spo2_by_date = {d.date: d for d in spo2}
        pai_by_date = {d.date: d for d in pai}

        for day in summaries:
            stress_day = stress_by_date.get(day.date)
            if stress_day:
                day.avg_stress = stress_day.avg_stress

            spo2_day = spo2_by_date.get(day.date)
            if spo2_day and spo2_day.readings:
                avg_spo2 = sum(r.spo2 for r in spo2_day.readings) / len(spo2_day.readings)
                day.avg_spo2 = int(round(avg_spo2))

            pai_day = pai_by_date.get(day.date)
            if pai_day:
                day.total_pai = pai_day.total_pai

        return summaries

    def get_stress_data(
        self,
        start_date: datetime,
        end_date: Optional[datetime] = None,
    ) -> list[StressData]:
        """
        Get stress data for a date range.

        Args:
            start_date: Start date
            end_date: End date (defaults to today)

        Returns:
            List of StressData objects for each day
        """
        self._ensure_authenticated()

        end_date = self._resolve_end_date(end_date)

        items = self._get_events(
            "all_day_stress",
            start_date,
            end_date,
            error_label="stress",
        )

        stress_list = []
        for item in items:
            date_str = self._date_str_from_ts(item.get("timestamp", 0))

            readings = []
            data_points = self._safe_json_loads(item.get("data", "[]"), [])
            if isinstance(data_points, list):
                for point in data_points:
                    point_ts = self._normalize_timestamp(point.get("time", 0))
                    readings.append(
                        StressReading(
                            timestamp=datetime.fromtimestamp(point_ts),
                            value=point.get("value", 0),
                        )
                    )

            stress_list.append(
                StressData(
                    date=date_str,
                    min_stress=int(item.get("minStress", 0)),
                    max_stress=int(item.get("maxStress", 0)),
                    avg_stress=int(item.get("avgStress", 0)),
                    relax_proportion=int(item.get("relaxProportion", 0)),
                    normal_proportion=int(item.get("normalProportion", 0)),
                    medium_proportion=int(item.get("mediumProportion", 0)),
                    high_proportion=int(item.get("highProportion", 0)),
                    readings=readings,
                )
            )

        return stress_list

    def get_spo2_data(
        self,
        start_date: datetime,
        end_date: Optional[datetime] = None,
        *,
        time_zone: Optional[str] = None,
    ) -> list[SpO2Data]:
        """
        Get blood oxygen (SpO2) data for a date range.

        Args:
            start_date: Start date
            end_date: End date (defaults to today)

        Returns:
            List of SpO2Data objects for each day
        """
        self._ensure_authenticated()

        end_date = self._resolve_end_date(end_date)

        items = self._get_events(
            "blood_oxygen",
            start_date,
            end_date,
            error_label="SpO2",
            extra_params={"timeZone": self._resolve_time_zone(time_zone)},
        )

        # Group by date
        daily_data: dict[str, SpO2Data] = {}

        for item in items:
            subtype = item.get("subType", "")

            if subtype == "odi":
                ts = self._normalize_timestamp(item.get("timestamp", 0))
                date_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")

                if date_str not in daily_data:
                    daily_data[date_str] = SpO2Data(date=date_str)

                # Oxygen Desaturation Index (from sleep)
                daily_data[date_str].odi = float(item.get("odi", 0))
                daily_data[date_str].odi_count = int(item.get("odiNum", 0))
                score = item.get("score")
                if score and int(score) > 0:
                    daily_data[date_str].sleep_score = int(score)

            elif subtype == "click":
                # Manual/auto SpO2 reading (payload is usually under `extra`)
                extra_raw = item.get("extra")
                extra = (
                    self._safe_json_loads(extra_raw, {}) if isinstance(extra_raw, str) else extra_raw
                )
                if not isinstance(extra, dict):
                    extra = {}

                spo2_val = item.get("spo2", item.get("value", 0)) or extra.get("spo2")
                if not spo2_val:
                    history = extra.get("spo2History")
                    if isinstance(history, list):
                        for val in reversed(history):
                            if val:
                                spo2_val = val
                                break

                reading_ts = extra.get("timestamp", item.get("timestamp", 0))
                reading_ts = self._normalize_timestamp(reading_ts)
                date_str = datetime.fromtimestamp(reading_ts).strftime("%Y-%m-%d")

                if date_str not in daily_data:
                    daily_data[date_str] = SpO2Data(date=date_str)

                if spo2_val:
                    reading_type = "auto" if extra.get("isAuto") else "manual"
                    daily_data[date_str].readings.append(
                        SpO2Reading(
                            timestamp=datetime.fromtimestamp(reading_ts),
                            spo2=int(spo2_val),
                            reading_type=reading_type,
                        )
                    )
            elif subtype == "osa_event":
                extra_raw = item.get("extra")
                extra = (
                    self._safe_json_loads(extra_raw, {}) if isinstance(extra_raw, str) else extra_raw
                )
                if not isinstance(extra, dict):
                    extra = {}

                event_ts = extra.get("timestamp", item.get("timestamp", 0))
                event_ts = self._normalize_timestamp(event_ts)
                date_str = datetime.fromtimestamp(event_ts).strftime("%Y-%m-%d")

                if date_str not in daily_data:
                    daily_data[date_str] = SpO2Data(date=date_str)

                spo2_decrease = extra.get("spo2_decrease")
                spo2_samples = extra.get("spo2") if isinstance(extra.get("spo2"), list) else []
                hr_samples = extra.get("hr") if isinstance(extra.get("hr"), list) else []

                daily_data[date_str].osa_events.append(
                    OSAEvent(
                        timestamp=datetime.fromtimestamp(event_ts),
                        spo2_decrease=int(spo2_decrease) if spo2_decrease is not None else None,
                        spo2_samples=[int(v) for v in spo2_samples if v is not None],
                        hr_samples=[int(v) for v in hr_samples if v is not None],
                    )
                )

        return list(daily_data.values())

    def get_pai_data(
        self,
        start_date: datetime,
        end_date: Optional[datetime] = None,
    ) -> list[PAIData]:
        """
        Get PAI (Personal Activity Intelligence) data for a date range.

        Args:
            start_date: Start date
            end_date: End date (defaults to today)

        Returns:
            List of PAIData objects for each day
        """
        self._ensure_authenticated()

        end_date = self._resolve_end_date(end_date)

        items = self._get_events(
            "PaiHealthInfo",
            start_date,
            end_date,
            error_label="PAI",
        )

        pai_list = []
        for item in items:
            date_str = self._date_str_from_ts(item.get("timestamp", 0))

            activity_scores = self._float_list(item.get("activityScores", []))
            next_activity_scores = self._float_list(item.get("nextActivityScores", []))

            pai_list.append(
                PAIData(
                    date=date_str,
                    total_pai=float(item.get("totalPai", 0)),
                    daily_pai=float(item.get("dailyPai", 0)),
                    resting_hr=int(item.get("restHr", 0)) or None,
                    max_hr=int(item.get("maxHr", 0)) or None,
                    low_zone_minutes=int(item.get("lowZoneMinutes", 0)),
                    medium_zone_minutes=int(item.get("mediumZoneMinutes", 0)),
                    high_zone_minutes=int(item.get("highZoneMinutes", 0)),
                    low_zone_pai=float(item.get("lowZonePai", 0)),
                    medium_zone_pai=float(item.get("mediumZonePai", 0)),
                    high_zone_pai=float(item.get("highZonePai", 0)),
                    low_zone_limit=int(item.get("lowZoneLowerLimit", 0)) or None,
                    medium_zone_limit=int(item.get("mediumZoneLowerLimit", 0)) or None,
                    high_zone_limit=int(item.get("highZoneLowerLimit", 0)) or None,
                    user_age=int(item.get("age", 0)) or None,
                    user_gender=int(item.get("gender")) if item.get("gender") is not None else None,
                    activity_scores=activity_scores,
                    next_activity_scores=next_activity_scores,
                )
            )

        return pai_list

    def get_workouts(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        *,
        source: Optional[str] = None,
        paginate: bool = True,
    ) -> list[Workout]:
        """
        Get workout/sport history.

        Args:
            start_date: Start date filter (optional)
            end_date: End date filter (optional)

        Returns:
            List of Workout objects
        """
        self._ensure_authenticated()

        headers = self._get_headers()

        params = {}
        if source:
            params["source"] = source

        workouts = []
        seen_track_ids = set()
        next_track_id = None

        while True:
            if next_track_id:
                params["stopTrackId"] = str(next_track_id)

            response = self._http.get(WORKOUT_HISTORY_URL, headers=headers, params=params)

            if response.status_code != 200:
                raise AmazfitClientError(
                    f"Failed to get workouts: {response.status_code} - {response.text}"
                )

            result = response.json()

            if result.get("code") != 1:
                raise AmazfitClientError(f"API error: {result.get('message', 'Unknown error')}")

            data = result.get("data", {})
            summary_list = data.get("summary", [])

            new_items = 0
            for item in summary_list:
                track_id = str(item.get("trackid", ""))
                if track_id and track_id in seen_track_ids:
                    continue
                if track_id:
                    seen_track_ids.add(track_id)
                new_items += 1

                if not track_id:
                    track_id = ""
                try:
                    end_ts = int(item.get("end_time", 0))
                    duration = int(item.get("run_time", 0))
                    start_ts = end_ts - duration

                    start_time = datetime.fromtimestamp(start_ts)
                    end_time = datetime.fromtimestamp(end_ts)

                    # Filter by date if specified
                    if start_date and start_time.date() < start_date.date():
                        continue
                    if end_date and start_time.date() > end_date.date():
                        continue

                    workout_type = int(item.get("type", 0))
                    workout_name = WORKOUT_TYPES.get(workout_type, f"unknown_{workout_type}")

                    # Parse training effect (stored as integer, divide by 10 for actual value)
                    te = item.get("te")
                    training_effect = te / 10.0 if te and te > 0 else None

                    # Parse heart rates - API returns strings like "110.0" so convert via float
                    avg_hr = item.get("avg_heart_rate")
                    max_hr = item.get("max_heart_rate")
                    min_hr = item.get("min_heart_rate")

                    # Parse anaerobic training effect
                    anaerobic = item.get("anaerobic_te")
                    anaerobic_te = anaerobic / 10.0 if anaerobic and anaerobic > 0 else None

                    # Parse VO2 max (-1 means not available)
                    vo2 = item.get("VO2_max")
                    vo2_max = int(vo2) if vo2 and int(vo2) > 0 else None

                    # Parse exercise load
                    load = item.get("exercise_load")
                    exercise_load = int(load) if load and int(load) > 0 else None

                    # Parse cadence and stride
                    cadence = item.get("avg_cadence")
                    avg_cadence = int(float(cadence)) if cadence and float(cadence) > 0 else None

                    stride = item.get("avg_stride_length")
                    avg_stride = float(stride) if stride and float(stride) > 0 else None

                    # Parse altitude (-1 means not available)
                    alt_up = item.get("altitude_ascend")
                    alt_down = item.get("altitude_descend")
                    altitude_ascend = int(alt_up) if alt_up and int(alt_up) >= 0 else None
                    altitude_descend = int(alt_down) if alt_down and int(alt_down) >= 0 else None

                    # Parse HR zones from heart_range field
                    # Format: "seconds,max_hr;seconds,max_hr;..."
                    hr_zones = []
                    hr_range = item.get("heart_range", "")
                    if hr_range:
                        zone_names = ["Very Light", "Light", "Moderate", "Hard", "Maximum", "Extreme"]
                        for i, zone_str in enumerate(hr_range.split(";")):
                            if zone_str:
                                parts = zone_str.split(",")
                                if len(parts) == 2:
                                    try:
                                        seconds = int(parts[0])
                                        max_hr_zone = int(parts[1])
                                        if seconds > 0:
                                            hr_zones.append(
                                                HeartRateZone(
                                                    zone=i + 1,
                                                    zone_name=zone_names[i]
                                                    if i < len(zone_names)
                                                    else f"Zone {i+1}",
                                                    seconds=seconds,
                                                    max_hr=max_hr_zone,
                                                )
                                            )
                                    except (ValueError, TypeError):
                                        pass

                    # Parse strength training fields
                    strength_scores = []
                    strength_groups = []
                    try:
                        scores_raw = item.get("strengthScores", [])
                        if isinstance(scores_raw, list):
                            strength_scores = [float(s) for s in scores_raw]
                        groups_raw = item.get("strength_training_group", [])
                        if isinstance(groups_raw, list):
                            for g in groups_raw:
                                if isinstance(g, dict):
                                    strength_groups.append(
                                        StrengthTrainingGroup(
                                            action_type=int(g.get("actionType", 0)),
                                            count=int(g.get("count", 0)),
                                        )
                                    )
                    except (ValueError, TypeError):
                        pass

                    total_groups = int(item.get("total_group", 0))

                    # Parse rope skipping / frequency fields
                    avg_freq = item.get("avg_frequency")
                    avg_frequency = float(avg_freq) if avg_freq and float(avg_freq) > 0 else None

                    avg_rtpc_val = item.get("averageRTPC")
                    avg_rtpc = float(avg_rtpc_val) if avg_rtpc_val and float(avg_rtpc_val) > 0 else None

                    best_rtpc_val = item.get("bestRTPC")
                    best_rtpc = int(best_rtpc_val) if best_rtpc_val and int(best_rtpc_val) > 0 else None

                    worst_rtpc_val = item.get("worstRTPC")
                    worst_rtpc = int(worst_rtpc_val) if worst_rtpc_val and int(worst_rtpc_val) > 0 else None

                    rest_time = item.get("rope_skipping_rest_time")
                    rope_rest = int(rest_time) if rest_time and int(rest_time) > 0 else None

                    # Parse running form fields
                    forefoot = item.get("forefoot_ratio")
                    forefoot_ratio = float(forefoot) if forefoot and float(forefoot) >= 0 else None

                    pause = item.get("pause_time")
                    pause_time = int(pause) if pause and int(pause) >= 0 else None

                    workouts.append(
                        Workout(
                            track_id=track_id,
                            workout_type=workout_type,
                            workout_name=workout_name,
                            start_time=start_time,
                            end_time=end_time,
                            duration_seconds=duration,
                            distance_meters=float(item.get("dis", 0) or 0),
                            calories=float(item.get("calorie", 0) or 0),
                            avg_heart_rate=int(float(avg_hr)) if avg_hr else None,
                            max_heart_rate=int(float(max_hr)) if max_hr else None,
                            min_heart_rate=int(float(min_hr)) if min_hr else None,
                            avg_pace=float(item.get("avg_pace", 0) or 0) or None,
                            total_steps=int(float(item.get("total_step", 0) or 0)),
                            training_effect=training_effect,
                            anaerobic_te=anaerobic_te,
                            vo2_max=vo2_max,
                            exercise_load=exercise_load,
                            avg_cadence=avg_cadence,
                            avg_stride_length=avg_stride,
                            altitude_ascend=altitude_ascend,
                            altitude_descend=altitude_descend,
                            hr_zones=hr_zones,
                            strength_scores=strength_scores,
                            strength_groups=strength_groups,
                            total_groups=total_groups,
                            avg_frequency=avg_frequency,
                            avg_rtpc=avg_rtpc,
                            best_rtpc=best_rtpc,
                            worst_rtpc=worst_rtpc,
                            rope_skipping_rest_time=rope_rest,
                            forefoot_ratio=forefoot_ratio,
                            pause_time=pause_time,
                        )
                    )
                except (ValueError, TypeError):
                    continue

            if not paginate:
                break

            next_track_id = data.get("next")
            if next_track_id in (None, "", 0, -1, "0", "-1"):
                break
            if str(next_track_id) in seen_track_ids:
                break
            if new_items == 0:
                break

        return workouts

    def get_readiness_data(
        self,
        start_date: datetime,
        end_date: Optional[datetime] = None,
    ) -> list[ReadinessData]:
        """
        Get readiness/recovery data including HRV and skin temperature.

        Args:
            start_date: Start date
            end_date: End date (defaults to today)

        Returns:
            List of ReadinessData objects for each day
        """
        self._ensure_authenticated()

        end_date = self._resolve_end_date(end_date)

        items = self._get_events(
            "readiness",
            start_date,
            end_date,
            error_label="readiness",
        )

        # Group by date and take the most complete record per day
        daily_data: dict[str, ReadinessData] = {}

        for item in items:
            # Only process watch_score subtype (contains the actual data)
            if item.get("subType") != "watch_score":
                continue

            ts = self._normalize_timestamp(int(item.get("timestamp", 0)))
            date_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")

            # Parse values - they come as strings
            def parse_int(val):
                if val is None or val == "" or val == "255":  # 255 means no data
                    return None
                try:
                    return int(val)
                except (ValueError, TypeError):
                    return None

            def parse_float(val):
                if val is None or val == "":
                    return None
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return None

            readiness = ReadinessData(
                date=date_str,
                readiness_score=parse_int(item.get("rdnsScore")),
                readiness_insight=parse_int(item.get("rdnsInsight")),
                rhr_score=parse_int(item.get("rhrScore")),
                rhr_baseline=parse_int(item.get("rhrBaseline")),
                sleep_rhr=parse_int(item.get("sleepRHR")),
                hrv_score=parse_int(item.get("hrvScore")),
                hrv_baseline=parse_int(item.get("hrvBaseline")),
                sleep_hrv=parse_int(item.get("sleepHRV")),
                skin_temp_score=parse_int(item.get("skinTempScore")),
                skin_temp_baseline=parse_float(item.get("skinTempBaseLine")),
                skin_temp_calibrated=parse_float(item.get("skinTempCalibrated")),
                mental_score=parse_int(item.get("mentScore")),
                mental_baseline=parse_int(item.get("mentBaseLine")),
                physical_score=parse_int(item.get("phyScore")),
                physical_baseline=parse_int(item.get("phyBaseline")),
                ahi_score=parse_int(item.get("ahiScore")),
                ahi_baseline=parse_float(item.get("ahiBaseline")),
                afib_score=parse_int(item.get("afibScore")),
                afib_baseline=parse_int(item.get("afibBaseLine")),
            )

            # Keep the record with more data for each day
            if date_str not in daily_data:
                daily_data[date_str] = readiness
            else:
                # Count non-None fields to determine which has more data
                existing = daily_data[date_str]
                existing_count = sum(1 for v in existing.model_dump().values() if v is not None)
                new_count = sum(1 for v in readiness.model_dump().values() if v is not None)
                if new_count > existing_count:
                    daily_data[date_str] = readiness

        return sorted(daily_data.values(), key=lambda x: x.date)
