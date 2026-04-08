from __future__ import annotations

import json

from backend.db import get_conn
from backend.schemas.healthkit import HealthSyncPayload


def save_healthkit_ingest_raw(*, user_id: str, payload: HealthSyncPayload) -> None:
    # Сохраняем payload как есть в raw-слой.
    # Это базовый ingestion для дальнейшей нормализации и recovery processing.
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into healthkit_ingest_raw (
                    user_id,
                    generated_at,
                    timezone,
                    payload_json
                )
                values (
                    %s,
                    %s,
                    %s,
                    %s::jsonb
                );
                """,
                (
                    user_id,
                    payload.generatedAt,
                    payload.timezone,
                    json.dumps(payload.model_dump(mode="json")),
                ),
            )
            conn.commit()