from datetime import date, datetime, timezone

from backend.services.readiness_freshness import classify_readiness_freshness


def _classify(**overrides):
    inputs = {
        "readiness_date": date(2026, 7, 30),
        "readiness_computed_at": datetime(2026, 7, 30, 5, tzinfo=timezone.utc),
        "recovery_source_at": date(2026, 7, 30),
        "training_source_at": date(2026, 7, 30),
        "evaluation_date": datetime(2026, 7, 30, 8, tzinfo=timezone.utc),
        "timezone": "Europe/Moscow",
        "data_quality": {"fallback_mode": None},
    }
    inputs.update(overrides)
    return classify_readiness_freshness(**inputs)


def test_both_current_sources_are_fresh():
    assert _classify() == {
        "freshness_state": "fresh",
        "freshness_reason_codes": [],
    }


def test_current_recovery_only_fallback_is_partial():
    result = _classify(
        training_source_at=None,
        data_quality={"fallback_mode": "recovery_only"},
    )
    assert result["freshness_state"] == "partial"
    assert result["freshness_reason_codes"] == [
        "training_source_missing",
        "fallback_recovery_only",
    ]


def test_current_load_only_fallback_is_partial():
    result = _classify(
        recovery_source_at=None,
        data_quality={"fallback_mode": "load_only"},
    )
    assert result["freshness_state"] == "partial"
    assert result["freshness_reason_codes"] == [
        "recovery_source_missing",
        "fallback_load_only",
    ]


def test_stale_recovery_source_is_stale():
    result = _classify(recovery_source_at=date(2026, 7, 29))
    assert result["freshness_state"] == "stale"
    assert "recovery_source_stale" in result["freshness_reason_codes"]


def test_stale_training_source_is_stale():
    result = _classify(training_source_at=date(2026, 7, 29))
    assert result["freshness_state"] == "stale"
    assert "training_source_stale" in result["freshness_reason_codes"]


def test_older_latest_readiness_date_is_stale():
    result = _classify(
        readiness_date=date(2026, 7, 29),
        recovery_source_at=date(2026, 7, 29),
        training_source_at=date(2026, 7, 29),
    )
    assert result["freshness_state"] == "stale"
    assert "readiness_date_before_local_today" in result["freshness_reason_codes"]


def test_missing_source_timestamps_are_missing():
    result = _classify(recovery_source_at=None, training_source_at=None)
    assert result["freshness_state"] == "missing"
    assert result["freshness_reason_codes"] == [
        "recovery_source_missing",
        "training_source_missing",
    ]


def test_timezone_boundary_changes_current_day_at_local_midnight():
    before_midnight = _classify(
        readiness_date=date(2026, 7, 29),
        recovery_source_at=date(2026, 7, 29),
        training_source_at=date(2026, 7, 29),
        evaluation_date=datetime(2026, 7, 29, 20, 59, tzinfo=timezone.utc),
    )
    after_midnight = _classify(
        readiness_date=date(2026, 7, 29),
        recovery_source_at=date(2026, 7, 29),
        training_source_at=date(2026, 7, 29),
        evaluation_date=datetime(2026, 7, 29, 21, 0, tzinfo=timezone.utc),
    )
    assert before_midnight["freshness_state"] == "fresh"
    assert after_midnight["freshness_state"] == "stale"


def test_same_inputs_always_produce_same_result():
    assert _classify() == _classify()


def test_historical_evaluation_does_not_age_readiness():
    result = _classify(
        readiness_date=date(2026, 6, 1),
        recovery_source_at=date(2026, 6, 1),
        training_source_at=date(2026, 6, 1),
        evaluation_date=date(2026, 6, 1),
    )
    assert result["freshness_state"] == "fresh"
