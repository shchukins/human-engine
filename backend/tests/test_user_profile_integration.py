import os
from datetime import date

import pytest

from backend.db import get_conn
from backend.services.user_profile_service import ProfileChange, get_profile, save_profile_value, resolve_activity_profile
from test_metrics_smoke_integration import _cleanup, _seed_test_data, TEST_USER_ID, TEST_ACTIVITY_ID

pytestmark = pytest.mark.skipif(not os.getenv('RUN_DB_TESTS'), reason='Requires isolated PostgreSQL test database')


@pytest.fixture
def seeded_profile():
    _cleanup()
    _seed_test_data()
    try:
        yield
    finally:
        with get_conn() as conn:
            for table in ['user_profile_value', 'activity_response_metrics', 'daily_training_load', 'daily_fitness_state', 'load_state_daily_v2', 'readiness_daily']:
                conn.execute(f'delete from {table} where user_id=%s', (TEST_USER_ID,))
        _cleanup()


def test_dated_ftp_weight_and_correction(seeded_profile):
    save_profile_value(TEST_USER_ID, ProfileChange(metric='ftp', value=222, effective_from=date(2026, 7, 25)))
    save_profile_value(TEST_USER_ID, ProfileChange(metric='weight', value=73.5, effective_from=date(2026, 8, 1)))
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Europe/Moscow midnight is 21:00 UTC on the preceding date.
            for start, expected in [('2026-07-24 20:59:59+00', 200), ('2026-07-24 21:00:00+00', 222), ('2026-08-02 00:00:00+00', 222)]:
                cur.execute('update strava_activity_raw set start_date=%s where strava_activity_id=%s', (start, TEST_ACTIVITY_ID))
                assert resolve_activity_profile(cur, TEST_USER_ID, TEST_ACTIVITY_ID)[0] == expected
    save_profile_value(TEST_USER_ID, ProfileChange(metric='ftp', value=223, effective_from=date(2026, 7, 25)))
    data = get_profile(TEST_USER_ID)
    assert len(data['history']) == 2
    assert data['current']['ftp']['value'] == 223
    assert data['current']['weight']['value'] == 73.5
    assert data['pending_from'] == date(2026, 7, 25)


def test_unchanged_ftp_does_not_schedule_recompute(seeded_profile):
    change = ProfileChange(metric='ftp', value=222, effective_from=date(2026, 7, 25))
    save_profile_value(TEST_USER_ID, change)
    with get_conn() as conn:
        conn.execute('update user_profile_value set needs_recompute=false where user_id=%s', (TEST_USER_ID,))
    save_profile_value(TEST_USER_ID, change)
    assert get_profile(TEST_USER_ID)['pending_from'] is None


def test_recompute_updates_stored_metrics_and_readiness_through_rest_days(seeded_profile):
    from backend.services.pipeline_service import compute_and_store_activity_metrics
    from backend.services.user_profile_service import recompute_profile_history, local_today
    with get_conn() as conn:
        conn.execute('update strava_activity_raw set start_date=%s where strava_activity_id=%s', ('2026-07-26 12:00:00+00', TEST_ACTIVITY_ID))
    before = compute_and_store_activity_metrics(TEST_ACTIVITY_ID)
    save_profile_value(TEST_USER_ID, ProfileChange(metric='ftp', value=222, effective_from=date(2026, 7, 25)))
    assert recompute_profile_history(TEST_USER_ID) == 1
    assert get_profile(TEST_USER_ID)['pending_from'] is None
    with get_conn() as conn:
        after = conn.execute('select tss from activity_metrics where strava_activity_id=%s', (TEST_ACTIVITY_ID,)).fetchone()[0]
        assert after == pytest.approx(before['tss'] * (200 / 222) ** 2)
        assert conn.execute('select count(*) from readiness_daily where user_id=%s and date=%s', (TEST_USER_ID, local_today())).fetchone()[0] > 0
    assert recompute_profile_history(TEST_USER_ID) == 0


def test_first_ftp_without_legacy_profile_and_no_future_leak(seeded_profile):
    from backend.services.pipeline_service import compute_and_store_activity_metrics
    with get_conn() as conn:
        conn.execute('delete from user_training_profile where user_id=%s', (TEST_USER_ID,))
    save_profile_value(TEST_USER_ID, ProfileChange(metric='ftp', value=222, effective_from=date(2026, 7, 25)))
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute('update strava_activity_raw set start_date=%s where strava_activity_id=%s', ('2026-07-24 12:00:00+00', TEST_ACTIVITY_ID))
            assert resolve_activity_profile(cur, TEST_USER_ID, TEST_ACTIVITY_ID)[0] is None
            cur.execute('update strava_activity_raw set start_date=%s where strava_activity_id=%s', ('2026-07-26 12:00:00+00', TEST_ACTIVITY_ID))
    result = compute_and_store_activity_metrics(TEST_ACTIVITY_ID)
    assert result['tss'] is not None
    assert all(v is None for v in result['power_zones_s'].values())
    assert all(v is None for v in result['hr_zones_s'].values())


def test_weight_only_does_not_schedule_load_recompute(seeded_profile):
    save_profile_value(TEST_USER_ID, ProfileChange(metric='weight', value=73.5, effective_from=date(2026, 7, 25)))
    assert get_profile(TEST_USER_ID)['pending_from'] is None


def test_profile_lock_rejects_overlapping_mutation(seeded_profile):
    from backend.services.user_profile_service import _profile_lock
    from fastapi import HTTPException
    with _profile_lock(TEST_USER_ID):
        with pytest.raises(HTTPException) as exc:
            save_profile_value(TEST_USER_ID, ProfileChange(metric='ftp', value=222, effective_from=date(2026, 7, 25)))
        assert exc.value.status_code == 409
    save_profile_value(TEST_USER_ID, ProfileChange(metric='ftp', value=222, effective_from=date(2026, 7, 25)))
