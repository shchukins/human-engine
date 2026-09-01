import pytest

from backend.services.readiness_composition import (
    READINESS_MODEL_VERSION,
    compose_readiness,
    normalize_feeling,
)


def test_strava_only_uses_freshness_without_penalizing_missing_optional_signals():
    result = compose_readiness(
        load_context={"tss": 70.0},
        freshness=10.0,
        feeling_score=None,
        physiology_score=None,
        physiology_explanation=None,
    )

    assert result["readiness_score"] == 60.0
    assert result["model"]["version"] == READINESS_MODEL_VERSION
    assert result["signal_families"]["freshness"]["effective_weight"] == 1.0
    assert result["signal_families"]["physiology"]["availability"] == "unavailable"
    assert result["signal_families"]["physiology"]["contribution"] == 0.0


def test_subjective_feeling_enriches_strava_only_result():
    result = compose_readiness(
        load_context={"tss": 70.0},
        freshness=0.0,
        feeling_score=5,
        physiology_score=None,
        physiology_explanation=None,
    )

    assert result["readiness_score"] == 70.0
    assert result["signal_families"]["freshness"]["effective_weight"] == 0.6
    assert result["signal_families"]["feeling"]["effective_weight"] == 0.4
    assert result["signal_families"]["feeling"]["contribution"] == 40.0


def test_feeling_and_physiology_share_optional_evidence_weight():
    result = compose_readiness(
        load_context={"tss": 0.0},
        freshness=0.0,
        feeling_score=3,
        physiology_score=100.0,
        physiology_explanation={"method": "baseline_v2"},
    )

    assert result["readiness_score"] == 60.0
    assert result["signal_families"]["freshness"]["effective_weight"] == 0.6
    assert result["signal_families"]["feeling"]["effective_weight"] == 0.2
    assert result["signal_families"]["physiology"]["effective_weight"] == 0.2


def test_physiology_only_is_valid_and_not_tied_to_load_availability():
    result = compose_readiness(
        load_context=None,
        freshness=None,
        feeling_score=None,
        physiology_score=72.5,
        physiology_explanation={},
    )

    assert result["readiness_score"] == 72.5
    assert result["signal_families"]["load"]["availability"] == "unavailable"
    assert result["signal_families"]["physiology"]["effective_weight"] == 1.0


def test_no_scored_signal_is_rejected():
    with pytest.raises(ValueError, match="at least one scored readiness signal"):
        compose_readiness(
            load_context={"tss": 0.0},
            freshness=None,
            feeling_score=None,
            physiology_score=None,
            physiology_explanation=None,
        )


@pytest.mark.parametrize(
    ("raw_score", "normalized"),
    [(1, 0.0), (2, 25.0), (3, 50.0), (4, 75.0), (5, 100.0)],
)
def test_feeling_scale_is_explicit(raw_score, normalized):
    assert normalize_feeling(raw_score) == normalized


def test_invalid_feeling_score_is_rejected():
    with pytest.raises(ValueError, match="between 1 and 5"):
        normalize_feeling(6)


def test_response_metrics_are_exposed_without_changing_readiness_score():
    without_response = compose_readiness(
        load_context={"tss": 70.0},
        freshness=10.0,
        feeling_score=4,
        physiology_score=None,
        physiology_explanation=None,
    )
    response_context = {
        "activity_id": 42,
        "version": "v1",
        "rpe_score": 4,
        "aerobic_decoupling_pct": 4.2,
    }
    with_response = compose_readiness(
        load_context={"tss": 70.0},
        freshness=10.0,
        feeling_score=4,
        physiology_score=None,
        physiology_explanation=None,
        response_context=response_context,
    )

    assert with_response["readiness_score"] == without_response["readiness_score"]
    assert with_response["signal_families"]["response"] == {
        "availability": "available",
        "used": False,
        "score": None,
        "configured_weight": 0.0,
        "effective_weight": 0.0,
        "contribution": 0.0,
        "reason_codes": ["response_context_only_phase_1"],
        "data": response_context,
    }
