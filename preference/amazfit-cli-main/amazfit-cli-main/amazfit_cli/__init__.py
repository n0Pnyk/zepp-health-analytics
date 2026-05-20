"""Amazfit Health API - Python client for accessing Amazfit/Zepp health data."""

from amazfit_cli.client import AmazfitClient
from amazfit_cli.models import (
    ActivityData,
    Credentials,
    HeartRateData,
    HeartRateZone,
    OSAEvent,
    PAIData,
    ReadinessData,
    SleepData,
    SpO2Data,
    StepData,
    StrengthTrainingGroup,
    StressData,
    Workout,
)

__version__ = "0.1.0"
__all__ = [
    "AmazfitClient",
    "ActivityData",
    "Credentials",
    "HeartRateData",
    "HeartRateZone",
    "OSAEvent",
    "PAIData",
    "ReadinessData",
    "SleepData",
    "SpO2Data",
    "StepData",
    "StrengthTrainingGroup",
    "StressData",
    "Workout",
]
