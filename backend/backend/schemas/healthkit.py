from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class SleepNightDTO(BaseModel):
    wakeDate: date
    sleepStart: datetime
    sleepEnd: datetime
    totalSleepMinutes: float
    awakeMinutes: float
    coreMinutes: float
    remMinutes: float
    deepMinutes: float
    inBedMinutes: Optional[float] = None


class RestingHRDailyDTO(BaseModel):
    date: date
    bpm: float


class HRVSampleDTO(BaseModel):
    startAt: datetime
    valueMs: float


class LatestWeightDTO(BaseModel):
    measuredAt: datetime
    kilograms: float


class HealthSyncPayload(BaseModel):
    generatedAt: datetime
    timezone: str = Field(min_length=1)
    sleepNights: List[SleepNightDTO] = Field(default_factory=list)
    restingHeartRateDaily: List[RestingHRDailyDTO] = Field(default_factory=list)
    hrvSamples: List[HRVSampleDTO] = Field(default_factory=list)
    latestWeight: Optional[LatestWeightDTO] = None


class HealthIngestResponse(BaseModel):
    ok: bool = True
    user_id: str
    sleep_nights_count: int
    resting_hr_count: int
    hrv_count: int
    latest_weight_included: bool