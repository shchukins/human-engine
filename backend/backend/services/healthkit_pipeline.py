from __future__ import annotations

from typing import Any

from backend.schemas.healthkit import HealthSyncPayload
from backend.services.health_recovery_daily import recompute_health_recovery_daily_for_date
from backend.services.healthkit_ingest import save_healthkit_ingest_raw
from backend.services.healthkit_processing import process_latest_healthkit_raw
from backend.services.readiness_daily import recompute_readiness_daily_for_date


def _collect_affected_dates(payload: HealthSyncPayload) -> list[str]:
    dates: set[str] = set()

    for item in payload.sleepNights:
        dates.add(str(item.wakeDate))

    for item in payload.restingHeartRateDaily:
        dates.add(str(item.date))

    for item in payload.hrvSamples:
        dates.add(item.startAt.date().isoformat())

    if payload.latestWeight is not None:
        dates.add(payload.latestWeight.measuredAt.date().isoformat())

    return sorted(dates)


def ingest_and_process_healthkit_payload(user_id: str, payload: HealthSyncPayload) -> dict[str, Any]:
    # 1. Raw ingest
    save_healthkit_ingest_raw(user_id=user_id, payload=payload)

    # 2. Latest raw -> normalized tables
    processing_result = process_latest_healthkit_raw(user_id=user_id)

    # 3. Determine affected dates from payload
    affected_dates = _collect_affected_dates(payload)

    recovery_results = []
    readiness_results = []

    # 4. Recompute recovery + readiness for all affected dates
    for target_date in affected_dates:
        recovery_result = recompute_health_recovery_daily_for_date(
            user_id=user_id,
            target_date=target_date,
        )
        recovery_results.append(recovery_result)

        readiness_result = recompute_readiness_daily_for_date(
            user_id=user_id,
            target_date=target_date,
        )
        readiness_results.append(readiness_result)

    return {
        "ok": True,
        "user_id": user_id,
        "affected_dates": affected_dates,
        "sleep_nights_count": len(payload.sleepNights),
        "resting_hr_count": len(payload.restingHeartRateDaily),
        "hrv_count": len(payload.hrvSamples),
        "latest_weight_included": payload.latestWeight is not None,
        "normalized": processing_result,
        "recovery_days_recomputed": len(recovery_results),
        "readiness_days_recomputed": len(readiness_results),
    }