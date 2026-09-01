from __future__ import annotations

import json
import logging
import time
from typing import Any

from fastapi import HTTPException

from backend.core.logging import log_event
from backend.db import get_conn
from backend.services.activity_response_service import load_recent_response_context
from backend.services.decision_engine import build_readiness_briefing, build_recommendation
from backend.services.readiness_composition import (
    READINESS_MODEL_VERSION,
    compose_readiness,
)

logger = logging.getLogger(__name__)


def _describe_readiness_status(score: float | None) -> str:
    if score is None:
        return "n/a"
    if score <= 24:
        return "Высокая усталость"
    if score <= 44:
        return "Нагрузка"
    if score <= 64:
        return "Нормальная готовность"
    if score <= 84:
        return "Хорошая готовность"
    return "Очень свежий"


def _detect_fallback_mode(signal_families: dict[str, Any]) -> str | None:
    freshness_used = signal_families["freshness"]["used"]
    feeling_used = signal_families["feeling"]["used"]
    physiology_used = signal_families["physiology"]["used"]
    if physiology_used and not freshness_used and not feeling_used:
        return "recovery_only"
    if freshness_used and not feeling_used and not physiology_used:
        return "load_only"
    if feeling_used and not freshness_used and not physiology_used:
        return "feeling_only"
    return None


def recompute_readiness_daily_for_date(user_id: str, target_date: str) -> dict[str, Any]:
    started_at = time.perf_counter()
    log_event(
        logger,
        "readiness_recompute_started",
        user_id=user_id,
        target_date=target_date,
    )

    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select
                        tss,
                        load_input_nonlinear,
                        fitness,
                        fatigue_fast,
                        fatigue_slow,
                        fatigue_total,
                        freshness
                    from load_state_daily_v2
                    where user_id = %s
                      and date = %s
                      and version = 'v2';
                    """,
                    (user_id, target_date),
                )
                load_row = cur.fetchone()

                cur.execute(
                    """
                    select
                        recovery_score_simple,
                        recovery_explanation_json
                    from health_recovery_daily
                    where user_id = %s
                      and date = %s;
                    """,
                    (user_id, target_date),
                )
                recovery_row = cur.fetchone()

                cur.execute(
                    """
                    select feedback_score
                    from activity_subjective_feedback
                    where user_id = %s
                      and activity_date = %s
                      and feedback_type = 'next_day_recovery'
                      and strava_activity_id is null
                    order by updated_at desc
                    limit 1;
                    """,
                    (user_id, target_date),
                )
                feeling_row = cur.fetchone()
                response_context = load_recent_response_context(
                    cur,
                    user_id=user_id,
                    target_date=target_date,
                )

                load_context = (
                    {
                        "tss": load_row[0],
                        "load_input_nonlinear": load_row[1],
                        "fitness": load_row[2],
                        "fatigue_fast": load_row[3],
                        "fatigue_slow": load_row[4],
                        "fatigue_total": load_row[5],
                    }
                    if load_row
                    else None
                )
                freshness = load_row[6] if load_row else None
                recovery_score_simple = recovery_row[0] if recovery_row else None
                recovery_explanation = recovery_row[1] if recovery_row else None
                feeling_score = feeling_row[0] if feeling_row else None

                if isinstance(recovery_explanation, str):
                    recovery_explanation = json.loads(recovery_explanation)

                if freshness is None and recovery_score_simple is None and feeling_score is None:
                    raise HTTPException(
                        status_code=404,
                        detail=(
                            "no freshness, feeling, or physiology data found for "
                            f"user_id={user_id} date={target_date}"
                        ),
                    )

                composition = compose_readiness(
                    load_context=load_context,
                    freshness=freshness,
                    feeling_score=feeling_score,
                    physiology_score=recovery_score_simple,
                    physiology_explanation=recovery_explanation,
                    response_context=response_context,
                )
                signal_families = composition["signal_families"]
                fallback_mode = _detect_fallback_mode(signal_families)
                freshness_norm = signal_families["freshness"]["score"]
                readiness_score_raw = composition["readiness_score_raw"]
                readiness_score = composition["readiness_score"]

                good_day_probability = (
                    round(readiness_score / 100.0, 3)
                    if readiness_score is not None
                    else None
                )

                status_text = _describe_readiness_status(readiness_score)

                cur.execute(
                    """
                    select timezone
                    from healthkit_ingest_raw
                    where user_id = %s
                    order by received_at desc
                    limit 1;
                    """,
                    (user_id,),
                )
                timezone_row = cur.fetchone()
                source_timezone = timezone_row[0] if timezone_row else "UTC"

                explanation_json = {
                    "fallback_mode": fallback_mode,
                    "freshness": freshness,
                    "freshness_norm": freshness_norm,
                    "recovery_score_simple": recovery_score_simple,
                    "feeling_score": feeling_score,
                    "signal_families": signal_families,
                    "reason_codes": composition["reason_codes"],
                    "model": composition["model"],
                    "formula": composition["model"]["formula_version"],
                    "recovery_explanation": recovery_explanation,
                    "source_timestamps": {
                        # These are source-row dates, not fabricated timestamps.
                        "recovery_source_at": target_date if recovery_row else None,
                        "training_source_at": target_date if load_row else None,
                        "timezone": source_timezone,
                    },
                }

                cur.execute(
                    """
                    insert into readiness_daily (
                        user_id,
                        date,
                        freshness,
                        recovery_score_simple,
                        readiness_score_raw,
                        readiness_score,
                        good_day_probability,
                        status_text,
                        explanation_json,
                        version,
                        updated_at
                    )
                    values (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, now()
                    )
                    on conflict (user_id, date, version) do update set
                        freshness = excluded.freshness,
                        recovery_score_simple = excluded.recovery_score_simple,
                        readiness_score_raw = excluded.readiness_score_raw,
                        readiness_score = excluded.readiness_score,
                        good_day_probability = excluded.good_day_probability,
                        status_text = excluded.status_text,
                        explanation_json = excluded.explanation_json,
                        updated_at = now();
                    """,
                    (
                        user_id,
                        target_date,
                        freshness,
                        recovery_score_simple,
                        readiness_score_raw,
                        readiness_score,
                        good_day_probability,
                        status_text,
                        json.dumps(explanation_json),
                        READINESS_MODEL_VERSION,
                    ),
                )
                conn.commit()

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

        result = {
            "ok": True,
            "user_id": user_id,
            "date": target_date,
            "freshness": freshness,
            "freshness_norm": freshness_norm,
            "recovery_score_simple": recovery_score_simple,
            "feeling_score": feeling_score,
            "readiness_score_raw": readiness_score_raw,
            "readiness_score": readiness_score,
            "good_day_probability": good_day_probability,
            "status_text": status_text,
            "fallback_mode": fallback_mode,
            "model_version": READINESS_MODEL_VERSION,
            "signal_families": signal_families,
            "reason_codes": composition["reason_codes"],
            "explanation_json": explanation_json,
            **decision,
            **briefing,
            "briefing_text": briefing["briefing"],
        }
        log_event(
            logger,
            "readiness_recompute_finished",
            user_id=user_id,
            target_date=target_date,
            readiness_score=readiness_score,
            good_day_probability=good_day_probability,
            duration_ms=round((time.perf_counter() - started_at) * 1000, 2),
        )
        return result
    except Exception as exc:
        log_event(
            logger,
            "error",
            level=logging.ERROR,
            error_type=type(exc).__name__,
            error=str(exc),
            context="readiness_recompute",
            user_id=user_id,
            target_date=target_date,
        )
        raise
