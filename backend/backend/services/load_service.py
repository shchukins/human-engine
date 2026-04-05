import psycopg
from fastapi import HTTPException

from backend.db import get_conn


def recompute_daily_load_all(user_id: str) -> dict:
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
