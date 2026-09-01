from backend.services.activity_response_service import (
    build_baseline_snapshot,
    classify_intensity_band,
    compute_aerobic_decoupling,
    compute_response_metrics,
)


def test_classify_intensity_band_has_explicit_boundaries():
    assert classify_intensity_band(None) is None
    assert classify_intensity_band(0.54) == "recovery"
    assert classify_intensity_band(0.55) == "endurance"
    assert classify_intensity_band(0.75) == "tempo"
    assert classify_intensity_band(0.90) == "threshold"
    assert classify_intensity_band(1.05) == "high_intensity"


def test_compute_response_metrics_includes_rpe_and_objective_relationships():
    result = compute_response_metrics(
        duration_s=3600,
        avg_power=180.0,
        normalized_power=190.0,
        avg_heartrate=150.0,
        intensity_factor=0.8,
        tss=64.0,
        variability_index=1.05,
        rpe_score=4,
        time_stream=list(range(3601)),
        watts_stream=[180.0] * 3601,
        hr_stream=[150.0] * 1800 + [153.0] * 1801,
    )

    assert result["avg_power_to_hr"] == 1.2
    assert result["normalized_power_to_hr"] == 1.266667
    assert result["aerobic_decoupling_pct"] > 0
    assert result["session_rpe_load"] == 240.0
    assert result["rpe_per_intensity_factor"] == 5.0
    assert result["session_rpe_load_per_tss"] == 3.75
    assert result["intensity_band"] == "tempo"
    assert result["availability"]["rpe"]["availability"] == "available"


def test_decoupling_rejects_nonsteady_or_short_sessions_explicitly():
    result = compute_aerobic_decoupling(
        time_stream=list(range(600)),
        watts_stream=[180.0] * 600,
        hr_stream=[150.0] * 600,
        duration_s=599,
        variability_index=1.2,
    )

    assert result["value"] is None
    assert result["availability"] == "unavailable"
    assert result["reason_codes"] == [
        "duration_below_30_minutes",
        "workout_not_steady",
    ]


def test_missing_power_hr_and_rpe_are_unavailable_not_zero():
    result = compute_response_metrics(
        duration_s=3600,
        avg_power=None,
        normalized_power=None,
        avg_heartrate=None,
        intensity_factor=None,
        tss=None,
        variability_index=None,
        rpe_score=None,
        time_stream=[],
        watts_stream=[],
        hr_stream=[],
    )

    assert result["avg_power_to_hr"] is None
    assert result["aerobic_decoupling_pct"] is None
    assert result["session_rpe_load"] is None
    assert result["availability"]["power"]["availability"] == "unavailable"
    assert result["availability"]["rpe"]["reason_codes"] == ["rpe_unavailable"]


def test_baseline_requires_three_comparable_observations_and_uses_median():
    current = {
        "normalized_power_to_hr": 1.3,
        "aerobic_decoupling_pct": 5.0,
        "rpe_per_intensity_factor": 5.5,
        "session_rpe_load_per_tss": 4.0,
    }
    history = [
        (1.0, 3.0, 4.0, 3.0),
        (1.1, 4.0, 5.0, 3.5),
        (1.2, None, 6.0, 4.0),
    ]

    baseline = build_baseline_snapshot(current, history)

    power_hr = baseline["metrics"]["normalized_power_to_hr"]
    decoupling = baseline["metrics"]["aerobic_decoupling_pct"]
    assert power_hr["availability"] == "available"
    assert power_hr["median"] == 1.1
    assert power_hr["deviation_pct"] == 18.182
    assert decoupling["availability"] == "unavailable"
    assert decoupling["sample_count"] == 2
