from backend.services import daily_readiness_pipeline


def test_daily_readiness_extends_load_calendar_before_readiness(monkeypatch):
    calls = []
    monkeypatch.setattr(
        daily_readiness_pipeline,
        "recompute_load_state_daily_v2",
        lambda **kwargs: calls.append(("load", kwargs)) or {"ok": True},
    )
    monkeypatch.setattr(
        daily_readiness_pipeline,
        "recompute_readiness_daily_for_date",
        lambda **kwargs: calls.append(("readiness", kwargs))
        or {"ok": True, "readiness_score": 62.5},
    )

    result = daily_readiness_pipeline.recompute_daily_readiness(
        user_id="user-1",
        target_date="2026-09-01",
    )

    assert calls == [
        (
            "load",
            {"user_id": "user-1", "through_date": "2026-09-01"},
        ),
        (
            "readiness",
            {"user_id": "user-1", "target_date": "2026-09-01"},
        ),
    ]
    assert result["readiness"]["readiness_score"] == 62.5


def test_healthkit_ingestion_routes_are_not_exposed():
    from backend.app import app

    route_paths = {route.path for route in app.routes}

    assert not any(path.startswith("/api/v1/healthkit/") for path in route_paths)
