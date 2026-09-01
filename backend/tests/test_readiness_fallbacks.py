import json

import pytest
from fastapi import HTTPException

from backend.services import readiness_daily


class _FakeCursor:
    def __init__(self, load_row, recovery_row, feeling_row=None) -> None:
        self._load_row = load_row
        self._recovery_row = recovery_row
        self._feeling_row = feeling_row
        self._last_query = ""
        self.insert_params: list[tuple] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, query, params):
        self._last_query = query
        if "insert into readiness_daily" in query:
            self.insert_params.append(params)

    def fetchone(self):
        if "from load_state_daily_v2" in self._last_query:
            return self._load_row
        if "from health_recovery_daily" in self._last_query:
            if self._recovery_row is None:
                return None
            return (*self._recovery_row, "recovery-updated-at")
        if "from activity_subjective_feedback" in self._last_query:
            return self._feeling_row
        return None


class _FakeConn:
    def __init__(self, cursor: _FakeCursor) -> None:
        self._cursor = cursor
        self.committed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return self._cursor

    def commit(self):
        self.committed = True


def _build_result(monkeypatch, *, load_row, recovery_row, feeling_row=None):
    fake_cursor = _FakeCursor(
        load_row=load_row,
        recovery_row=recovery_row,
        feeling_row=feeling_row,
    )
    fake_conn = _FakeConn(fake_cursor)

    monkeypatch.setattr(readiness_daily, "get_conn", lambda: fake_conn)

    result = readiness_daily.recompute_readiness_daily_for_date(
        user_id="user-1",
        target_date="2026-04-16",
    )
    explanation_json = json.loads(fake_cursor.insert_params[0][8])
    return result, explanation_json, fake_cursor, fake_conn


def test_recompute_readiness_daily_uses_full_formula_and_propagates_recovery_explanation(monkeypatch):
    recovery_explanation = {"method": "baseline_v2", "sleep_score": 82.8}

    result, explanation_json, fake_cursor, fake_conn = _build_result(
        monkeypatch,
        load_row=(80.0, 80.0, 50.0, 20.0, 10.0, 18.0, 5.0),
        recovery_row=(70.0, json.dumps(recovery_explanation)),
    )

    assert result["fallback_mode"] is None
    assert result["freshness"] == 5.0
    assert result["freshness_norm"] == 55.0
    assert result["recovery_score_simple"] == 70.0
    assert result["readiness_score_raw"] == 61.0
    assert result["readiness_score"] == 61.0
    assert result["good_day_probability"] == 0.61
    assert result["recommendation"] == "moderate"
    assert "Readiness score is 61/100" in result["reason"]

    assert explanation_json["fallback_mode"] is None
    assert explanation_json["freshness"] == 5.0
    assert explanation_json["freshness_norm"] == 55.0
    assert explanation_json["recovery_score_simple"] == 70.0
    assert explanation_json["recovery_explanation"] == {
        **recovery_explanation,
        "provider": "healthkit",
        "collection_status": "historical",
    }
    assert explanation_json["source_timestamps"] == {
        "recovery_source_at": "2026-04-16",
        "training_source_at": "2026-04-16",
        "timezone": "Europe/Moscow",
    }

    assert len(fake_cursor.insert_params) == 1
    assert fake_conn.committed is True


def test_recompute_readiness_daily_uses_recovery_only_fallback(monkeypatch):
    recovery_explanation = {"method": "baseline_v2", "hrv_score": 61.2}

    result, explanation_json, _, _ = _build_result(
        monkeypatch,
        load_row=None,
        recovery_row=(66.4, recovery_explanation),
    )

    assert result["fallback_mode"] == "recovery_only"
    assert result["readiness_score"] == 66.4
    assert result["good_day_probability"] == 0.664
    assert result["recommendation"] == "moderate"
    assert "Load context is missing" in result["reason"]

    assert explanation_json["fallback_mode"] == "recovery_only"
    assert explanation_json["freshness"] is None
    assert explanation_json["freshness_norm"] is None
    assert explanation_json["recovery_score_simple"] == 66.4
    assert explanation_json["recovery_explanation"] == {
        **recovery_explanation,
        "provider": "healthkit",
        "collection_status": "historical",
    }


