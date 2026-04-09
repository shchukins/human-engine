from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from backend.db import get_conn

import json


def _clamp(value: float, low: float, high: float) -> float:
    """Ограничивает значение диапазоном [low, high]."""
    return max(low, min(high, value))


def _compute_recovery_score_simple(
    sleep_minutes: float | None,
    resting_hr_bpm: float | None,
    hrv_daily_median_ms: float | None,
) -> float | None:
    """
    Простейшая baseline-free версия recovery score.

    Это временный heuristic score:
    - сон выше -> лучше
    - resting HR ниже -> лучше
    - HRV выше -> лучше

    Шкала результата: 0..100.
    """
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

    return _clamp(round(score, 1), 0.0, 100.0)


def _compute_recovery_score_with_baseline(
    sleep_minutes: float | None,
    hrv_today: float | None,
    rhr_today: float | None,
    hrv_baseline: float | None,
    rhr_baseline: float | None,
) -> tuple[float, dict[str, float | None]]:
    """
    Более продвинутая версия recovery score с baseline.

    Возвращает:
    - recovery_score
    - explanation dict с breakdown по компонентам
    """
    hrv_dev = None
    rhr_dev = None

    if hrv_today is not None and hrv_baseline not in (None, 0):
        hrv_dev = (hrv_today - hrv_baseline) / hrv_baseline
        hrv_score = 50.0 + 50.0 * hrv_dev
    else:
        hrv_score = 50.0

    if rhr_today is not None and rhr_baseline not in (None, 0):
        rhr_dev = (rhr_today - rhr_baseline) / rhr_baseline
        rhr_score = 50.0 - 50.0 * rhr_dev
    else:
        rhr_score = 50.0

    if sleep_minutes is not None:
        sleep_score = min(sleep_minutes / 480.0, 1.0) * 100.0
    else:
        sleep_score = 50.0

    hrv_score = _clamp(hrv_score, 0.0, 100.0)
    rhr_score = _clamp(rhr_score, 0.0, 100.0)
    sleep_score = _clamp(sleep_score, 0.0, 100.0)

    recovery_score = (
        0.4 * hrv_score
        + 0.3 * rhr_score
        + 0.3 * sleep_score
    )
    recovery_score = round(_clamp(recovery_score, 0.0, 100.0), 1)

    explanation = {
        "method": "baseline_v2",
        "sleep_minutes": sleep_minutes,
        "hrv_today": hrv_today,
        "rhr_today": rhr_today,
        "hrv_baseline": hrv_baseline,
        "rhr_baseline": rhr_baseline,
        "hrv_dev": round(hrv_dev, 4) if hrv_dev is not None else None,
        "rhr_dev": round(rhr_dev, 4) if rhr_dev is not None else None,
        "sleep_score": round(sleep_score, 1),
        "hrv_score": round(hrv_score, 1),
        "rhr_score": round(rhr_score, 1),
        "weights": {
            "hrv_score": 0.4,
            "rhr_score": 0.3,
            "sleep_score": 0.3,
        },
        "recovery_score_simple": recovery_score,
    }

    return recovery_score, explanation


def recompute_health_recovery_daily_for_date(user_id: str, target_date: str) -> dict[str, Any]:
    """
    Пересчитывает daily recovery snapshot для заданного пользователя и даты.

    Источники:
    - health_sleep_night
    - health_resting_hr_daily
    - health_hrv_sample
    - health_weight_measurement

    Результат сохраняется в:
    - health_recovery_daily
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            # 1. Забираем sleep aggregate для target_date.
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

            # 2. Забираем resting HR за target_date.
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

            # 3. Считаем median HRV за target_date.
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

            # 4. Забираем последний известный вес на target_date или раньше.
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

            # 5. Собираем daily values.
            sleep_minutes = None
            awake_minutes = None
            rem_minutes = None
            deep_minutes = None

            if sleep_row:
                sleep_minutes, awake_minutes, rem_minutes, deep_minutes = sleep_row

            resting_hr_bpm = resting_hr_row[0] if resting_hr_row else None
            hrv_daily_median_ms = hrv_row[0] if hrv_row and hrv_row[0] is not None else None
            weight_kg = weight_row[0] if weight_row else None

            # 6. Если вообще нет health data, отдаём 404.
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

            # 7. Baseline HRV: median по предыдущему окну, исключая target_date.
            cur.execute(
                """
                select percentile_cont(0.5) within group (order by value_ms)
                from health_hrv_sample
                where user_id = %s
                  and sample_start_at::date < %s::date
                  and sample_start_at::date >= (%s::date - interval '14 days');
                """,
                (user_id, target_date, target_date),
            )
            hrv_baseline_row = cur.fetchone()
            hrv_baseline = hrv_baseline_row[0] if hrv_baseline_row and hrv_baseline_row[0] is not None else None

            # 8. Baseline resting HR: median по предыдущему окну, исключая target_date.
            cur.execute(
                """
                select percentile_cont(0.5) within group (order by bpm)
                from health_resting_hr_daily
                where user_id = %s
                  and date < %s::date
                  and date >= (%s::date - interval '14 days');
                """,
                (user_id, target_date, target_date),
            )
            rhr_baseline_row = cur.fetchone()
            rhr_baseline = rhr_baseline_row[0] if rhr_baseline_row and rhr_baseline_row[0] is not None else None

            # 9. Считаем recovery score.
            # Пока сохраняем его в колонку recovery_score_simple для совместимости схемы и API.
            recovery_score_simple, recovery_explanation = _compute_recovery_score_with_baseline(
                sleep_minutes=sleep_minutes,
                hrv_today=hrv_daily_median_ms,
                rhr_today=resting_hr_bpm,
                hrv_baseline=hrv_baseline,
                rhr_baseline=rhr_baseline,
            )

            # Если по какой-то причине baseline-based score не получился,
            # используем старый простой fallback.
            if recovery_score_simple is None:
                recovery_score_simple = _compute_recovery_score_simple(
                    sleep_minutes=sleep_minutes,
                    resting_hr_bpm=resting_hr_bpm,
                    hrv_daily_median_ms=hrv_daily_median_ms,
                )
                recovery_explanation = {
                    "method": "simple_fallback",
                    "sleep_minutes": sleep_minutes,
                    "hrv_today": hrv_daily_median_ms,
                    "rhr_today": resting_hr_bpm,
                    "hrv_baseline": hrv_baseline,
                    "rhr_baseline": rhr_baseline,
                    "recovery_score_simple": recovery_score_simple,
                }

            # 10. Upsert в daily recovery table.
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
        recovery_explanation_json,
        updated_at
    )
    values (
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, now()
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
        recovery_explanation_json = excluded.recovery_explanation_json,
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
        json.dumps(recovery_explanation),
    ),
)
            conn.commit()

    # 11. Возвращаем snapshot для API/debug.
    return {
        "ok": True,
        "user_id": user_id,
        "date": target_date,
        "sleep_minutes": sleep_minutes,
        "resting_hr_bpm": resting_hr_bpm,
        "hrv_daily_median_ms": hrv_daily_median_ms,
        "weight_kg": weight_kg,
        "recovery_score_simple": recovery_score_simple,
        "hrv_baseline": hrv_baseline,
        "rhr_baseline": rhr_baseline,
        "recovery_explanation": recovery_explanation,
    }