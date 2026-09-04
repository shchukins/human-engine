from __future__ import annotations

from datetime import date
from typing import Any

from backend.config import settings
from backend.db import get_conn
from backend.services.decision_engine import build_recommendation
from backend.services.readiness_composition import READINESS_MODEL_VERSION


PILOT_QUERY = """
with days as (
    select generate_series(%s::date, %s::date, interval '1 day')::date as day
), activity_stats as (
    select
        (r.start_date at time zone %s)::date as day,
        count(*) as activity_count,
        count(*) filter (
            where delivery.delivery_status = 'sent'
        ) as rpe_prompt_count,
        count(*) filter (
            where delivery.delivery_status = 'sent'
              and feedback.id is not null
        ) as rpe_response_count
    from strava_activity_raw r
    left join activity_delivery_log delivery
      on delivery.activity_id = r.strava_activity_id
     and delivery.delivery_type = 'post_ride_rpe'
    left join activity_subjective_feedback feedback
      on feedback.canonical_activity_id = r.strava_activity_id
     and feedback.feedback_type = 'post_ride_rpe'
    where r.user_id = %s
      and (r.start_date at time zone %s)::date between %s::date and %s::date
      and r.is_deleted = false
      and r.is_excluded = false
    group by 1
), snapshot_stats as (
    select
        snapshot_date as day,
        (array_agg(snapshot_json order by captured_at)
            filter (where event_type = 'recovery_checkin_before'))[1] as checkin_before,
        (array_agg(snapshot_json order by captured_at desc)
            filter (where event_type = 'recovery_checkin_after'))[1] as checkin_after,
        (array_agg(snapshot_json order by captured_at desc)
            filter (where event_type = 'daily_readiness_delivery'))[1] as delivery_snapshot
    from decision_context_snapshot
    where user_id = %s
      and snapshot_date between %s::date and %s::date
    group by snapshot_date
), ingest_failures as (
    select
        (coalesce(finished_at, started_at, scheduled_at) at time zone %s)::date as day,
        count(*) as failure_count
    from strava_activity_ingest_job
    where user_id = %s
      and status in ('failed', 'error')
      and (coalesce(finished_at, started_at, scheduled_at) at time zone %s)::date
          between %s::date and %s::date
    group by 1
)
select
    days.day,
    readiness.readiness_score,
    readiness.good_day_probability,
    readiness.status_text,
    readiness.explanation_json,
    readiness.updated_at,
    notification.delivery_status,
    coalesce(previous_load.activities_count, 0),
    coalesce(previous_load.tss, 0),
    prompt.delivery_status,
    recovery_feedback.id is not null,
    coalesce(activity_stats.activity_count, 0),
    coalesce(activity_stats.rpe_prompt_count, 0),
    coalesce(activity_stats.rpe_response_count, 0),
    snapshot_stats.checkin_before,
    snapshot_stats.checkin_after,
    snapshot_stats.delivery_snapshot,
    coalesce(ingest_failures.failure_count, 0),
    case
        when notification.delivery_status = 'failed' then 1
        else 0
    end + case
        when prompt.delivery_status = 'failed' then 1
        else 0
    end as delivery_failures
from days
left join readiness_daily readiness
  on readiness.user_id = %s
 and readiness.date = days.day
 and readiness.version = %s
left join notification_log notification
  on notification.user_id = %s
 and notification.notification_type = 'daily_readiness'
 and notification.notification_date = days.day
left join daily_training_load previous_load
  on previous_load.user_id = %s
 and previous_load.date = days.day - 1
left join subjective_feedback_prompt_log prompt
  on prompt.user_id = %s
 and prompt.prompt_type = 'next_day_recovery'
 and prompt.target_date = days.day
left join activity_subjective_feedback recovery_feedback
  on recovery_feedback.user_id = %s
 and recovery_feedback.activity_date = days.day
 and recovery_feedback.feedback_type = 'next_day_recovery'
 and recovery_feedback.strava_activity_id is null
left join activity_stats on activity_stats.day = days.day
left join snapshot_stats on snapshot_stats.day = days.day
left join ingest_failures on ingest_failures.day = days.day
order by days.day;
"""


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _rate(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def _decision_changed(before: Any, after: Any) -> bool | None:
    before = _as_dict(before)
    after = _as_dict(after)
    if not before or not after:
        return None
    return (
        before.get("readiness_score") != after.get("readiness_score")
        or before.get("recommendation") != after.get("recommendation")
    )


def build_pilot_report(
    *,
    user_id: str,
    date_from: date,
    date_to: date,
    timezone: str,
    rows: list[tuple[Any, ...]],
) -> dict[str, Any]:
    if date_to < date_from:
        raise ValueError("date_to must be on or after date_from")

    signal_distribution = {
        family: {"available_days": 0, "used_days": 0}
        for family in ("load", "freshness", "response", "feeling", "physiology")
    }
    days: list[dict[str, Any]] = []
    valid_recommendations = 0
    valid_without_physiology = 0
    recovery_eligible = recovery_responses = 0
    rpe_prompts = rpe_responses = 0
    checkin_observed = checkin_changed = 0
    stale_or_missing_training_days = 0
    ingest_failures = delivery_failures = 0

    for row in rows:
        (
            day,
            readiness_score,
            good_day_probability,
            status_text,
            explanation_json,
            readiness_computed_at,
            notification_status,
            previous_activities_count,
            previous_tss,
            recovery_prompt_status,
            has_recovery_feedback,
            activity_count,
            day_rpe_prompts,
            day_rpe_responses,
            checkin_before,
            checkin_after,
            delivery_snapshot,
            day_ingest_failures,
            day_delivery_failures,
        ) = row
        explanation = _as_dict(explanation_json)
        families = _as_dict(explanation.get("signal_families"))
        source_timestamps = _as_dict(explanation.get("source_timestamps"))
        training_source_at = source_timestamps.get("training_source_at")
        training_is_current = (
            training_source_at is not None and str(training_source_at) == str(day)
        )
        stale_or_missing_training_days += int(not training_is_current)
        recommendation = None
        if readiness_score is not None:
            recommendation = build_recommendation(
                readiness_score=float(readiness_score),
                explanation=explanation,
            )["recommendation"]
            valid_recommendations += 1
            if (
                _as_dict(families.get("physiology")).get("availability")
                != "available"
            ):
                valid_without_physiology += 1

        for family, counts in signal_distribution.items():
            state = _as_dict(families.get(family))
            counts["available_days"] += int(
                state.get("availability") == "available"
            )
            counts["used_days"] += int(bool(state.get("used")))

        eligible = int(previous_activities_count or 0) > 0 or float(previous_tss or 0) > 0
        recovery_eligible += int(eligible)
        recovery_responses += int(eligible and bool(has_recovery_feedback))
        rpe_prompts += int(day_rpe_prompts or 0)
        rpe_responses += int(day_rpe_responses or 0)
        changed = _decision_changed(checkin_before, checkin_after)
        if changed is not None:
            checkin_observed += 1
            checkin_changed += int(changed)
        ingest_failures += int(day_ingest_failures or 0)
        delivery_failures += int(day_delivery_failures or 0)

        days.append({
            "date": str(day),
            "readiness_score": readiness_score,
            "good_day_probability": good_day_probability,
            "status_text": status_text,
            "recommendation": recommendation,
            "readiness_computed_at": readiness_computed_at,
            "notification_status": notification_status,
            "recovery_prompt_status": recovery_prompt_status,
            "recovery_feedback": bool(has_recovery_feedback),
            "activities": int(activity_count or 0),
            "rpe_prompts": int(day_rpe_prompts or 0),
            "rpe_responses": int(day_rpe_responses or 0),
            "checkin_decision_changed": changed,
            "delivery_snapshot_available": bool(delivery_snapshot),
            "training_input_current": training_is_current,
            "ingest_failures": int(day_ingest_failures or 0),
            "delivery_failures": int(day_delivery_failures or 0),
        })

    day_count = len(days)
    return {
        "scope": {
            "user_id": user_id,
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
            "timezone": timezone,
            "days": day_count,
            "minimum_14_consecutive_days_met": day_count >= 14,
            "model_version": READINESS_MODEL_VERSION,
        },
        "metrics": {
            "valid_morning_recommendations": {
                "numerator": valid_recommendations,
                "denominator": day_count,
                "rate": _rate(valid_recommendations, day_count),
            },
            "valid_recommendations_without_physiology": {
                "numerator": valid_without_physiology,
                "denominator": valid_recommendations,
                "rate": _rate(valid_without_physiology, valid_recommendations),
            },
            "morning_recovery_response": {
                "numerator": recovery_responses,
                "denominator": recovery_eligible,
                "rate": _rate(recovery_responses, recovery_eligible),
            },
            "post_workout_rpe_completion": {
                "numerator": rpe_responses,
                "denominator": rpe_prompts,
                "rate": _rate(rpe_responses, rpe_prompts),
            },
            "signal_family_distribution": signal_distribution,
            "stale_or_missing_required_training_input": {
                "numerator": stale_or_missing_training_days,
                "denominator": day_count,
                "rate": _rate(stale_or_missing_training_days, day_count),
            },
            "recommendation_changes_after_checkin": {
                "numerator": checkin_changed,
                "denominator": checkin_observed,
                "rate": _rate(checkin_changed, checkin_observed),
            },
            "failures": {
                "ingestion": ingest_failures,
                "delivery": delivery_failures,
                "processing": None,
                "decision": None,
                "presentation": None,
            },
            "duplicate_delivery_rate": {
                "status": "not_measurable",
                "reason": "current idempotency tables store canonical delivery state, not every delivery attempt",
            },
            "api_web_telegram_consistency": {
                "status": "not_measurable",
                "reason": "API and Web read the same current state, but historical presentation observations are not persisted",
            },
        },
        "days": days,
    }


def generate_pilot_report(
    *,
    user_id: str,
    date_from: date,
    date_to: date,
    timezone: str | None = None,
) -> dict[str, Any]:
    report_timezone = timezone or settings.whatte_timezone
    params = (
        date_from,
        date_to,
        report_timezone,
        user_id,
        report_timezone,
        date_from,
        date_to,
        user_id,
        date_from,
        date_to,
        report_timezone,
        user_id,
        report_timezone,
        date_from,
        date_to,
        user_id,
        READINESS_MODEL_VERSION,
        user_id,
        user_id,
        user_id,
        user_id,
    )
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(PILOT_QUERY, params)
            rows = cur.fetchall()
    return build_pilot_report(
        user_id=user_id,
        date_from=date_from,
        date_to=date_to,
        timezone=report_timezone,
        rows=rows,
    )
