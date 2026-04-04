from unittest.mock import MagicMock, patch

from backend.services.ingest_service import process_one_strava_ingest_job


def _mock_conn(job_row):
    conn = MagicMock()
    cur = MagicMock()

    # Первый fetchone() возвращает pending job.
    cur.fetchone.side_effect = [job_row]

    conn.cursor.return_value.__enter__.return_value = cur
    conn.__enter__.return_value = conn
    return conn, cur


@patch("backend.services.ingest_service.notify_training_processed")
@patch("backend.services.ingest_service.process_activity_pipeline")
@patch("backend.services.ingest_service.get_conn")
@patch("backend.services.ingest_service.settings")
def test_notify_sent_for_webhook_create(
    mock_settings,
    mock_get_conn,
    mock_pipeline,
    mock_notify,
):
    mock_settings.telegram_notify_on_webhook_success = True

    job_row = (
        100,                # job_id
        "sergey",           # user_id
        191684548,          # athlete_id
        17855535922,        # activity_id
        "webhook_create",   # reason
        0,                  # attempt_count
    )

    conn1, cur1 = _mock_conn(job_row)
    conn2, cur2 = _mock_conn(job_row)

    # Первый get_conn() -> чтение job + update running
    # Второй get_conn() -> update done
    mock_get_conn.side_effect = [conn1, conn2]

    mock_pipeline.return_value = {
        "ok": True,
        "name": "Test Workout",
        "tss": 42.5,
    }

    result = process_one_strava_ingest_job()

    assert result["ok"] is True
    assert result["job_id"] == 100
    assert result["activity_id"] == 17855535922

    mock_notify.assert_called_once_with(
        user_id="sergey",
        activity_id=17855535922,
    )


@patch("backend.services.ingest_service.notify_training_processed")
@patch("backend.services.ingest_service.process_activity_pipeline")
@patch("backend.services.ingest_service.get_conn")
@patch("backend.services.ingest_service.settings")
def test_notify_not_sent_for_non_webhook_reason(
    mock_settings,
    mock_get_conn,
    mock_pipeline,
    mock_notify,
):
    mock_settings.telegram_notify_on_webhook_success = True

    job_row = (
        101,                  # job_id
        "sergey",             # user_id
        191684548,            # athlete_id
        17855535922,          # activity_id
        "manual_worker_test", # reason
        0,                    # attempt_count
    )

    conn1, cur1 = _mock_conn(job_row)
    conn2, cur2 = _mock_conn(job_row)

    mock_get_conn.side_effect = [conn1, conn2]

    mock_pipeline.return_value = {
        "ok": True,
        "name": "Test Workout",
        "tss": 42.5,
    }

    result = process_one_strava_ingest_job()

    assert result["ok"] is True
    assert result["job_id"] == 101
    assert result["activity_id"] == 17855535922

    mock_notify.assert_not_called()