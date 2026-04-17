from __future__ import annotations

import math
from typing import Any

from backend.db import get_conn


TAU_FITNESS = 40.0
TAU_FATIGUE_FAST = 4.0
TAU_FATIGUE_SLOW = 9.0

WEIGHT_FATIGUE_FAST = 0.65
WEIGHT_FATIGUE_SLOW = 0.35


def _transform_tss_nonlinear(tss: float | None) -> float:
    return tss or 0.0


def recompute_load_state_daily_v2(user_id: str) -> dict[str, Any]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                with source_dates as (
                    select date
                    from daily_training_load
                    where user_id = %s

                    union

                    select date
                    from health_recovery_daily
                    where user_id = %s
                ),
                bounds as (
                    select
                        min(date) as min_date,
                        max(date) as max_date
                    from source_dates
                ),
                calendar as (
                    select generate_series(
                        b.min_date,
                        b.max_date,
                        interval '1 day'
                    )::date as date
                    from bounds b
                    where b.min_date is not null
                      and b.max_date is not null
                )
                select
                    c.date,
                    coalesce(dtl.tss, 0) as tss
                from calendar c
                left join daily_training_load dtl
                    on dtl.user_id = %s
                   and dtl.date = c.date
                order by c.date asc;
                """,
                (user_id, user_id, user_id),
            )
            rows = cur.fetchall()

            if not rows:
                return {
                    "ok": True,
                    "user_id": user_id,
                    "days_processed": 0,
                    "last_date": None,
                }

            fitness_prev = 0.0
            fatigue_fast_prev = 0.0
            fatigue_slow_prev = 0.0

            processed = 0
            last_date = None

            for row_date, tss in rows:
                load_input_nonlinear = _transform_tss_nonlinear(tss)

                fitness = fitness_prev + (
                    load_input_nonlinear - fitness_prev
                ) / TAU_FITNESS
                fatigue_fast = fatigue_fast_prev + (
                    load_input_nonlinear - fatigue_fast_prev
                ) / TAU_FATIGUE_FAST
                fatigue_slow = fatigue_slow_prev + (
                    load_input_nonlinear - fatigue_slow_prev
                ) / TAU_FATIGUE_SLOW

                fatigue_total = (
                    WEIGHT_FATIGUE_FAST * fatigue_fast
                    + WEIGHT_FATIGUE_SLOW * fatigue_slow
                )
                freshness = fitness - fatigue_total

                cur.execute(
                    """
                    insert into load_state_daily_v2 (
                        user_id,
                        date,
                        tss,
                        load_input_nonlinear,
                        fitness,
                        fatigue_fast,
                        fatigue_slow,
                        fatigue_total,
                        freshness,
                        version,
                        updated_at
                    )
                    values (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, 'v2', now()
                    )
                    on conflict (user_id, date, version) do update set
                        tss = excluded.tss,
                        load_input_nonlinear = excluded.load_input_nonlinear,
                        fitness = excluded.fitness,
                        fatigue_fast = excluded.fatigue_fast,
                        fatigue_slow = excluded.fatigue_slow,
                        fatigue_total = excluded.fatigue_total,
                        freshness = excluded.freshness,
                        updated_at = now();
                    """,
                    (
                        user_id,
                        row_date,
                        tss,
                        load_input_nonlinear,
                        fitness,
                        fatigue_fast,
                        fatigue_slow,
                        fatigue_total,
                        freshness,
                    ),
                )

                fitness_prev = fitness
                fatigue_fast_prev = fatigue_fast
                fatigue_slow_prev = fatigue_slow

                processed += 1
                last_date = row_date

            conn.commit()

    return {
        "ok": True,
        "user_id": user_id,
        "days_processed": processed,
        "last_date": str(last_date) if last_date else None,
        "last_fitness": fitness_prev,
        "last_fatigue_fast": fatigue_fast_prev,
        "last_fatigue_slow": fatigue_slow_prev,
        "last_freshness": freshness,
    }
