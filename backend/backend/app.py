from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import psycopg
from fastapi import FastAPI, HTTPException, Query, Request
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
import requests

class Settings(BaseSettings):
    database_url: str = Field(alias="DATABASE_URL")
    strava_verify_token: str = Field(alias="STRAVA_VERIFY_TOKEN")
    strava_client_id: str = Field(alias="STRAVA_CLIENT_ID")
    strava_client_secret: str = Field(alias="STRAVA_CLIENT_SECRET")

    class Config:
        env_file = ".env"


settings = Settings()

app = FastAPI(title="Human Engine API", version="0.1.0")


class EventIn(BaseModel):
    source: str = Field(min_length=1, examples=["strava", "healthkit"])
    event_type: str = Field(min_length=1, examples=["webhook", "sleep_sync"])
    payload: dict[str, Any]


class EventOut(BaseModel):
    id: int
    source: str
    event_type: str
    payload: dict[str, Any]
    received_at: datetime

class StravaWebhookChallenge(BaseModel):
    hub_mode: str = Field(alias="hub.mode")
    hub_challenge: str = Field(alias="hub.challenge")
    hub_verify_token: str = Field(alias="hub.verify_token")


class StravaWebhookChallengeResponse(BaseModel):
    hub_challenge: str = Field(alias="hub.challenge")


def get_conn():
    return psycopg.connect(settings.database_url)


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/dbz")
def dbz():
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                cur.fetchone()
        return {"db": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"db error: {e}")


@app.post("/events", response_model=EventOut)
def create_event(event: EventIn):
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO events (source, event_type, payload)
                    VALUES (%s, %s, %s::jsonb)
                    RETURNING id, source, event_type, payload, received_at;
                    """,
                    (event.source, event.event_type, json.dumps(event.payload)),
                )
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=500, detail="insert failed")
                conn.commit()

        return {
            "id": row[0],
            "source": row[1],
            "event_type": row[2],
            "payload": row[3],
            "received_at": row[4],
        }
    except psycopg.Error as e:
        raise HTTPException(status_code=500, detail=f"db error: {e}")


@app.get("/events", response_model=list[EventOut])
def list_events(limit: int = Query(default=20, ge=1, le=200)):
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, source, event_type, payload, received_at
                    FROM events
                    ORDER BY received_at DESC
                    LIMIT %s;
                    """,
                    (limit,),
                )
                rows = cur.fetchall()

        return [
            {
                "id": r[0],
                "source": r[1],
                "event_type": r[2],
                "payload": r[3],
                "received_at": r[4],
            }
            for r in rows
        ]
    except psycopg.Error as e:
        raise HTTPException(status_code=500, detail=f"db error: {e}")
    
    
