import datetime as dt

import psycopg
import requests
from fastapi import HTTPException

from backend.config import settings
from backend.db import get_conn


def refresh_strava_token_if_needed(user_id: str):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select
                    access_token,
                    refresh_token,
                    extract(epoch from expires_at)::bigint as expires_at_unix
                from user_strava_connection
                where user_id = %s;
                """,
                (user_id,),
            )
            row = cur.fetchone()

            if not row:
                raise HTTPException(
                    status_code=404,
                    detail=f"user_strava_connection not found for user_id={user_id}",
                )

            access_token, refresh_token, expires_at_unix = row

    now_unix = int(dt.datetime.now(dt.timezone.utc).timestamp())

    if expires_at_unix > now_unix + 60:
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
            detail=f"strava token refresh failed {response.status_code}: {response.text[:300]}",
        )

    payload = response.json()

    new_access_token = payload["access_token"]
    new_refresh_token = payload["refresh_token"]
    new_expires_at_unix = payload["expires_at"]

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                update user_strava_connection
                set
                    access_token = %s,
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
