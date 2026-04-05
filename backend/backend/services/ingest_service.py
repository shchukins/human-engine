from typing import Any

from backend.config import settings
from backend.db import get_conn
from backend.services.notification_service import notify_training_processed
from backend.services.pipeline_service import process_activity_pipeline


MAX_ATTEMPTS = 5
RETRY_DELAY_MINUTES = 5


def _is_retryable_error(error_text: str) -> bool:
    text = (error_text or "").lower()

    non_retry_markers = [
        "404",
        "record not found",
        "invalid",
    ]

    if any(marker in text for marker in non_retry_markers):
        return False

    retry_markers = [
        "403",
        "429",
        "500",
        "502",
        "503",
        "504",
        "timeout",
        "connection",
    ]

    return any(marker in text for marker in retry_markers)


def process_one_strava_ingest_job() -> dict[str, Any]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select
                    j.id,
                    j.user_id,
                    j.strava_athlete_id,
                    j.strava_activity_id,
                    j.reason,
                    j.attempt_count
                from strava_activity_ingest_job j
                where j.status = 'pending'
                  and (j.scheduled_at is null or j.scheduled_at <= now())
                order by j.scheduled_at asc nulls first, j.id asc
                limit 1;
                """
            )

            row = cur.fetchone()

            if not row:
                return {"ok": True, "message": "no pending jobs"}

            job_id, user_id, athlete_id, activity_id, reason, attempt_count = row

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

        if settings.telegram_notify_on_webhook_success and reason == "webhook_create":
            try:
                notify_training_processed(user_id=user_id, activity_id=activity_id)
            except Exception:
                pass

        return {
            "ok": True,
            "job_id": job_id,
            "activity_id": activity_id,
            "name": result.get("name"),
            "tss": result.get("tss"),
        }

    except Exception as e:
        error_text = str(e)[:500]
        next_attempt_number = (attempt_count or 0) + 1

        retryable = _is_retryable_error(error_text)
        exhausted = next_attempt_number >= MAX_ATTEMPTS

        with get_conn() as conn:
            with conn.cursor() as cur:
                if retryable and not exhausted:
                    cur.execute(
                        """
                        update strava_activity_ingest_job
                        set status = 'pending',
                            started_at = null,
                            finished_at = null,
                            scheduled_at = now() + (%s * interval '1 minute'),
                            last_error = %s
                        where id = %s;
                        """,
                        (RETRY_DELAY_MINUTES, error_text, job_id),
                    )
                    conn.commit()

                    return {
                        "ok": False,
                        "job_id": job_id,
                        "activity_id": activity_id,
                        "status": "retry_scheduled",
                        "attempt": next_attempt_number,
                        "max_attempts": MAX_ATTEMPTS,
                        "error": error_text,
                    }

                cur.execute(
                    """
                    update strava_activity_ingest_job
                    set status = 'failed',
                        finished_at = now(),
                        last_error = %s
                    where id = %s;
                    """,
                    (error_text, job_id),
                )
                conn.commit()

        raise