@app.get("/strava/webhook", response_model=StravaWebhookChallengeResponse)
def strava_webhook_verify(
    hub_mode: str = Query(alias="hub.mode"),
    hub_challenge: str = Query(alias="hub.challenge"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
):
    # Strava ожидает JSON: {"hub.challenge": "<value>"}
    if hub_verify_token != settings.strava_verify_token:
        raise HTTPException(status_code=401, detail="invalid verify token")
    return {"hub.challenge": hub_challenge}


@app.post("/strava/webhook")
async def strava_webhook_receive(request: Request):
    payload = await request.json()

    aspect_type = payload.get("aspect_type", "webhook")
    object_type = payload.get("object_type")
    object_id = payload.get("object_id")
    owner_id = payload.get("owner_id")
    subscription_id = payload.get("subscription_id")
    updates = payload.get("updates")
    event_time_unix = payload.get("event_time")

    if not object_type or object_id is None or owner_id is None or event_time_unix is None:
        raise HTTPException(status_code=400, detail="invalid strava webhook payload")

    dedupe_key = (
        f"strava:{subscription_id}:{owner_id}:"
        f"{object_type}:{object_id}:{aspect_type}:{event_time_unix}"
    )

    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    insert into strava_webhook_event (
                        subscription_id,
                        owner_id,
                        object_type,
                        object_id,
                        aspect_type,
                        event_time,
                        updates,
                        payload,
                        dedupe_key
                    )
                    values (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        to_timestamp(%s),
                        %s::jsonb,
                        %s::jsonb,
                        %s
                    )
                    on conflict (dedupe_key) do nothing
                    returning id;
                    """,
                    (
                        subscription_id,
                        owner_id,
                        object_type,
                        object_id,
                        aspect_type,
                        event_time_unix,
                        json.dumps(updates) if updates is not None else None,
                        json.dumps(payload),
                        dedupe_key,
                    ),
                )
                webhook_row = cur.fetchone()
                webhook_event_id = webhook_row[0] if webhook_row else None

                if (
                    webhook_event_id is not None
                    and object_type == "activity"
                    and aspect_type in ("create", "update")
                ):
                    cur.execute(
                        """
                        select user_id
                        from user_strava_connection
                        where strava_athlete_id = %s;
                        """,
                        (owner_id,),
                    )
                    user_row = cur.fetchone()

                    if user_row:
                        user_id = user_row[0]
                        cur.execute(
                            """
                            insert into strava_activity_ingest_job (
                                webhook_event_id,
                                user_id,
                                strava_athlete_id,
                                strava_activity_id,
                                reason,
                                status
                            )
                            values (%s, %s, %s, %s, %s, 'pending')
                            on conflict do nothing
                            returning id;
                            """,
                            (
                                webhook_event_id,
                                user_id,
                                owner_id,
                                object_id,
                                f"webhook_{aspect_type}",
                            ),
                        )

                conn.commit()

        return {"ok": True, "event_id": webhook_event_id}
    except psycopg.Error as e:
        raise HTTPException(status_code=500, detail=f"db error: {e}")

def refresh_strava_token_if_needed(user_id: str) -> tuple[str, str, int]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select access_token, refresh_token, extract(epoch from expires_at)::bigint
                from user_strava_connection
                where user_id = %s;
                """,
                (user_id,),
            )
            row = cur.fetchone()

            if not row:
                raise HTTPException(status_code=404, detail=f"strava connection not found for user_id={user_id}")

            access_token, refresh_token, expires_at_unix = row

    now_unix = int(datetime.utcnow().timestamp())

    # Обновляем токен, если он уже истек или истечет меньше чем через 5 минут
    if expires_at_unix > now_unix + 300:
        return access_token, refresh_token, expires_at_unix

    response = requests.post(
        "https://www.strava.com/oauth/token",
        data={
            "client_id": settings.strava_client_id,
            "client_secret": settings.strava_client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
        timeout=30,
    )

    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"strava token refresh failed: {response.status_code}",
        )

    token_data = response.json()

    new_access_token = token_data["access_token"]
    new_refresh_token = token_data["refresh_token"]
    new_expires_at_unix = token_data["expires_at"]

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                update user_strava_connection
                set access_token = %s,
                    refresh_token = %s,
                    expires_at = to_timestamp(%s),
                    updated_at = now()
                where user_id = %s;
                """,
                (
                    new_access_token,
                    new_refresh_token,
                    new_expires_at_unix,
                    user_id,
                ),
            )
            conn.commit()

    return new_access_token, new_refresh_token, new_expires_at_unix

def process_one_strava_ingest_job() -> dict[str, Any]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select
                    j.id,
                    j.user_id,
                    j.strava_athlete_id,
                    j.strava_activity_id
                from strava_activity_ingest_job j
                where j.status = 'pending'
                order by j.scheduled_at asc
                limit 1;
                """
            )

            row = cur.fetchone()

            if not row:
                return {"ok": True, "message": "no pending jobs"}

            job_id, user_id, athlete_id, activity_id = row

            cur.execute(
                """
                update strava_activity_ingest_job
                set status = 'running',
                    started_at = now(),
                    attempt_count = attempt_count + 1
                where id = %s;
                """,
                (job_id,),
            )

            conn.commit()

    access_token, _, _ = refresh_strava_token_if_needed(user_id)

    response = requests.get(
        f"https://www.strava.com/api/v3/activities/{activity_id}",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    )

    if response.status_code != 200:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    update strava_activity_ingest_job
                    set status = 'failed',
                        finished_at = now(),
                        last_error = %s
                    where id = %s;
                    """,
                    (f"strava api status {response.status_code}: {response.text[:500]}", job_id),
                )
                conn.commit()

        raise HTTPException(
            status_code=502,
            detail=f"strava api error {response.status_code}",
        )

    activity = response.json()

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

            cur.execute(
                """
                update strava_activity_ingest_job
                set status = 'done',
                    finished_at = now(),
                    last_error = null
                where id = %s;
                """,
                (job_id,),
            )
            conn.commit()

    return {
        "ok": True,
        "job_id": job_id,
        "activity_id": activity_id,
        "name": activity.get("name"),
    }



@app.post("/debug/strava/fetch-one")
def debug_strava_fetch_one():
    try:
        return process_one_strava_ingest_job()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"http error: {e}")
    except psycopg.Error as e:
        raise HTTPException(status_code=500, detail=f"db error: {e}")

@app.post("/debug/strava/fetch-streams/{activity_id}")
def debug_strava_fetch_streams(activity_id: int):
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select user_id, strava_athlete_id
                    from strava_activity_raw
                    where strava_activity_id = %s;
                    """,
                    (activity_id,),
                )
                row = cur.fetchone()

                if not row:
                    raise HTTPException(
                        status_code=404,
                        detail=f"activity not found in strava_activity_raw: {activity_id}",
                    )

                user_id, athlete_id = row

        access_token, _, _ = refresh_strava_token_if_needed(user_id)

        response = requests.get(
            f"https://www.strava.com/api/v3/activities/{activity_id}/streams",
            params={
                "keys": "time,distance,latlng,altitude,velocity_smooth,heartrate,cadence,watts,temp,grade_smooth",
                "key_by_type": "true",
            },
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=30,
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"strava streams api error {response.status_code}: {response.text[:300]}",
            )

        streams = response.json()

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
            "ok": True,
            "activity_id": activity_id,
            "user_id": user_id,
            "streams_saved": saved,
            "stream_types": list(streams.keys()),
        }

    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"http error: {e}")
    except psycopg.Error as e:
        raise HTTPException(status_code=500, detail=f"db error: {e}")

