from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from backend.db import get_conn


def _compute_recovery_score_simple(
    sleep_minutes: float | None,
    resting_hr_bpm: float | None,
    hrv_daily_median_ms: float | None,
) -> float | None:
    # Простейшая baseline-free версия recovery score.
    # Это временный heuristic score, не финальная модель.
    if sleep_minutes is None and resting_hr_bpm is None and hrv_daily_median_ms is None:
        return None

    score = 50.0

    if sleep_minutes is not None:
        # 8 часов сна как условная хорошая точка.
        score += min(20.0, max(-20.0, (sleep_minutes - 480.0) / 12.0))

    if resting_hr_bpm is not None:
        # Чем ниже resting HR, тем лучше, в очень грубой форме.
        score += min(15.0, max(-15.0, (60.0 - resting_hr_bpm) * 1.2))

    if hrv_daily_median_ms is not None:
        # Чем выше HRV, тем лучше, без baseline пока очень грубо.
        score += min(15.0, max(-15.0, (hrv_daily_median_ms - 50.0) * 0.5))

    return max(0.0, min(100.0, round(score, 1)))


def recompute_health_recovery_daily_for_date(user_id: str, target_date: str) -> dict[str, Any]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Sleep for target_date
            cur.execute(
                """
                select
                    total_sleep_minutes,
                    awake_minutes,
                    rem_minutes,
                    deep_minutes
                from health_sleep_night
                where user_id = %s
                  and wake_date = %s;
                """,
                (user_id, target_date),
            )
            sleep_row = cur.fetchone()

            # Resting HR for target_date
            cur.execute(
                """
                select bpm
                from health_resting_hr_daily
                where user_id = %s
                  and date = %s;
                """,
                (user_id, target_date),
            )
            resting_hr_row = cur.fetchone()

            # HRV median for target_date
            cur.execute(
                """
                select percentile_cont(0.5) within group (order by value_ms)
                from health_hrv_sample
                where user_id = %s
                  and sample_start_at::date = %s;
                """,
                (user_id, target_date),
            )
            hrv_row = cur.fetchone()

            # Latest weight on or before target_date
            cur.execute(
                """
                select kilograms
                from health_weight_measurement
                where user_id = %s
                  and measured_at::date <= %s
                order by measured_at desc
                limit 1;
                """,
                (user_id, target_date),
            )
            weight_row = cur.fetchone()

            sleep_minutes = None
            awake_minutes = None
            rem_minutes = None
            deep_minutes = None

            if sleep_row:
                sleep_minutes, awake_minutes, rem_minutes, deep_minutes = sleep_row

            resting_hr_bpm = resting_hr_row[0] if resting_hr_row else None
            hrv_daily_median_ms = hrv_row[0] if hrv_row and hrv_row[0] is not None else None
            weight_kg = weight_row[0] if weight_row else None

            if (
                sleep_minutes is None
                and resting_hr_bpm is None
                and hrv_daily_median_ms is None
                and weight_kg is None
            ):
                raise HTTPException(
                    status_code=404,
                    detail=f"no health data found for user_id={user_id} date={target_date}",
                )

            recovery_score_simple = _compute_recovery_score_simple(
                sleep_minutes=sleep_minutes,
                resting_hr_bpm=resting_hr_bpm,
                hrv_daily_median_ms=hrv_daily_median_ms,
            )

            cur.execute(
                """
                insert into health_recovery_daily (
                    user_id,
                    date,
                    sleep_minutes,
                    awake_minutes,
                    rem_minutes,
                    deep_minutes,
                    resting_hr_bpm,
                    hrv_daily_median_ms,
                    weight_kg,
                    recovery_score_simple,
                    updated_at
                )
                values (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now()
                )
                on conflict (user_id, date) do update set
                    sleep_minutes = excluded.sleep_minutes,
                    awake_minutes = excluded.awake_minutes,
                    rem_minutes = excluded.rem_minutes,
                    deep_minutes = excluded.deep_minutes,
                    resting_hr_bpm = excluded.resting_hr_bpm,
                    hrv_daily_median_ms = excluded.hrv_daily_median_ms,
                    weight_kg = excluded.weight_kg,
                    recovery_score_simple = excluded.recovery_score_simple,
                    updated_at = now();
                """,
                (
                    user_id,
                    target_date,
                    sleep_minutes,
                    awake_minutes,
                    rem_minutes,
                    deep_minutes,
                    resting_hr_bpm,
                    hrv_daily_median_ms,
                    weight_kg,
                    recovery_score_simple,
                ),
            )
            conn.commit()

    return {
        "ok": True,
        "user_id": user_id,
        "date": target_date,
        "sleep_minutes": sleep_minutes,
        "resting_hr_bpm": resting_hr_bpm,
        "hrv_daily_median_ms": hrv_daily_median_ms,
        "weight_kg": weight_kg,
        "recovery_score_simple": recovery_score_simple,
    }