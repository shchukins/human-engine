import pytest

from backend.services.readiness_composition import (
    READINESS_MODEL_VERSION,
    compose_readiness,
    normalize_feeling,
    normalize_response_drift,
    normalize_response_ratio_deviation,
    score_response_context,
)


def _response_context(
    *,
    activity_date="2026-08-31",
    efficiency_deviation=10.0,
    drift_current=4.0,
    drift_baseline=2.0,
    rpe_tss_deviation=10.0,
    rpe_if_deviation=20.0,
):
    return {
        "activity_id": 42,
        "activity_date": activity_date,
        "version": "v1",
        "baseline": {
            "minimum_samples": 3,
            "metrics": {
                "normalized_power_to_hr": {
                    "sample_count": 5,
                    "current": 1.1,
                    "median": 1.0,
                    "deviation_pct": efficiency_deviation,
                },
                "aerobic_decoupling_pct": {
                    "sample_count": 5,
                    "current": drift_current,
                    "median": drift_baseline,
                    "deviation_pct": 100.0,
                },
                "session_rpe_load_per_tss": {
                    "sample_count": 5,
                    "current": 1.1,
                    "median": 1.0,
                    "deviation_pct": rpe_tss_deviation,
                },
                "rpe_per_intensity_factor": {
                    "sample_count": 5,
                    "current": 1.2,
                    "median": 1.0,
                    "deviation_pct": rpe_if_deviation,
                },
            },
        },
    }


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


def test_response_without_usable_baseline_preserves_existing_readiness_formula():
    without_response = compose_readiness(
        load_context={"tss": 70.0},
        freshness=10.0,
        feeling_score=4,
        physiology_score=None,
        physiology_explanation=None,
    )
    response_context = {
        "activity_id": 42,
        "activity_date": "2026-08-31",
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
        target_date="2026-09-01",
    )

    assert with_response["readiness_score"] == without_response["readiness_score"]
    response = with_response["signal_families"]["response"]
    assert response["availability"] == "available"
    assert response["used"] is False
    assert response["score"] is None
    assert response["configured_weight"] == 0.0
    assert response["effective_weight"] == 0.0
    assert response["contribution"] == 0.0
    assert response["reason_codes"] == ["response_baseline_insufficient"]


@pytest.mark.parametrize(
    ("deviation", "higher_is_better", "expected"),
    [
        (0.0, True, 50.0),
        (10.0, True, 70.0),
        (-10.0, True, 30.0),
        (10.0, False, 30.0),
        (-10.0, False, 70.0),
        (100.0, True, 100.0),
        (100.0, False, 0.0),
    ],
)
def test_response_ratio_normalization_is_directional_and_bounded(
    deviation,
    higher_is_better,
    expected,
):
    assert (
        normalize_response_ratio_deviation(
            deviation,
            higher_is_better=higher_is_better,
        )
        == expected
    )


def test_drift_uses_percentage_point_difference_with_zero_or_negative_baseline():
    assert normalize_response_drift(2.0, 0.0) == 30.0
    assert normalize_response_drift(1.0, -1.0) == 30.0
    assert normalize_response_drift(-3.0, 2.0) == 100.0


def test_response_builds_equal_objective_and_subjective_channels():
    result = score_response_context(
        _response_context(),
        target_date="2026-09-01",
    )

    scoring = result["data"]["scoring"]
    assert scoring["components"]["efficiency"]["score"] == 70.0
    assert scoring["components"]["drift"]["score"] == 30.0
    assert scoring["channels"] == {"objective": 50.0, "subjective": 30.0}
    assert scoring["selected_subjective_metric"] == "session_rpe_load_per_tss"
    assert result["score"] == 40.0
    assert result["configured_weight"] == 0.2


def test_response_uses_rpe_per_intensity_fallback_without_counting_both_ratios():
    context = _response_context(rpe_tss_deviation=None, rpe_if_deviation=20.0)
    result = score_response_context(context, target_date="2026-09-01")

    scoring = result["data"]["scoring"]
    assert scoring["selected_subjective_metric"] == "rpe_per_intensity_factor"
    assert scoring["components"]["subjective_cost"]["score"] == 10.0
    assert scoring["channels"]["subjective"] == 10.0


@pytest.mark.parametrize(
    ("target_date", "expected_recency", "expected_weight", "reason_codes"),
    [
        ("2026-08-31", 1.0, 0.2, []),
        ("2026-09-01", 1.0, 0.2, []),
        ("2026-09-04", 0.5, 0.1, []),
        ("2026-09-07", 0.0, 0.0, ["response_expired_for_scoring"]),
    ],
)
def test_response_recency_reduces_configured_weight(
    target_date,
    expected_recency,
    expected_weight,
    reason_codes,
):
    result = score_response_context(_response_context(), target_date=target_date)

    assert result["data"]["scoring"]["recency"] == expected_recency
    assert result["configured_weight"] == expected_weight
    assert result["reason_codes"] == reason_codes


def test_response_takes_weight_from_recovery_evidence_budget():
    result = compose_readiness(
        load_context={"tss": 70.0},
        freshness=0.0,
        feeling_score=3,
        physiology_score=50.0,
        physiology_explanation={},
        response_context=_response_context(
            efficiency_deviation=0.0,
            drift_current=2.0,
            drift_baseline=2.0,
            rpe_tss_deviation=0.0,
        ),
        target_date="2026-09-01",
    )

    families = result["signal_families"]
    assert families["freshness"]["effective_weight"] == 0.6
    assert families["response"]["effective_weight"] == 0.2
    assert families["feeling"]["effective_weight"] == pytest.approx(0.1)
    assert families["physiology"]["effective_weight"] == pytest.approx(0.1)
    assert sum(family["effective_weight"] for family in families.values()) == pytest.approx(1.0)


def test_better_response_increases_readiness_with_other_signals_held_constant():
    common = {
        "load_context": {"tss": 70.0},
        "freshness": 0.0,
        "feeling_score": 3,
        "physiology_score": 50.0,
        "physiology_explanation": {},
        "target_date": "2026-09-01",
    }
    poor = compose_readiness(
        **common,
        response_context=_response_context(
            efficiency_deviation=-20.0,
            drift_current=6.0,
            drift_baseline=2.0,
            rpe_tss_deviation=20.0,
        ),
    )
    good = compose_readiness(
        **common,
        response_context=_response_context(
            efficiency_deviation=20.0,
            drift_current=-2.0,
            drift_baseline=2.0,
            rpe_tss_deviation=-20.0,
        ),
    )

    assert poor["signal_families"]["response"]["used"] is True
    assert good["readiness_score"] > poor["readiness_score"]


def test_absolute_load_context_is_not_counted_again_when_response_is_used():
    common = {
        "freshness": 0.0,
        "feeling_score": 3,
        "physiology_score": None,
        "physiology_explanation": None,
        "response_context": _response_context(),
        "target_date": "2026-09-01",
    }

    low_load_context = compose_readiness(load_context={"tss": 20.0}, **common)
    high_load_context = compose_readiness(load_context={"tss": 200.0}, **common)

    assert high_load_context["readiness_score"] == low_load_context["readiness_score"]
    assert high_load_context["signal_families"]["load"]["configured_weight"] == 0.0
    assert high_load_context["signal_families"]["load"]["contribution"] == 0.0
