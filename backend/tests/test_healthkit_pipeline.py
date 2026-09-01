from datetime import date, datetime

import pytest

from backend.schemas.healthkit import HealthSyncPayload, RestingHRDailyDTO
from backend.services import healthkit_pipeline


def _payload() -> HealthSyncPayload:
    return HealthSyncPayload(
        generatedAt=datetime(2026, 4, 17, 10, 0, 0),
        timezone="Europe/Moscow",
        restingHeartRateDaily=[
            RestingHRDailyDTO(date=date(2026, 4, 16), bpm=52.0),
        ],
    )


def test_legacy_healthkit_replay_uses_explicit_historical_date(monkeypatch):
    calls = []
    monkeypatch.setattr(
        healthkit_pipeline,
        "save_healthkit_ingest_raw",
        lambda **kwargs: calls.append(("raw", kwargs["user_id"])),
    )
    monkeypatch.setattr(
        healthkit_pipeline,
        "process_latest_healthkit_raw",
        lambda user_id: {"ok": True, "user_id": user_id},
    )
    monkeypatch.setattr(
        healthkit_pipeline,
        "recompute_health_recovery_daily_for_date",
        lambda user_id, target_date: calls.append(("recovery", target_date))
        or {"ok": True},
    )
    monkeypatch.setattr(
        healthkit_pipeline,
        "recompute_load_state_daily_v2",
        lambda user_id, through_date: calls.append(("load", through_date))
        or {
            "ok": True,
            "days_processed": 1,
            "last_date": through_date,
        },
    )
    monkeypatch.setattr(
        healthkit_pipeline,
        "recompute_readiness_daily_for_date",
        lambda user_id, target_date: calls.append(("readiness", target_date))
        or {
            "ok": True,
            "date": target_date,
            "freshness": 2.0,
            "explanation_json": {"recovery_explanation": {}},
        },
    )

    result = healthkit_pipeline.ingest_and_process_healthkit_payload(
        user_id="user-1",
        payload=_payload(),
    )

    assert result["affected_dates"] == ["2026-04-16"]
    assert result["load_last_date"] == "2026-04-16"
    assert calls == [
        ("raw", "user-1"),
        ("recovery", "2026-04-16"),
        ("load", "2026-04-16"),
        ("readiness", "2026-04-16"),
    ]


def test_legacy_healthkit_replay_rejects_incomplete_load_calendar(monkeypatch):
    monkeypatch.setattr(
        healthkit_pipeline,
        "save_healthkit_ingest_raw",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        healthkit_pipeline,
        "process_latest_healthkit_raw",
        lambda user_id: {"ok": True},
    )
    monkeypatch.setattr(
        healthkit_pipeline,
        "recompute_health_recovery_daily_for_date",
        lambda user_id, target_date: {"ok": True},
    )
    monkeypatch.setattr(
        healthkit_pipeline,
        "recompute_load_state_daily_v2",
        lambda user_id, through_date: {"ok": True, "last_date": None},
    )
    monkeypatch.setattr(
        healthkit_pipeline,
        "recompute_readiness_daily_for_date",
        lambda user_id, target_date: {"ok": True},
    )

    with pytest.raises(ValueError, match="did not reach latest recovery date"):
        healthkit_pipeline.ingest_and_process_healthkit_payload(
            user_id="user-1",
            payload=_payload(),
        )