def test_recompute_readiness_daily_uses_load_only_fallback(monkeypatch):
    result, explanation_json, _, _ = _build_result(
        monkeypatch,
        load_row=(60.0, 60.0, 50.0, 20.0, 10.0, 18.0, 12.5),
        recovery_row=None,
    )

    assert result["fallback_mode"] == "load_only"
    assert result["freshness"] == 12.5
    assert result["freshness_norm"] == 62.5
    assert result["recovery_score_simple"] is None
    assert result["readiness_score"] == 62.5
    assert result["good_day_probability"] == 0.625
    assert result["recommendation"] == "moderate"
    assert "Recovery context is missing" in result["reason"]

    assert explanation_json["fallback_mode"] == "load_only"
    assert explanation_json["freshness"] == 12.5
    assert explanation_json["freshness_norm"] == 62.5
    assert explanation_json["recovery_score_simple"] is None
    assert explanation_json["recovery_explanation"] is None


def test_recompute_readiness_daily_returns_404_without_creating_row(monkeypatch):
    fake_cursor = _FakeCursor(load_row=None, recovery_row=None)
    fake_conn = _FakeConn(fake_cursor)

    monkeypatch.setattr(readiness_daily, "get_conn", lambda: fake_conn)

    with pytest.raises(HTTPException) as exc_info:
        readiness_daily.recompute_readiness_daily_for_date(
            user_id="user-1",
            target_date="2026-04-16",
        )

    assert exc_info.value.status_code == 404
    assert "no freshness, feeling, or physiology data found" in exc_info.value.detail
    assert fake_cursor.insert_params == []
    assert fake_conn.committed is False


def test_recompute_readiness_daily_uses_morning_feeling_without_physiology(monkeypatch):
    result, explanation_json, _, _ = _build_result(
        monkeypatch,
        load_row=(60.0, 60.0, 50.0, 20.0, 10.0, 18.0, 0.0),
        recovery_row=None,
        feeling_row=(5,),
    )

    assert result["readiness_score"] == 70.0
    assert result["feeling_score"] == 5
    assert result["signal_families"]["feeling"]["contribution"] == 40.0
    assert explanation_json["signal_families"]["physiology"]["availability"] == "unavailable"
    assert explanation_json["model"]["version"] == readiness_daily.READINESS_MODEL_VERSION


def test_recompute_readiness_daily_persists_readiness_bearing_response(monkeypatch):
    response_context = {
        "activity_id": 42,
        "activity_date": "2026-04-15",
        "version": "v1",
        "baseline": {
            "metrics": {
                "normalized_power_to_hr": {
                    "current": 0.9,
                    "median": 1.0,
                    "deviation_pct": -10.0,
                    "sample_count": 5,
                },
                "aerobic_decoupling_pct": {
                    "current": 5.0,
                    "median": 2.0,
                    "deviation_pct": 150.0,
                    "sample_count": 5,
                },
                "session_rpe_load_per_tss": {
                    "current": 1.1,
                    "median": 1.0,
                    "deviation_pct": 10.0,
                    "sample_count": 5,
                },
            }
        },
    }
    monkeypatch.setattr(
        readiness_daily,
        "load_recent_response_context",
        lambda *args, **kwargs: response_context,
    )

    result, explanation_json, fake_cursor, _ = _build_result(
        monkeypatch,
        load_row=(60.0, 60.0, 50.0, 20.0, 10.0, 18.0, 0.0),
        recovery_row=(50.0, {"method": "baseline_v2"}),
    )

    response = result["signal_families"]["response"]
    assert response["used"] is True
    assert response["score"] == 27.5
    assert response["configured_weight"] == 0.2
    assert result["fallback_mode"] is None
    assert explanation_json["model"] == {
        "name": "readiness_signal_composition",
        "version": readiness_daily.READINESS_MODEL_VERSION,
        "formula_version": "signal_weighted_response_v1",
    }
    assert fake_cursor.insert_params[0][9] == readiness_daily.READINESS_MODEL_VERSION
