from __future__ import annotations

import json
from datetime import date, datetime, timezone
from typing import Any

from fastapi import HTTPException

from backend.db import get_conn
from backend.services.decision_engine import build_readiness_briefing, build_recommendation
from backend.services.readiness_freshness import classify_readiness_freshness


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _derive_data_quality(explanation_json: Any) -> dict[str, str]:
    explanation = _as_dict(explanation_json)
    recovery_explanation = _as_dict(explanation.get("recovery_explanation"))
    fallback_mode = explanation.get("fallback_mode")
    freshness_norm = explanation.get("freshness_norm")

    # TODO: add training="partial" when readiness explanation includes explicit
    # unsupported / continuity-only load context. MVP keeps the contract simple.
    training = "ok"
    if freshness_norm is None or fallback_mode == "recovery_only":
        training = "missing"

    return {
        "sleep": "ok" if recovery_explanation.get("sleep_minutes") is not None else "missing",
        "hrv": "ok" if recovery_explanation.get("hrv_today") is not None else "missing",
        "resting_hr": "ok" if recovery_explanation.get("rhr_today") is not None else "missing",
        "training": training,
    }


def _serialize_timestamp(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _build_readiness_daily_response(
    row: tuple[Any, ...],
    *,
    evaluation_date: date | datetime | str,
) -> dict[str, Any]:
    (
        db_user_id,
        db_date,
        readiness_score,
        good_day_probability,
        status_text,
        explanation_json,
        *optional_updated_at,
    ) = row
    readiness_computed_at = optional_updated_at[0] if optional_updated_at else None
    explanation = _as_dict(explanation_json)
    source_timestamps = _as_dict(explanation.get("source_timestamps"))
    source_snapshot_missing = not source_timestamps
    recovery_source_at = source_timestamps.get("recovery_source_at")
    training_source_at = source_timestamps.get("training_source_at")
    source_timezone = source_timestamps.get("timezone") or "UTC"
    freshness = classify_readiness_freshness(
        readiness_date=db_date,
        readiness_computed_at=readiness_computed_at,
        recovery_source_at=recovery_source_at,
        training_source_at=training_source_at,
        evaluation_date=evaluation_date,
        timezone=source_timezone,
        data_quality={"fallback_mode": explanation.get("fallback_mode")},
    )
    if source_snapshot_missing:
        freshness["freshness_state"] = "missing"
        freshness["freshness_reason_codes"] = [
            "legacy_timestamp_snapshot_missing",
            *freshness["freshness_reason_codes"],
        ]
    decision = build_recommendation(
        readiness_score=readiness_score,
        explanation=explanation_json,
    )
    briefing = build_readiness_briefing(
        readiness_score=readiness_score,
        status_text=status_text,
        recommendation=decision["recommendation"],
        reason=decision["reason"],
        explanation=explanation_json,
    )

    return {
        "ok": True,
        "user_id": db_user_id,
        "date": str(db_date),
        "readiness_score": readiness_score,
        "good_day_probability": good_day_probability,
        "status_text": status_text,
        "explanation": explanation_json,
        "data_quality": _derive_data_quality(explanation_json),
        **freshness,
        "readiness_computed_at": _serialize_timestamp(readiness_computed_at),
        "recovery_source_at": _serialize_timestamp(recovery_source_at),
        "training_source_at": _serialize_timestamp(training_source_at),
        **decision,
        **briefing,
        "briefing_text": briefing["briefing"],
    }


def get_readiness_daily_for_date(user_id: str, target_date: str) -> dict[str, Any]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select
                    user_id,
                    date,
                    readiness_score,
                    good_day_probability,
                    status_text,
                    explanation_json,
                    updated_at
                from readiness_daily
                where user_id = %s
                  and date = %s
                  and version = 'v2';
                """,
                (user_id, target_date),
            )
            row = cur.fetchone()

    if not row:
        raise HTTPException(
            status_code=404,
            detail=f"readiness not found for user_id={user_id} date={target_date}",
        )

    # A date-specific read evaluates the stored snapshot against its own target
    # date, so historical rows do not age merely because they are viewed later.
    return _build_readiness_daily_response(
        row,
        evaluation_date=row[1] or target_date,
    )


def get_latest_readiness_daily(
    user_id: str,
    *,
    evaluation_at: datetime | None = None,
) -> dict[str, Any]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select
                    user_id,
                    date,
                    readiness_score,
                    good_day_probability,
                    status_text,
                    explanation_json,
                    updated_at
                from readiness_daily
                where user_id = %s
                  and version = 'v2'
                order by date desc
                limit 1;
                """,
                (user_id,),
            )
            row = cur.fetchone()

    if not row:
        raise HTTPException(
            status_code=404,
            detail=f"latest readiness not found for user_id={user_id}",
        )

    return _build_readiness_daily_response(
        row,
        evaluation_date=evaluation_at or datetime.now(timezone.utc),
    )


def get_readiness_daily_history(user_id: str, days: int) -> dict[str, Any]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select
                    date,
                    readiness_score,
                    good_day_probability,
                    status_text,
                    explanation_json
                from readiness_daily
                where user_id = %s
                  and version = 'v2'
                order by date desc
                limit %s;
                """,
                (user_id, days),
            )
            rows = cur.fetchall()

    points = [
        {
            "date": str(row_date),
            "readiness_score": readiness_score,
            "good_day_probability": good_day_probability,
            "status_text": status_text,
            "explanation": explanation_json,
        }
        for row_date, readiness_score, good_day_probability, status_text, explanation_json in rows
    ]
    points.reverse()

    return {
        "ok": True,
        "user_id": user_id,
        "days": days,
        "points": points,
    }