@app.post("/debug/metrics/compute/{activity_id}")
def debug_compute_activity_metrics(activity_id: int):
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select
                        user_id,
                        strava_activity_id,
                        moving_time_s,
                        elapsed_time_s,
                        distance_m,
                        total_elevation_gain_m,
                        average_speed_mps,
                        max_speed_mps,
                        average_heartrate,
                        max_heartrate,
                        average_watts,
                        max_watts,
                        weighted_average_watts,
                        kilojoules
                    from strava_activity_raw
                    where strava_activity_id = %s;
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

                cur.execute(
                    """
                    select
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
                        hr_z4_upper
                    from user_training_profile
                    where user_id = %s
                    order by effective_from desc
                    limit 1;
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

                cur.execute(
                    """
                    select stream_type, data_json
                    from strava_activity_stream_raw
                    where strava_activity_id = %s;
                    """,
                    (activity_id,),
                )
                stream_rows = cur.fetchall()

        streams = {}
        for stream_type, data_json in stream_rows:
            streams[stream_type] = data_json

        time_stream = streams.get("time", {}).get("data", [])
        watts_stream = streams.get("watts", {}).get("data", [])
        hr_stream = streams.get("heartrate", {}).get("data", [])

        if not time_stream:
            raise HTTPException(
                status_code=400,
                detail=f"time stream not found for activity_id={activity_id}",
            )

        def compute_deltas(times: list[int]) -> list[int]:
            if len(times) < 2:
                return [0] * len(times)

            deltas: list[int] = []
            for i in range(len(times)):
                if i == 0:
                    delta = times[1] - times[0]
                else:
                    delta = times[i] - times[i - 1]

                if delta < 0:
                    delta = 0
                deltas.append(delta)

            return deltas

        def rolling_mean(values: list[float], window: int) -> list[float]:
            if not values:
                return []

            result: list[float] = []
            running_sum = 0.0

            for i, value in enumerate(values):
                running_sum += value

                if i >= window:
                    running_sum -= values[i - window]

                current_window = min(i + 1, window)
                result.append(running_sum / current_window)

            return result

        deltas = compute_deltas(time_stream)

        normalized_power = None
        intensity_factor = None
        variability_index = None
        tss = None

        if watts_stream and ftp_watts and ftp_watts > 0:
            watts_values = [float(v) if v is not None else 0.0 for v in watts_stream]
            rolling_30s = rolling_mean(watts_values, 30)

            if rolling_30s:
                fourth_power_mean = sum(v ** 4 for v in rolling_30s) / len(rolling_30s)
                normalized_power = fourth_power_mean ** 0.25

                if avg_power and avg_power > 0:
                    variability_index = normalized_power / avg_power

                intensity_factor = normalized_power / ftp_watts

                if elapsed_time_s and elapsed_time_s > 0:
                    tss = (elapsed_time_s * normalized_power * intensity_factor) / (ftp_watts * 3600) * 100

        power_zones = {
            "z1": 0,
            "z2": 0,
            "z3": 0,
            "z4": 0,
            "z5": 0,
            "z6": 0,
            "z7": 0,
        }

        if watts_stream:
            for i in range(min(len(watts_stream), len(deltas))):
                value = watts_stream[i]
                delta = deltas[i]

                if value is None:
                    continue

                if value <= power_z1_upper:
                    power_zones["z1"] += delta
                elif value <= power_z2_upper:
                    power_zones["z2"] += delta
                elif value <= power_z3_upper:
                    power_zones["z3"] += delta
                elif value <= power_z4_upper:
                    power_zones["z4"] += delta
                elif value <= power_z5_upper:
                    power_zones["z5"] += delta
                elif value <= power_z6_upper:
                    power_zones["z6"] += delta
                else:
                    power_zones["z7"] += delta

        hr_zones = {
            "z1": 0,
            "z2": 0,
            "z3": 0,
            "z4": 0,
            "z5": 0,
        }

        if hr_stream:
            for i in range(min(len(hr_stream), len(deltas))):
                value = hr_stream[i]
                delta = deltas[i]

                if value is None:
                    continue

                if hr_z1_upper is not None and value <= hr_z1_upper:
                    hr_zones["z1"] += delta
                elif hr_z2_upper is not None and value <= hr_z2_upper:
                    hr_zones["z2"] += delta
                elif hr_z3_upper is not None and value <= hr_z3_upper:
                    hr_zones["z3"] += delta
                elif hr_z4_upper is not None and value <= hr_z4_upper:
                    hr_zones["z4"] += delta
                else:
                    hr_zones["z5"] += delta

        metrics_json = {
            "source": "debug_metrics_v1",
            "streams_present": list(streams.keys()),
            "ftp_watts": ftp_watts,
            "hr_max": hr_max,
        }

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    insert into activity_metrics (
                        user_id,
                        strava_activity_id,
                        version,
                        duration_s,
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
                        time_in_power_z1_s,
                        time_in_power_z2_s,
                        time_in_power_z3_s,
                        time_in_power_z4_s,
                        time_in_power_z5_s,
                        time_in_power_z6_s,
                        time_in_power_z7_s,
                        time_in_hr_z1_s,
                        time_in_hr_z2_s,
                        time_in_hr_z3_s,
                        time_in_hr_z4_s,
                        time_in_hr_z5_s,
                        raw_json,
                        computed_at
                    )
                    values (
                        %s, %s, 'v1', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        %s::jsonb, now()
                    )
                    on conflict (strava_activity_id, version) do update set
                        user_id = excluded.user_id,
                        duration_s = excluded.duration_s,
                        moving_time_s = excluded.moving_time_s,
                        distance_m = excluded.distance_m,
                        elevation_gain_m = excluded.elevation_gain_m,
                        avg_speed_mps = excluded.avg_speed_mps,
                        max_speed_mps = excluded.max_speed_mps,
                        avg_heartrate = excluded.avg_heartrate,
                        max_heartrate = excluded.max_heartrate,
                        avg_power = excluded.avg_power,
                        max_power = excluded.max_power,
                        weighted_avg_power = excluded.weighted_avg_power,
                        normalized_power = excluded.normalized_power,
                        intensity_factor = excluded.intensity_factor,
                        variability_index = excluded.variability_index,
                        work_kj = excluded.work_kj,
                        tss = excluded.tss,
                        time_in_power_z1_s = excluded.time_in_power_z1_s,
                        time_in_power_z2_s = excluded.time_in_power_z2_s,
                        time_in_power_z3_s = excluded.time_in_power_z3_s,
                        time_in_power_z4_s = excluded.time_in_power_z4_s,
                        time_in_power_z5_s = excluded.time_in_power_z5_s,
                        time_in_power_z6_s = excluded.time_in_power_z6_s,
                        time_in_power_z7_s = excluded.time_in_power_z7_s,
                        time_in_hr_z1_s = excluded.time_in_hr_z1_s,
                        time_in_hr_z2_s = excluded.time_in_hr_z2_s,
                        time_in_hr_z3_s = excluded.time_in_hr_z3_s,
                        time_in_hr_z4_s = excluded.time_in_hr_z4_s,
                        time_in_hr_z5_s = excluded.time_in_hr_z5_s,
                        raw_json = excluded.raw_json,
                        computed_at = now();
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

    except psycopg.Error as e:
        raise HTTPException(status_code=500, detail=f"db error: {e}")

@app.post("/debug/load/compute-day/{user_id}/{date_str}")
def debug_compute_daily_load(user_id: str, date_str: str):
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:

                cur.execute(
                    """
                    select
                        count(*),
                        coalesce(sum(duration_s),0),
                        coalesce(sum(distance_m),0),
                        coalesce(sum(elevation_gain_m),0),
                        coalesce(sum(work_kj),0),
                        coalesce(sum(tss),0)
                    from activity_metrics
                    where user_id = %s
                      and date(computed_at) = %s::date;
                    """,
                    (user_id, date_str),
                )

                row = cur.fetchone()

                (
                    activities_count,
                    duration_s,
                    distance_m,
                    elevation_gain_m,
                    work_kj,
                    tss,
                ) = row

                cur.execute(
                    """
                    insert into daily_training_load (
                        user_id,
                        date,
                        activities_count,
                        duration_s,
                        distance_m,
                        elevation_gain_m,
                        work_kj,
                        tss,
                        computed_at
                    )
                    values (%s,%s,%s,%s,%s,%s,%s,%s,now())
                    on conflict (user_id, date) do update set
                        activities_count = excluded.activities_count,
                        duration_s = excluded.duration_s,
                        distance_m = excluded.distance_m,
                        elevation_gain_m = excluded.elevation_gain_m,
                        work_kj = excluded.work_kj,
                        tss = excluded.tss,
                        computed_at = now();
                    """,
                    (
                        user_id,
                        date_str,
                        activities_count,
                        duration_s,
                        distance_m,
                        elevation_gain_m,
                        work_kj,
                        tss,
                    ),
                )

                conn.commit()

        return {
            "ok": True,
            "user_id": user_id,
            "date": date_str,
            "activities": activities_count,
            "tss": tss,
        }

    except psycopg.Error as e:
        raise HTTPException(status_code=500, detail=f"db error: {e}")


@app.post("/debug/fitness/recompute/{user_id}")
def debug_recompute_fitness_state(user_id: str):
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    with bounds as (
                        select min(date) as min_date, max(date) as max_date
                        from daily_training_load
                        where user_id = %s
                    ),
                    calendar as (
                        select generate_series(
                            (select min_date from bounds),
                            (select max_date from bounds),
                            interval '1 day'
                        )::date as date
                    )
                    select
                        c.date,
                        coalesce(d.tss, 0) as daily_tss
                    from calendar c
                    left join daily_training_load d
                      on d.user_id = %s
                     and d.date = c.date
                    order by c.date asc;
                    """,
                    (user_id, user_id),
                )
                rows = cur.fetchall()

                if not rows:
                    raise HTTPException(
                        status_code=404,
                        detail=f"daily_training_load not found for user_id={user_id}",
                    )

        fitness_tau = 42.0
        fatigue_tau = 7.0

        fitness_signal = 0.0
        fatigue_signal = 0.0

        results = []

        for row in rows:
            day, daily_tss = row
            daily_tss = float(daily_tss or 0)

            fitness_signal = fitness_signal + (daily_tss - fitness_signal) / fitness_tau
            fatigue_signal = fatigue_signal + (daily_tss - fatigue_signal) / fatigue_tau
            freshness_signal = fitness_signal - fatigue_signal

            results.append(
                (
                    user_id,
                    day,
                    daily_tss,
                    fitness_signal,
                    fatigue_signal,
                    freshness_signal,
                )
            )

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    delete from daily_fitness_state
                    where user_id = %s
                      and model_version = 'v1';
                    """,
                    (user_id,),
                )

                for item in results:
                    cur.execute(
                        """
                        insert into daily_fitness_state (
                            user_id,
                            date,
                            daily_tss,
                            fitness_signal,
                            fatigue_signal,
                            freshness_signal,
                            model_version,
                            computed_at
                        )
                        values (%s, %s, %s, %s, %s, %s, 'v1', now());
                        """,
                        item,
                    )

                conn.commit()

        last_day = results[-1]

        return {
            "ok": True,
            "user_id": user_id,
            "days_processed": len(results),
            "last_date": str(last_day[1]),
            "last_daily_tss": last_day[2],
            "last_fitness_signal": last_day[3],
            "last_fatigue_signal": last_day[4],
            "last_freshness_signal": last_day[5],
        }

    except psycopg.Error as e:
        raise HTTPException(status_code=500, detail=f"db error: {e}")


@app.get("/debug/strava/list-activities/{user_id}")
def debug_list_strava_activities(user_id: str, per_page: int = 30, page: int = 1):
    try:
        access_token, _, _ = refresh_strava_token_if_needed(user_id)

        response = requests.get(
            "https://www.strava.com/api/v3/athlete/activities",
            params={
                "per_page": per_page,
                "page": page,
            },
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=30,
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"strava list activities error {response.status_code}: {response.text[:300]}",
            )

        activities = response.json()

        result = []
        for item in activities:
            result.append(
                {
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "sport_type": item.get("sport_type") or item.get("type"),
                    "start_date": item.get("start_date"),
                    "distance": item.get("distance"),
                    "moving_time": item.get("moving_time"),
                }
            )

        return {
            "ok": True,
            "user_id": user_id,
            "page": page,
            "per_page": per_page,
            "count": len(result),
            "activities": result,
        }

    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"http error: {e}")




@app.post("/debug/backfill/recent/{user_id}")
def debug_backfill_recent(user_id: str, per_page: int = 10, page: int = 1):
    try:
        access_token, _, _ = refresh_strava_token_if_needed(user_id)

        response = requests.get(
            "https://www.strava.com/api/v3/athlete/activities",
            params={
                "per_page": per_page,
                "page": page,
            },
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=30,
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"strava list activities error {response.status_code}: {response.text[:300]}",
            )
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select strava_athlete_id
                    from user_strava_connection
                    where user_id = %s;
                    """,
                    (user_id,),
                )
                athlete_row = cur.fetchone()

                if not athlete_row:
                    raise HTTPException(
                        status_code=404,
                        detail=f"user_strava_connection not found for user_id={user_id}",
                    )

                strava_athlete_id = athlete_row[0]
        activities = response.json()
        processed = []

        for item in activities:
            activity_id = item.get("id")
            if not activity_id:
                continue

            # 1. если activity_raw еще нет, создаем ingest job и сразу обрабатываем
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        select 1
                        from strava_activity_raw
                        where strava_activity_id = %s;
                        """,
                        (activity_id,),
                    )
                    exists_row = cur.fetchone()

                    if not exists_row:
                        cur.execute(
                            """
                            insert into strava_activity_ingest_job (
                                webhook_event_id,
                                user_id,
                                strava_athlete_id,
                                strava_activity_id,
                                reason,
                                status
                            )
                            values (null, %s, %s, %s, 'backfill_recent', 'pending')
                            on conflict do nothing;
                            """,
                            (user_id, strava_athlete_id, activity_id),
                        )                        
                        conn.commit()

            # 2. пробуем подтянуть саму activity
            process_one_strava_ingest_job()

            # 3. streams
            debug_strava_fetch_streams(activity_id)

            # 4. metrics
            debug_compute_activity_metrics(activity_id)

            processed.append(
                {
                    "activity_id": activity_id,
                    "name": item.get("name"),
                    "start_date": item.get("start_date"),
                }
            )

        return {
            "ok": True,
            "user_id": user_id,
            "count": len(processed),
            "activities": processed,
        }

    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"http error: {e}")
    except psycopg.Error as e:
        raise HTTPException(status_code=500, detail=f"db error: {e}")


@app.post("/debug/load/recompute-all/{user_id}")
def debug_recompute_daily_load_all(user_id: str):
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select
                        m.user_id,
                        date(r.start_date) as day,
                        count(*) as activities_count,
                        coalesce(sum(m.duration_s), 0) as duration_s,
                        coalesce(sum(m.distance_m), 0) as distance_m,
                        coalesce(sum(m.elevation_gain_m), 0) as elevation_gain_m,
                        coalesce(sum(m.work_kj), 0) as work_kj,
                        coalesce(sum(m.tss), 0) as tss
                    from activity_metrics m
                    join strava_activity_raw r
                      on r.strava_activity_id = m.strava_activity_id
                    where m.user_id = %s
                    group by m.user_id, date(r.start_date)
                    order by day asc;
                    """,
                    (user_id,),
                )
                rows = cur.fetchall()

                if not rows:
                    raise HTTPException(
                        status_code=404,
                        detail=f"no activity_metrics found for user_id={user_id}",
                    )

                for row in rows:
                    (
                        row_user_id,
                        day,
                        activities_count,
                        duration_s,
                        distance_m,
                        elevation_gain_m,
                        work_kj,
                        tss,
                    ) = row

                    cur.execute(
                        """
                        insert into daily_training_load (
                            user_id,
                            date,
                            activities_count,
                            duration_s,
                            distance_m,
                            elevation_gain_m,
                            work_kj,
                            tss,
                            computed_at
                        )
                        values (%s, %s, %s, %s, %s, %s, %s, %s, now())
                        on conflict (user_id, date) do update set
                            activities_count = excluded.activities_count,
                            duration_s = excluded.duration_s,
                            distance_m = excluded.distance_m,
                            elevation_gain_m = excluded.elevation_gain_m,
                            work_kj = excluded.work_kj,
                            tss = excluded.tss,
                            computed_at = now();
                        """,
                        (
                            row_user_id,
                            day,
                            activities_count,
                            duration_s,
                            distance_m,
                            elevation_gain_m,
                            work_kj,
                            tss,
                        ),
                    )

                conn.commit()

        return {
            "ok": True,
            "user_id": user_id,
            "days_processed": len(rows),
            "from_date": str(rows[0][1]),
            "to_date": str(rows[-1][1]),
        }

    except psycopg.Error as e:
        raise HTTPException(status_code=500, detail=f"db error: {e}")



@app.get("/fitness/history/{user_id}")
def fitness_history(user_id: str, limit: int = 120):
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select
                        date,
                        daily_tss,
                        fitness_signal,
                        fatigue_signal,
                        freshness_signal
                    from daily_fitness_state
                    where user_id = %s
                    order by date desc
                    limit %s;
                    """,
                    (user_id, limit),
                )

                rows = cur.fetchall()

        result = []
        for r in rows:
            result.append(
                {
                    "date": str(r[0]),
                    "tss": float(r[1]),
                    "fitness": float(r[2]),
                    "fatigue": float(r[3]),
                    "freshness": float(r[4]),
                }
            )

        result.reverse()

        return {
            "ok": True,
            "user_id": user_id,
            "points": len(result),
            "data": result,
        }

    except psycopg.Error as e:
        raise HTTPException(status_code=500, detail=f"db error: {e}")
