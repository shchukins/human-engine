from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import psycopg
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = Field(alias="DATABASE_URL")

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