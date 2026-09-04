from datetime import date, datetime, timezone

from backend.services.pilot_report import build_pilot_report


def _row(day: date, **overrides):
    values = {
        "readiness_score": 70.0,
        "good_day_probability": 0.7,
        "status_text": "Good",
        "explanation": {"source_timestamps": {"training_source_at": day.isoformat()},
                        "signal_families": {
            "load": {"available": True, "used": False},
            "freshness": {"available": True, "used": True},
            "response": {"available": False, "used": False},
            "feeling": {"available": False, "used": False},
            "physiology": {"available": False, "used": False},
        }},
        "computed_at": datetime(2026, 9, 1, 5, tzinfo=timezone.utc),
        "notification_status": "sent", "previous_activities": 1,
        "previous_tss": 50.0, "prompt_status": "sent",
        "recovery_feedback": True, "activities": 1, "rpe_prompts": 1,
        "rpe_responses": 1,
        "before": {"readiness_score": 60.0, "recommendation": "moderate"},
        "after": {"readiness_score": 70.0, "recommendation": "moderate"},
        "delivery": {"readiness_score": 70.0}, "ingest_failures": 0,
        "delivery_failures": 0,
    }
    values.update(overrides)
    return (
        day, values["readiness_score"], values["good_day_probability"],
        values["status_text"], values["explanation"], values["computed_at"],
        values["notification_status"], values["previous_activities"],
        values["previous_tss"], values["prompt_status"],
        values["recovery_feedback"], values["activities"], values["rpe_prompts"],
        values["rpe_responses"], values["before"], values["after"],
        values["delivery"], values["ingest_failures"], values["delivery_failures"],
    )


def test_report_uses_explicit_denominators_and_signal_availability():
    rows = [
        _row(date(2026, 9, 1)),
        _row(date(2026, 9, 2), readiness_score=None, good_day_probability=None,
             status_text=None, explanation={}, previous_activities=0,
             previous_tss=0, prompt_status=None, recovery_feedback=False,
             activities=0, rpe_prompts=0, rpe_responses=0, before=None,
             after=None, delivery=None, ingest_failures=1, delivery_failures=1),
    ]
    report = build_pilot_report(user_id="user-1", date_from=date(2026, 9, 1),
                                date_to=date(2026, 9, 2), timezone="Europe/Moscow",
                                rows=rows)
    metrics = report["metrics"]
    assert metrics["valid_morning_recommendations"] == {
        "numerator": 1, "denominator": 2, "rate": 0.5,
    }
    assert metrics["valid_recommendations_without_physiology"]["rate"] == 1.0
    assert metrics["morning_recovery_response"]["rate"] == 1.0
    assert metrics["post_workout_rpe_completion"]["rate"] == 1.0
    assert metrics["signal_family_distribution"]["freshness"] == {
        "available_days": 1, "used_days": 1,
    }
    assert metrics["recommendation_changes_after_checkin"]["rate"] == 1.0
    assert metrics["stale_or_missing_required_training_input"]["rate"] == 0.5
    assert metrics["failures"]["ingestion"] == 1
    assert metrics["failures"]["delivery"] == 1


def test_report_does_not_claim_rates_without_denominators():
    row = _row(date(2026, 9, 1), readiness_score=None, previous_activities=0,
               previous_tss=0, recovery_feedback=False, rpe_prompts=0,
               rpe_responses=0, before=None, after=None)
    report = build_pilot_report(user_id="user-1", date_from=date(2026, 9, 1),
                                date_to=date(2026, 9, 1), timezone="Europe/Moscow",
                                rows=[row])
    metrics = report["metrics"]
    assert metrics["valid_recommendations_without_physiology"]["rate"] is None
    assert metrics["morning_recovery_response"]["rate"] is None
    assert metrics["post_workout_rpe_completion"]["rate"] is None
    assert metrics["recommendation_changes_after_checkin"]["rate"] is None
