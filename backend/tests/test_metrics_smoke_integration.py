import json
import os
from datetime import datetime, timezone

import pytest

from backend.db import get_conn
from backend.services.pipeline_service import compute_and_store_activity_metrics


pytestmark = pytest.mark.skipif(
    not os.getenv("RUN_DB_TESTS"),
    reason="DB integration tests are disabled. Set RUN_DB_TESTS=1 to run.",
)


TEST_USER_ID = "test_metrics_smoke_user"
TEST_ACTIVITY_ID = 999000111222
TEST_ATHLETE_ID = 191684548


def _cleanup() -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "delete from activity_metrics where strava_activity_id = %s;",
                (TEST_ACTIVITY_ID,),
            )
            cur.execute(
                "delete from strava_activity_stream_raw where strava_activity_id = %s;",
                (TEST_ACTIVITY_ID,),
            )
            cur.execute(
                "delete from strava_activity_raw where strava_activity_id = %s;",
                (TEST_ACTIVITY_ID,),
            )
            cur.execute(
                "delete from user_training_profile where user_id = %s;",
                (TEST_USER_ID,),
            )
            conn.commit()


def _seed_test_data() -> None:
    time_data = list(range(60))
    watts_data = [150] * 60
    hr_data = [130] * 60

    with get_conn() as conn:
        with conn.cursor() as cur:
            # Профиль пользователя с FTP и зонами
            cur.execute(
                """
                insert into user_training_profile (
                    user_id,
                    effective_from,
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
                )
                values (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                );
                """,
                (
                    TEST_USER_ID,
                    datetime(2026, 1, 1, tzinfo=timezone.utc),
                    200,
                    190,
                    110,
                    150,
                    180,
                    210,
                    240,
                    280,
                    120,
                    140,
                    155,
                    170,
                ),
            )

            # Raw activity
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
                );
                """,
                (
                    TEST_USER_ID,
                    TEST_ATHLETE_ID,
                    TEST_ACTIVITY_ID,
                    "VirtualRide",
                    "Smoke Test Workout",
                    datetime(2026, 4, 2, 18, 0, 0, tzinfo=timezone.utc),
                    "(GMT+00:00) UTC",
                    20000.0,
                    60,
                    60,
                    100.0,
                    5.0,
                    8.0,
                    130.0,
                    145.0,
                    150.0,
                    180.0,
                    150.0,
                    50.0,
                    True,
                    False,
                    False,
                    json.dumps({"id": TEST_ACTIVITY_ID, "name": "Smoke Test Workout"}),
                ),
            )

            # Time stream
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
                values (%s, %s, %s, %s, %s, %s::jsonb, now());
                """,
                (
                    TEST_ACTIVITY_ID,
                    "time",
                    "time",
                    "high",
                    len(time_data),
                    json.dumps({"data": time_data}),
                ),
            )

            # Watts stream
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
                values (%s, %s, %s, %s, %s, %s::jsonb, now());
                """,
                (
                    TEST_ACTIVITY_ID,
                    "watts",
                    "time",
                    "high",
                    len(watts_data),
                    json.dumps({"data": watts_data}),
                ),
            )

            # Heart rate stream
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
                values (%s, %s, %s, %s, %s, %s::jsonb, now());
                """,
                (
                    TEST_ACTIVITY_ID,
                    "heartrate",
                    "time",
                    "high",
                    len(hr_data),
                    json.dumps({"data": hr_data}),
                ),
            )

            conn.commit()


def test_compute_and_store_activity_metrics_smoke():
    _cleanup()
    _seed_test_data()

    try:
        result = compute_and_store_activity_metrics(TEST_ACTIVITY_ID)

        assert result["ok"] is True
        assert result["activity_id"] == TEST_ACTIVITY_ID
        assert result["user_id"] == TEST_USER_ID
        assert result["tss"] is not None
        assert result["normalized_power"] is not None
        assert result["intensity_factor"] is not None

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select
                        strava_activity_id,
                        tss,
                        normalized_power,
                        intensity_factor
                    from activity_metrics
                    where strava_activity_id = %s
                      and version = 'v1';
                    """,
                    (TEST_ACTIVITY_ID,),
                )
                row = cur.fetchone()

        assert row is not None
        assert row[0] == TEST_ACTIVITY_ID
        assert row[1] is not None
        assert row[2] is not None
        assert row[3] is not None

    finally:
        _cleanup()
