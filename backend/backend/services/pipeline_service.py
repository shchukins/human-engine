import json
from typing import Any

from fastapi import HTTPException

from backend.db import get_conn
from backend.services.fitness_service import recompute_fitness_state
from backend.services.load_service import recompute_daily_load_all
from backend.services.metrics_service import (
    compute_deltas,
    compute_hr_zones,
    compute_power_metrics,
    compute_power_zones,
)
from backend.services.strava_auth import refresh_strava_token_if_needed
from backend.services.strava_client import (
    fetch_activity,
    fetch_activity_streams,
)


# ============================================================
# STEP 1: Fetch activity (RAW layer)
# ============================================================
# Загружаем activity из Strava и сохраняем как "источник истины".
# Это слой сырых данных, который не пересчитывается и нужен
# для воспроизводимости всех последующих расчетов.
def fetch_and_store_activity_raw(
    user_id: str,
    athlete_id: int,
    activity_id: int,
) -> dict[str, Any]:
    # Получаем валидный access_token (с refresh при необходимости)
    access_token, _, _ = refresh_strava_token_if_needed(user_id)

    # Запрашиваем activity из Strava API
    activity = fetch_activity(access_token=access_token, activity_id=activity_id)

    # Сохраняем raw activity в БД (upsert)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into strava_activity_raw (
                    user_id,
                    strava_athlete_id,
                    strava_activity_id,
                    activity_type,
                    name,
                    start_date,
                    timezone,
                    distance_m,
                    moving_time_s,
                    elapsed_time_s,
                    total_elevation_gain_m,
                    average_speed_mps,
                    max_speed_mps,
                    average_heartrate,
                    max_heartrate,
                    average_watts,
                    max_watts,
                    weighted_average_watts,
                    kilojoules,
                    trainer,
                    commute,
                    manual,
                    raw_json,
                    fetched_at,
                    updated_at,
                    is_deleted
                )
                values (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s::jsonb, now(), now(), false
                )
                on conflict (strava_activity_id) do update set
                    user_id = excluded.user_id,
                    strava_athlete_id = excluded.strava_athlete_id,
                    activity_type = excluded.activity_type,
                    name = excluded.name,
                    start_date = excluded.start_date,
                    timezone = excluded.timezone,
                    distance_m = excluded.distance_m,
                    moving_time_s = excluded.moving_time_s,
                    elapsed_time_s = excluded.elapsed_time_s,
                    total_elevation_gain_m = excluded.total_elevation_gain_m,
                    average_speed_mps = excluded.average_speed_mps,
                    max_speed_mps = excluded.max_speed_mps,
                    average_heartrate = excluded.average_heartrate,
                    max_heartrate = excluded.max_heartrate,
                    average_watts = excluded.average_watts,
                    max_watts = excluded.max_watts,
                    weighted_average_watts = excluded.weighted_average_watts,
                    kilojoules = excluded.kilojoules,
                    trainer = excluded.trainer,
                    commute = excluded.commute,
                    manual = excluded.manual,
                    raw_json = excluded.raw_json,
                    fetched_at = now(),
                    updated_at = now(),
                    is_deleted = false;
                """,
                (
                    user_id,
                    athlete_id,
                    activity_id,
                    activity.get("sport_type") or activity.get("type"),
                    activity.get("name"),
                    activity.get("start_date"),
                    activity.get("timezone"),
                    activity.get("distance"),
                    activity.get("moving_time"),
                    activity.get("elapsed_time"),
                    activity.get("total_elevation_gain"),
                    activity.get("average_speed"),
                    activity.get("max_speed"),
                    activity.get("average_heartrate"),
                    activity.get("max_heartrate"),
                    activity.get("average_watts"),
                    activity.get("max_watts"),
                    activity.get("weighted_average_watts"),
                    activity.get("kilojoules"),
                    activity.get("trainer"),
                    activity.get("commute"),
                    activity.get("manual"),
                    json.dumps(activity),
                ),
            )
            conn.commit()

    return activity


# ============================================================
# STEP 2: Fetch streams (time series layer)
# ============================================================
# Streams — это временные ряды (watts, hr, distance и т.д.),
# которые используются для расчета метрик (NP, TSS, зоны).
def fetch_and_store_activity_streams(user_id: str, activity_id: int) -> dict[str, Any]:
    access_token, _, _ = refresh_strava_token_if_needed(user_id)
    streams = fetch_activity_streams(access_token=access_token, activity_id=activity_id)

    saved = 0

    with get_conn() as conn:
        with conn.cursor() as cur:
            for stream_type, stream_payload in streams.items():
                cur.execute(
                    """
                    insert into strava_activity_stream_raw (
                        strava_activity_id,
                        stream_type,
                        series_type,
                        resolution,
                        original_size,
                        data_json,
                        fetched_at
                    )
                    values (%s, %s, %s, %s, %s, %s::jsonb, now())
                    on conflict (strava_activity_id, stream_type) do update set
                        series_type = excluded.series_type,
                        resolution = excluded.resolution,
                        original_size = excluded.original_size,
                        data_json = excluded.data_json,
                        fetched_at = now();
                    """,
                    (
                        activity_id,
                        stream_type,
                        stream_payload.get("series_type"),
                        stream_payload.get("resolution"),
                        stream_payload.get("original_size"),
                        json.dumps(stream_payload),
                    ),
                )
                saved += 1

            conn.commit()

    return {
        "streams_saved": saved,
        "stream_types": list(streams.keys()),
    }


# ============================================================
# STEP 3: Compute metrics (physics + physiology)
# ============================================================
# Здесь происходит ключевая логика:
# - NP (normalized power)
# - IF (intensity factor)
# - TSS (нагрузка)
# - зоны мощности и пульса
def compute_and_store_activity_metrics(activity_id: int) -> dict[str, Any]:
    # --- загрузка raw activity ---
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select ...
                """,
                (activity_id,),
            )
            raw_row = cur.fetchone()

            if not raw_row:
                raise HTTPException(
                    status_code=404,
                    detail=f"activity not found in strava_activity_raw: {activity_id}",
                )

            (
                user_id,
                strava_activity_id,
                moving_time_s,
                elapsed_time_s,
                distance_m,
                elevation_gain_m,
                avg_speed_mps,
                max_speed_mps,
                avg_heartrate,
                max_heartrate,
                avg_power,
                max_power,
                weighted_avg_power,
                work_kj,
            ) = raw_row

            # --- загрузка тренировочного профиля пользователя ---
            # FTP и границы зон нужны для расчета нагрузки и распределения по зонам
            cur.execute(
                """
                select ...
                """,
                (user_id,),
            )
            profile_row = cur.fetchone()

            if not profile_row:
                raise HTTPException(
                    status_code=404,
                    detail=f"user_training_profile not found for user_id={user_id}",
                )

            (
                ftp_watts,
                hr_max,
                power_z1_upper,
                power_z2_upper,
                power_z3_upper,
                power_z4_upper,
                power_z5_upper,
                power_z6_upper,
                hr_z1_upper,
                hr_z2_upper,
                hr_z3_upper,
                hr_z4_upper,
            ) = profile_row

            # --- загрузка streams ---
            cur.execute(
                """
                select stream_type, data_json
                from strava_activity_stream_raw
                where strava_activity_id = %s;
                """,
                (activity_id,),
            )
            stream_rows = cur.fetchall()

    # Преобразуем streams в удобный словарь
    streams = {stream_type: data_json for stream_type, data_json in stream_rows}

    time_stream = streams.get("time", {}).get("data", [])
    watts_stream = streams.get("watts", {}).get("data", [])
    hr_stream = streams.get("heartrate", {}).get("data", [])

    # Без time_stream невозможно корректно посчитать нагрузку
    if not time_stream:
        raise HTTPException(
            status_code=400,
            detail=f"time stream not found for activity_id={activity_id}",
        )

    # --- вычисление дельт времени ---
    # нужно для интеграции (время в зонах, NP и т.д.)
    deltas = compute_deltas(time_stream)

    # --- расчет ключевых power-метрик ---
    power_metrics = compute_power_metrics(
        watts_stream=watts_stream,
        avg_power=avg_power,
        ftp_watts=ftp_watts,
        elapsed_time_s=elapsed_time_s,
    )

    normalized_power = power_metrics["normalized_power"]
    intensity_factor = power_metrics["intensity_factor"]
    variability_index = power_metrics["variability_index"]
    tss = power_metrics["tss"]

    # --- распределение по зонам мощности ---
    power_zones = compute_power_zones(
        watts_stream=watts_stream,
        deltas=deltas,
        power_z1_upper=power_z1_upper,
        power_z2_upper=power_z2_upper,
        power_z3_upper=power_z3_upper,
        power_z4_upper=power_z4_upper,
        power_z5_upper=power_z5_upper,
        power_z6_upper=power_z6_upper,
    )

    # --- распределение по зонам пульса ---
    hr_zones = compute_hr_zones(
        hr_stream=hr_stream,
        deltas=deltas,
        hr_z1_upper=hr_z1_upper,
        hr_z2_upper=hr_z2_upper,
        hr_z3_upper=hr_z3_upper,
        hr_z4_upper=hr_z4_upper,
    )

    # Метаданные расчета (версия pipeline и входные параметры)
    metrics_json = {
        "source": "pipeline_service_v1",
        "streams_present": list(streams.keys()),
        "ftp_watts": ftp_watts,
        "hr_max": hr_max,
    }

    # --- сохранение метрик ---
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into activity_metrics ...
                """,
                (
                    user_id,
                    strava_activity_id,
                    elapsed_time_s,
                    moving_time_s,
                    distance_m,
                    elevation_gain_m,
                    avg_speed_mps,
                    max_speed_mps,
                    avg_heartrate,
                    max_heartrate,
                    avg_power,
                    max_power,
                    weighted_avg_power,
                    normalized_power,
                    intensity_factor,
                    variability_index,
                    work_kj,
                    tss,
                    power_zones["z1"],
                    power_zones["z2"],
                    power_zones["z3"],
                    power_zones["z4"],
                    power_zones["z5"],
                    power_zones["z6"],
                    power_zones["z7"],
                    hr_zones["z1"],
                    hr_zones["z2"],
                    hr_zones["z3"],
                    hr_zones["z4"],
                    hr_zones["z5"],
                    json.dumps(metrics_json),
                ),
            )
            conn.commit()

    return {
        "ok": True,
        "activity_id": activity_id,
        "user_id": user_id,
        "normalized_power": normalized_power,
        "intensity_factor": intensity_factor,
        "variability_index": variability_index,
        "tss": tss,
        "power_zones_s": power_zones,
        "hr_zones_s": hr_zones,
    }


# ============================================================
# FULL PIPELINE (end-to-end)
# ============================================================
# Это главный orchestrator:
# 1. raw activity
# 2. streams
# 3. metrics
# 4. load (TSS aggregation)
# 5. fitness (CTL/ATL/TSB)
def process_activity_pipeline(
    user_id: str,
    athlete_id: int,
    activity_id: int,
) -> dict[str, Any]:
    activity = fetch_and_store_activity_raw(
        user_id=user_id,
        athlete_id=athlete_id,
        activity_id=activity_id,
    )

    streams_result = fetch_and_store_activity_streams(
        user_id=user_id,
        activity_id=activity_id,
    )

    metrics_result = compute_and_store_activity_metrics(activity_id=activity_id)

    # --- обновление агрегированных метрик ---
    # Load = дневной TSS
    load_result = recompute_daily_load_all(user_id)

    # Fitness = CTL/ATL/TSB (адаптация организма)
    fitness_result = recompute_fitness_state(user_id)

    return {
        "ok": True,
        "user_id": user_id,
        "activity_id": activity_id,
        "name": activity.get("name"),
        "streams_saved": streams_result["streams_saved"],
        "tss": metrics_result["tss"],
        "load_days_processed": load_result["days_processed"],
        "fitness_days_processed": fitness_result["days_processed"],
        "last_freshness_signal": fitness_result["last_freshness_signal"],
    }
