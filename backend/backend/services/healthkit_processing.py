from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from backend.db import get_conn


def process_latest_healthkit_raw(user_id: str) -> dict[str, Any]:
    # Берем последний raw payload пользователя и раскладываем по нормализованным таблицам.
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select payload_json
                from healthkit_ingest_raw
                where user_id = %s
                order by received_at desc, id desc
                limit 1;
                """,
                (user_id,),
            )
            row = cur.fetchone()

            if not row:
                raise HTTPException(
                    status_code=404,
                    detail=f"healthkit raw payload not found for user_id={user_id}",
                )

            payload = row[0]

            sleep_nights = payload.get("sleepNights", [])
            resting_hr_daily = payload.get("restingHeartRateDaily", [])
            hrv_samples = payload.get("hrvSamples", [])
            latest_weight = payload.get("latestWeight")

            sleep_count = 0
            resting_hr_count = 0
            hrv_count = 0
            weight_count = 0

            for item in sleep_nights:
                cur.execute(
                    """
                    insert into health_sleep_night (
                        user_id,
                        wake_date,
                        sleep_start_at,
                        sleep_end_at,
                        total_sleep_minutes,
                        awake_minutes,
                        core_minutes,
                        rem_minutes,
                        deep_minutes,
                        in_bed_minutes,
                        updated_at
                    )
                    values (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now()
                    )
                    on conflict (user_id, wake_date) do update set
                        sleep_start_at = excluded.sleep_start_at,
                        sleep_end_at = excluded.sleep_end_at,
                        total_sleep_minutes = excluded.total_sleep_minutes,
                        awake_minutes = excluded.awake_minutes,
                        core_minutes = excluded.core_minutes,
                        rem_minutes = excluded.rem_minutes,
                        deep_minutes = excluded.deep_minutes,
                        in_bed_minutes = excluded.in_bed_minutes,
                        updated_at = now();
                    """,
                    (
                        user_id,
                        item["wakeDate"],
                        item["sleepStart"],
                        item["sleepEnd"],
                        item["totalSleepMinutes"],
                        item["awakeMinutes"],
                        item["coreMinutes"],
                        item["remMinutes"],
                        item["deepMinutes"],
                        item.get("inBedMinutes"),
                    ),
                )
                sleep_count += 1

            for item in resting_hr_daily:
                cur.execute(
                    """
                    insert into health_resting_hr_daily (
                        user_id,
                        date,
                        bpm,
                        updated_at
                    )
                    values (
                        %s, %s, %s, now()
                    )
                    on conflict (user_id, date) do update set
                        bpm = excluded.bpm,
                        updated_at = now();
                    """,
                    (
                        user_id,
                        item["date"],
                        item["bpm"],
                    ),
                )
                resting_hr_count += 1

            for item in hrv_samples:
                cur.execute(
                    """
                    insert into health_hrv_sample (
                        user_id,
                        sample_start_at,
                        value_ms
                    )
                    values (
                        %s, %s, %s
                    )
                    on conflict (user_id, sample_start_at) do update set
                        value_ms = excluded.value_ms;
                    """,
                    (
                        user_id,
                        item["startAt"],
                        item["valueMs"],
                    ),
                )
                hrv_count += 1

            if latest_weight is not None:
                cur.execute(
                    """
                    insert into health_weight_measurement (
                        user_id,
                        measured_at,
                        kilograms
                    )
                    values (
                        %s, %s, %s
                    )
                    on conflict (user_id, measured_at) do update set
                        kilograms = excluded.kilograms;
                    """,
                    (
                        user_id,
                        latest_weight["measuredAt"],
                        latest_weight["kilograms"],
                    ),
                )
                weight_count = 1

            conn.commit()

    return {
        "ok": True,
        "user_id": user_id,
        "sleep_nights_processed": sleep_count,
        "resting_hr_processed": resting_hr_count,
        "hrv_processed": hrv_count,
        "weight_processed": weight_count,
    }