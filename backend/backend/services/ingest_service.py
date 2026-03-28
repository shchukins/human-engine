from typing import Any

from backend.db import get_conn
from backend.services.pipeline_service import process_activity_pipeline


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

    try:
        result = process_activity_pipeline(
            user_id=user_id,
            athlete_id=athlete_id,
            activity_id=activity_id,
        )

        with get_conn() as conn:
            with conn.cursor() as cur:
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
            "name": result.get("name"),
            "tss": result.get("tss"),
        }

    except Exception as e:
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
                    (str(e)[:500], job_id),
                )
                conn.commit()

        raise
