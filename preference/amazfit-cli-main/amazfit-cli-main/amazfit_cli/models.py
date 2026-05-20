"""Data models for Amazfit health data."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Credentials(BaseModel):
    """Authentication credentials returned from Huami API."""

    user_id: str
    app_token: str
    login_token: str


class StepData(BaseModel):
    """Step count data for a time period."""

    timestamp: datetime
    steps: int
    distance_meters: int = Field(default=0, description="Distance in meters")
    calories: int = Field(default=0, description="Calories burned")
    run_distance: int = Field(default=0, description="Running distance in meters")
    walking_minutes: int = Field(default=0, description="Minutes spent walking")
    running_calories: int = Field(default=0, description="Calories from running")
    running_steps: int = Field(default=0, description="Steps from running")


class SleepPhase(BaseModel):
    """Individual sleep phase (deep or light sleep)."""

    start: datetime
    end: datetime
    phase_type: str = Field(description="'deep' or 'light'")
    duration_minutes: int


class SleepData(BaseModel):
    """Sleep data for a night."""

    date: str
    start_time: datetime
    end_time: datetime
    total_minutes: int
    deep_sleep_minutes: int
    light_sleep_minutes: int
    rem_sleep_minutes: int = 0
    awake_minutes: int = 0
    sleep_score: Optional[int] = Field(default=None, description="Sleep quality score (0-100)")
    resting_heart_rate: Optional[int] = Field(default=None, description="Resting HR during sleep")
    sleep_onset_latency: Optional[int] = Field(default=None, description="Minutes to fall asleep")
    wake_count: int = Field(default=0, description="Number of times woken up")
    wake_minutes: int = Field(default=0, description="Total minutes awake during sleep")
    total_bed_time: Optional[int] = Field(default=None, description="Total time in bed (minutes)")
    out_of_bed_time: Optional[int] = Field(default=None, description="Time out of bed during sleep (minutes)")
    interruption_score: Optional[int] = Field(default=None, description="Sleep interruption score")
    phases: list[SleepPhase] = Field(default_factory=list)


class HeartRateData(BaseModel):
    """Heart rate measurement."""

    timestamp: datetime
    bpm: int
    activity_type: Optional[str] = None


class ActivitySummary(BaseModel):
    """Summary of activity for a specific time window."""

    start: datetime
    end: datetime
    mode: int = Field(description="Activity mode code")
    mode_name: str = Field(description="Human readable activity name")
    steps: int = 0
    distance: int = 0
    calories: int = 0


class ActivityData(BaseModel):
    """Daily activity data including steps, sleep, and heart rate."""

    date: str
    steps: Optional[StepData] = None
    sleep: Optional[SleepData] = None
    heart_rates: list[HeartRateData] = Field(default_factory=list)
    activities: list[ActivitySummary] = Field(default_factory=list)

    @property
    def total_steps(self) -> int:
        """Total steps for the day."""
        return self.steps.steps if self.steps else 0


class StressReading(BaseModel):
    """Individual stress reading."""

    timestamp: datetime
    value: int = Field(description="Stress level (0-100)")


class StressData(BaseModel):
    """Daily stress data."""

    date: str
    min_stress: int = 0
    max_stress: int = 0
    avg_stress: int = 0
    relax_proportion: int = Field(default=0, description="% of day in relaxed state")
    normal_proportion: int = Field(default=0, description="% of day in normal state")
    medium_proportion: int = Field(default=0, description="% of day in medium stress")
    high_proportion: int = Field(default=0, description="% of day in high stress")
    readings: list[StressReading] = Field(default_factory=list)


class SpO2Reading(BaseModel):
    """Individual blood oxygen reading."""

    timestamp: datetime
    spo2: int = Field(description="Blood oxygen percentage (0-100)")
    reading_type: str = Field(default="auto", description="'manual' or 'auto'")


class OSAEvent(BaseModel):
    """Sleep apnea event data (OSA)."""

    timestamp: datetime
    spo2_decrease: Optional[int] = Field(default=None, description="Lowest SpO2 during event")
    spo2_samples: list[int] = Field(default_factory=list, description="SpO2 sample series")
    hr_samples: list[int] = Field(default_factory=list, description="HR sample series")


class SpO2Data(BaseModel):
    """Daily blood oxygen data."""

    date: str
    odi: Optional[float] = Field(default=None, description="Oxygen Desaturation Index")
    odi_count: int = Field(default=0, description="Number of desaturation events")
    sleep_score: Optional[int] = Field(default=None, description="Sleep breathing score")
    readings: list[SpO2Reading] = Field(default_factory=list)
    osa_events: list[OSAEvent] = Field(default_factory=list)


class PAIData(BaseModel):
    """Personal Activity Intelligence data for a day."""

    date: str
    total_pai: float = Field(default=0, description="7-day rolling PAI score")
    daily_pai: float = Field(default=0, description="PAI earned today")
    resting_hr: Optional[int] = Field(default=None, description="Resting heart rate")
    max_hr: Optional[int] = Field(default=None, description="Max heart rate capacity")
    low_zone_minutes: int = Field(default=0, description="Minutes in low intensity zone")
    medium_zone_minutes: int = Field(default=0, description="Minutes in medium intensity zone")
    high_zone_minutes: int = Field(default=0, description="Minutes in high intensity zone")
    low_zone_pai: float = Field(default=0, description="PAI from low zone")
    medium_zone_pai: float = Field(default=0, description="PAI from medium zone")
    high_zone_pai: float = Field(default=0, description="PAI from high zone")
    low_zone_limit: Optional[int] = Field(default=None, description="Low zone HR lower limit")
    medium_zone_limit: Optional[int] = Field(default=None, description="Medium zone HR lower limit")
    high_zone_limit: Optional[int] = Field(default=None, description="High zone HR lower limit")
    user_age: Optional[int] = Field(default=None, description="User age for PAI calculation")
    user_gender: Optional[int] = Field(default=None, description="User gender (0=male, 1=female)")
    activity_scores: list[float] = Field(default_factory=list, description="7-day activity score history")
    next_activity_scores: list[float] = Field(default_factory=list, description="Projected activity scores")


class HeartRateZone(BaseModel):
    """Heart rate zone data from a workout."""

    zone: int = Field(description="Zone number (1-6)")
    zone_name: str = Field(description="Zone name (Very Light, Light, Moderate, Hard, Maximum)")
    seconds: int = Field(description="Time spent in this zone (seconds)")
    max_hr: int = Field(description="Upper HR limit for this zone")


class StrengthTrainingGroup(BaseModel):
    """A group/set in a strength training workout."""

    action_type: int = Field(description="Type of exercise (0=general)")
    count: int = Field(description="Number of reps in this set")


# Workout type codes
WORKOUT_TYPES = {
    1: "outdoor_running",
    2: "walking",
    3: "cycling",
    4: "treadmill",
    5: "indoor_cycling",
    6: "elliptical",
    7: "climbing",
    8: "trail_running",
    9: "skiing",
    10: "snowboarding",
    16: "freestyle",
    17: "swimming",
    18: "indoor_swimming",
    19: "open_water_swimming",
    20: "yoga",
    21: "rowing",
    22: "indoor_rowing",
    64: "strength_training",
    128: "hiit",
    223: "other",
}


class Workout(BaseModel):
    """A recorded workout/sport activity."""

    track_id: str = Field(description="Unique workout identifier")
    workout_type: int = Field(description="Workout type code")
    workout_name: str = Field(default="", description="Human readable workout type")
    start_time: datetime
    end_time: datetime
    duration_seconds: int = Field(default=0, description="Total duration in seconds")
    distance_meters: float = Field(default=0, description="Distance in meters")
    calories: float = Field(default=0, description="Calories burned")
    avg_heart_rate: Optional[int] = None
    max_heart_rate: Optional[int] = None
    min_heart_rate: Optional[int] = None
    avg_pace: Optional[float] = Field(default=None, description="Average pace (min/km)")
    total_steps: int = Field(default=0, description="Total steps during workout")
    training_effect: Optional[float] = Field(default=None, description="Aerobic training effect (1-5)")
    anaerobic_te: Optional[float] = Field(default=None, description="Anaerobic training effect (1-5)")
    vo2_max: Optional[int] = Field(default=None, description="Estimated VO2 max")
    exercise_load: Optional[int] = Field(default=None, description="Exercise load score")
    avg_cadence: Optional[int] = Field(default=None, description="Average cadence (steps/strokes per min)")
    avg_stride_length: Optional[float] = Field(default=None, description="Average stride length (cm)")
    altitude_ascend: Optional[int] = Field(default=None, description="Total elevation gain (m)")
    altitude_descend: Optional[int] = Field(default=None, description="Total elevation loss (m)")
    hr_zones: list[HeartRateZone] = Field(default_factory=list, description="Time in each HR zone")
    # Strength training fields
    strength_scores: list[float] = Field(default_factory=list, description="Strength scores per set")
    strength_groups: list[StrengthTrainingGroup] = Field(default_factory=list, description="Strength training sets")
    total_groups: int = Field(default=0, description="Total number of strength training sets")
    # Rope skipping / jumping fields
    avg_frequency: Optional[float] = Field(default=None, description="Average frequency (jumps/min)")
    avg_rtpc: Optional[float] = Field(default=None, description="Average rope turns per cycle")
    best_rtpc: Optional[int] = Field(default=None, description="Best rope turns per cycle")
    worst_rtpc: Optional[int] = Field(default=None, description="Worst rope turns per cycle")
    rope_skipping_rest_time: Optional[int] = Field(default=None, description="Rest time during rope skipping (s)")
    # Running form analysis
    forefoot_ratio: Optional[float] = Field(default=None, description="Forefoot strike ratio (-1 if unavailable)")
    pause_time: Optional[int] = Field(default=None, description="Total pause time (seconds)")


class ReadinessData(BaseModel):
    """Daily readiness/recovery data including HRV and skin temperature."""

    date: str
    readiness_score: Optional[int] = Field(default=None, description="Overall readiness score (0-100)")
    readiness_insight: Optional[int] = Field(default=None, description="Readiness insight code")
    rhr_score: Optional[int] = Field(default=None, description="Resting heart rate score (0-100)")
    rhr_baseline: Optional[int] = Field(default=None, description="Personal RHR baseline (bpm)")
    sleep_rhr: Optional[int] = Field(default=None, description="Resting HR during sleep (bpm)")
    hrv_score: Optional[int] = Field(default=None, description="Heart rate variability score (0-100)")
    hrv_baseline: Optional[int] = Field(default=None, description="Personal HRV baseline (ms)")
    sleep_hrv: Optional[int] = Field(default=None, description="HRV during sleep (ms)")
    skin_temp_score: Optional[int] = Field(default=None, description="Skin temperature score (0-100)")
    skin_temp_baseline: Optional[float] = Field(default=None, description="Skin temp baseline (°C deviation)")
    skin_temp_calibrated: Optional[float] = Field(default=None, description="Calibrated skin temp (°C deviation)")
    mental_score: Optional[int] = Field(default=None, description="Mental wellness score (0-100)")
    mental_baseline: Optional[int] = Field(default=None, description="Mental baseline")
    physical_score: Optional[int] = Field(default=None, description="Physical score (0-100)")
    physical_baseline: Optional[int] = Field(default=None, description="Physical baseline")
    ahi_score: Optional[int] = Field(default=None, description="Sleep apnea (AHI) score (0-100)")
    ahi_baseline: Optional[float] = Field(default=None, description="AHI baseline value")
    afib_score: Optional[int] = Field(default=None, description="Atrial fibrillation score")
    afib_baseline: Optional[int] = Field(default=None, description="AFib baseline")


class DaySummary(BaseModel):
    """Full day summary with all health metrics."""

    date: str
    total_steps: int = 0
    total_distance_meters: int = 0
    total_calories: int = 0
    sleep_minutes: int = 0
    deep_sleep_minutes: int = 0
    light_sleep_minutes: int = 0
    rem_sleep_minutes: int = 0
    resting_heart_rate: Optional[int] = None
    max_heart_rate: Optional[int] = None
    min_heart_rate: Optional[int] = None
    avg_stress: Optional[int] = None
    avg_spo2: Optional[int] = None
    total_pai: Optional[float] = None
