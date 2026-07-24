from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from backend.config import settings
from backend.core.logging import log_event
from backend.schemas.healthkit import HealthSyncPayload
from backend.services.health_recovery_daily import recompute_health_recovery_daily_for_date
from backend.services.healthkit_ingest import save_healthkit_ingest_raw
from backend.services.healthkit_processing import process_latest_healthkit_raw
from backend.services.load_state_v2 import recompute_load_state_daily_v2
from backend.services.notification_service import send_daily_readiness
from backend.services.readiness_daily import recompute_readiness_daily_for_date

logger = logging.getLogger(__name__)


def _recovery_dates(payload: HealthSyncPayload) -> set[str]:
    dates = {str(item.wakeDate) for item in payload.sleepNights}
    dates.update(str(item.date) for item in payload.restingHeartRateDaily)
    dates.update(item.startAt.date().isoformat() for item in payload.hrvSamples)
    return dates


def _local_today(timezone_name: str) -> str:
    try:
        local_timezone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        local_timezone = timezone.utc
    return datetime.now(timezone.utc).astimezone(local_timezone).date().isoformat()


def _successful_sync_at() -> datetime:
    return datetime.now(timezone.utc)


def _send_fresh_morning_briefing(
    *,
    user_id: str,
    payload: HealthSyncPayload,
) -> None:
    notification_date = date.fromisoformat(_local_today(payload.timezone))
    eligible_recovery_dates = {
        notification_date,
        notification_date - timedelta(days=1),
    }
    affected_recovery_dates = {
        date.fromisoformat(value) for value in _recovery_dates(payload)
    }
    eligible_affected_dates = affected_recovery_dates & eligible_recovery_dates

    if user_id != settings.daily_readiness_user_id or not eligible_affected_dates:
        return

    recovery_date = max(eligible_affected_dates)
    data_freshness = {
        "state": "fresh",
        "recovery_date": recovery_date.isoformat(),
        "last_successful_sync_at": _successful_sync_at(),
    }
    try:
        sent = send_daily_readiness(
            user_id=user_id,
            notification_date=notification_date,
            recovery_date=recovery_date,
            data_freshness=data_freshness,
        )
        log_event(
            logger,
            "daily_readiness_fresh_sync_triggered",
            user_id=user_id,
            notification_date=notification_date.isoformat(),
            recovery_date=recovery_date.isoformat(),
            sent=sent,
        )
    except Exception as error:
        # Notification delivery is auxiliary: a Telegram failure must not turn
        # an already successful deterministic HealthKit pipeline into a failed sync.
        log_event(
            logger,
            "daily_readiness_fresh_sync_failed",
            level=logging.ERROR,
            user_id=user_id,
            notification_date=notification_date.isoformat(),
            recovery_date=recovery_date.isoformat(),
            error_type=type(error).__name__,
            error=str(error),
        )


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


def _validate_pipeline_consistency(
    affected_dates: list[str],
    load_result: dict[str, Any],
    readiness_results: list[dict[str, Any]],
) -> None:
    if not affected_dates:
        return

    load_last_date = load_result.get("last_date")
    latest_affected_date = affected_dates[-1]

    if load_last_date is None or load_last_date < latest_affected_date:
        raise ValueError(
            "load_state_daily_v2 did not reach latest recovery date: "
            f"load_last_date={load_last_date}, latest_affected_date={latest_affected_date}"
        )

    readiness_by_date = {result.get("date"): result for result in readiness_results}

    for target_date in affected_dates:
        readiness_result = readiness_by_date.get(target_date)
        if not readiness_result or not readiness_result.get("ok"):
            raise ValueError(f"readiness_daily was not created for date={target_date}")

        explanation_json = readiness_result.get("explanation_json")
        if not isinstance(explanation_json, dict):
            raise ValueError(f"readiness explanation missing for date={target_date}")

        if "recovery_explanation" not in explanation_json:
            raise ValueError(
                f"readiness explanation missing recovery_explanation for date={target_date}"
            )

        if readiness_result.get("freshness") is None:
            raise ValueError(
                "freshness is missing after load recompute for date="
                f"{target_date}"
            )


def ingest_and_process_healthkit_payload(user_id: str, payload: HealthSyncPayload) -> dict[str, Any]:
    # 1. Raw ingest
    save_healthkit_ingest_raw(user_id=user_id, payload=payload)

    # 2. Latest raw -> normalized tables
    processing_result = process_latest_healthkit_raw(user_id=user_id)

    # 3. Determine affected dates from payload
    affected_dates = _collect_affected_dates(payload)
    max_affected_date = affected_dates[-1] if affected_dates else None

    recovery_results = []
    readiness_results = []

    # 4. Recompute recovery for all affected dates
    for target_date in affected_dates:
        recovery_result = recompute_health_recovery_daily_for_date(
            user_id=user_id,
            target_date=target_date,
        )
        recovery_results.append(recovery_result)

    # 5. Recompute load state after recovery so freshness is available to readiness.
    load_result = recompute_load_state_daily_v2(user_id=user_id)

    # 6. Recompute readiness for all affected dates
    for target_date in affected_dates:
        readiness_result = recompute_readiness_daily_for_date(
            user_id=user_id,
            target_date=target_date,
        )
        readiness_results.append(readiness_result)

    _validate_pipeline_consistency(
        affected_dates=affected_dates,
        load_result=load_result,
        readiness_results=readiness_results,
    )

    log_event(
        logger,
        "healthkit_payload_processed",
        user_id=user_id,
        affected_dates_count=len(affected_dates),
        sleep_count=len(payload.sleepNights),
        hrv_count=len(payload.hrvSamples),
        rhr_count=len(payload.restingHeartRateDaily),
        readiness_days_recomputed=len(readiness_results),
    )
    _send_fresh_morning_briefing(user_id=user_id, payload=payload)

    return {
        "ok": True,
        "user_id": user_id,
        "affected_dates": affected_dates,
        "max_affected_date": max_affected_date,
        "sleep_nights_count": len(payload.sleepNights),
        "resting_hr_count": len(payload.restingHeartRateDaily),
        "hrv_count": len(payload.hrvSamples),
        "latest_weight_included": payload.latestWeight is not None,
        "normalized": processing_result,
        "recovery_days_recomputed": len(recovery_results),
        "load_recomputed": True,
        "load_days_recomputed": load_result.get("days_processed"),
        "load_last_date": load_result.get("last_date"),
        "readiness_days_recomputed": len(readiness_results),
        "downstream_consistency_checked": True,
    }
