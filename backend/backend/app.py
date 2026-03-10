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
