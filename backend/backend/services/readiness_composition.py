from __future__ import annotations

from datetime import date
from statistics import mean
from typing import Any


READINESS_MODEL_VERSION = "v2_signal_composition_response_v1"
READINESS_MODEL_NAME = "readiness_signal_composition"
READINESS_FORMULA_VERSION = "signal_weighted_response_v1"

FRESHNESS_CONFIGURED_WEIGHT = 0.6
RECOVERY_EVIDENCE_WEIGHT = 0.4
RESPONSE_MAX_CONFIGURED_WEIGHT = 0.2
RESPONSE_RATIO_POINTS_PER_DEVIATION_PCT = 2.0
RESPONSE_DRIFT_POINTS_PER_PERCENTAGE_POINT = 10.0
RESPONSE_SCORING_WINDOW_DAYS = 7

SIGNAL_FAMILIES = ("load", "freshness", "response", "feeling", "physiology")


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def normalize_freshness(freshness: float | None) -> float | None:
    """Map load-state freshness to the established deterministic 0..100 scale."""
    if freshness is None:
        return None
    return _clamp(50.0 + freshness, 0.0, 100.0)


def normalize_feeling(feeling_score: int | float | None) -> float | None:
    """Map the explicit 1..5 morning scale to 0..100 with a neutral midpoint."""
    if feeling_score is None:
        return None
    if feeling_score < 1 or feeling_score > 5:
        raise ValueError("feeling_score must be between 1 and 5")
    return round((float(feeling_score) - 1.0) * 25.0, 1)


def normalize_response_ratio_deviation(
    deviation_pct: float | None,
    *,
    higher_is_better: bool,
) -> float | None:
    """Map a comparable-session ratio deviation to a neutral-centered score.

    A 25% improvement or deterioration reaches the 0/100 bounds. Absolute
    activity load is intentionally absent: only deviation from the athlete's
    comparable-session baseline participates.
    """
    if deviation_pct is None:
        return None
    direction = 1.0 if higher_is_better else -1.0
    return round(
        _clamp(
            50.0
            + direction
            * RESPONSE_RATIO_POINTS_PER_DEVIATION_PCT
            * float(deviation_pct),
            0.0,
            100.0,
        ),
        1,
    )


def normalize_response_drift(
    current_pct: float | None,
    baseline_median_pct: float | None,
) -> float | None:
    """Score aerobic drift by percentage-point difference from baseline.

    Relative percentage deviation is unsafe here because a drift baseline can
    legitimately be zero or negative. Five percentage points worse/better than
    baseline reaches the 0/100 bounds.
    """
    if current_pct is None or baseline_median_pct is None:
        return None
    delta_pp = float(current_pct) - float(baseline_median_pct)
    return round(
        _clamp(
            50.0 - RESPONSE_DRIFT_POINTS_PER_PERCENTAGE_POINT * delta_pp,
            0.0,
            100.0,
        ),
        1,
    )


def _as_date(value: str | date | None) -> date | None:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None


def _baseline_metric(response_context: dict[str, Any], name: str) -> dict[str, Any]:
    baseline = response_context.get("baseline")
    if not isinstance(baseline, dict):
        return {}
    metrics = baseline.get("metrics")
    if not isinstance(metrics, dict):
        return {}
    metric = metrics.get(name)
    return metric if isinstance(metric, dict) else {}


def _component(
    *,
    metric: str,
    score: float | None,
    current: float | None,
    baseline: float | None,
    deviation: float | None,
    deviation_unit: str,
    direction: str,
) -> dict[str, Any]:
    return {
        "metric": metric,
        "availability": "available" if score is not None else "unavailable",
        "score": score,
        "current": current,
        "baseline_median": baseline,
        "deviation": deviation,
        "deviation_unit": deviation_unit,
        "direction": direction,
    }


def score_response_context(
    response_context: dict[str, Any] | None,
    *,
    target_date: str | date | None,
) -> dict[str, Any]:
    """Build a deterministic readiness-bearing score from response baselines."""
    if response_context is None:
        return {
            "score": None,
            "configured_weight": 0.0,
            "reason_codes": ["response_metrics_unavailable"],
            "data": {},
        }

    activity_date = _as_date(response_context.get("activity_date"))
    scoring_date = _as_date(target_date)
    age_days = (
        (scoring_date - activity_date).days
        if scoring_date is not None and activity_date is not None
        else None
    )

    efficiency_metric = _baseline_metric(response_context, "normalized_power_to_hr")
    efficiency_deviation = efficiency_metric.get("deviation_pct")
    efficiency_score = normalize_response_ratio_deviation(
        efficiency_deviation,
        higher_is_better=True,
    )

    drift_metric = _baseline_metric(response_context, "aerobic_decoupling_pct")
    drift_current = drift_metric.get("current")
    drift_baseline = drift_metric.get("median")
    drift_delta_pp = (
        float(drift_current) - float(drift_baseline)
        if drift_current is not None and drift_baseline is not None
        else None
    )
    drift_score = normalize_response_drift(drift_current, drift_baseline)

    subjective_metric_name = None
    subjective_metric: dict[str, Any] = {}
    for candidate in ("session_rpe_load_per_tss", "rpe_per_intensity_factor"):
        candidate_metric = _baseline_metric(response_context, candidate)
        if candidate_metric.get("deviation_pct") is not None:
            subjective_metric_name = candidate
            subjective_metric = candidate_metric
            break
    subjective_deviation = subjective_metric.get("deviation_pct")
    subjective_score = normalize_response_ratio_deviation(
        subjective_deviation,
        higher_is_better=False,
    )

    components = {
        "efficiency": _component(
            metric="normalized_power_to_hr",
            score=efficiency_score,
            current=efficiency_metric.get("current"),
            baseline=efficiency_metric.get("median"),
            deviation=efficiency_deviation,
            deviation_unit="percent",
            direction="higher_is_better",
        ),
        "drift": _component(
            metric="aerobic_decoupling_pct",
            score=drift_score,
            current=drift_current,
            baseline=drift_baseline,
            deviation=drift_delta_pp,
            deviation_unit="percentage_points",
            direction="higher_is_worse",
        ),
        "subjective_cost": _component(
            metric=subjective_metric_name or "session_rpe_load_per_tss",
            score=subjective_score,
            current=subjective_metric.get("current"),
            baseline=subjective_metric.get("median"),
            deviation=subjective_deviation,
            deviation_unit="percent",
            direction="higher_is_worse",
        ),
    }

    objective_scores = [
        score for score in (efficiency_score, drift_score) if score is not None
    ]
    objective_score = round(mean(objective_scores), 1) if objective_scores else None
    channel_scores = [
        score for score in (objective_score, subjective_score) if score is not None
    ]
    response_score = round(mean(channel_scores), 1) if channel_scores else None

    reason_codes: list[str] = []
    recency = 0.0
    if age_days is None:
        reason_codes.append("response_target_date_unavailable")
    elif age_days < 0:
        reason_codes.append("response_activity_after_target_date")
    elif age_days >= RESPONSE_SCORING_WINDOW_DAYS:
        reason_codes.append("response_expired_for_scoring")
    else:
        # The response is fully current through the next day, then fades
        # linearly so a week-old session cannot carry yesterday's influence.
        recency = _clamp(
            1.0 - max(age_days - 1, 0) / (RESPONSE_SCORING_WINDOW_DAYS - 1),
            0.0,
            1.0,
        )

    if response_score is None:
        reason_codes.append("response_baseline_insufficient")

    configured_weight = (
        round(RESPONSE_MAX_CONFIGURED_WEIGHT * recency, 6)
        if response_score is not None
        else 0.0
    )
    return {
        "score": response_score,
        "configured_weight": configured_weight,
        "reason_codes": reason_codes,
        "data": {
            **response_context,
            "scoring": {
                "age_days": age_days,
                "recency": round(recency, 6),
                "components": components,
                "channels": {
                    "objective": objective_score,
                    "subjective": subjective_score,
                },
                "selected_subjective_metric": subjective_metric_name,
            },
        },
    }


def _family(
    *,
    availability: str,
    used: bool,
    score: float | None,
    configured_weight: float,
    effective_weight: float,
    contribution: float,
    reason_codes: list[str],
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "availability": availability,
        "used": used,
        "score": score,
        "configured_weight": configured_weight,
        "effective_weight": effective_weight,
        "contribution": contribution,
        "reason_codes": reason_codes,
        "data": data or {},
    }


def compose_readiness(
    *,
    load_context: dict[str, Any] | None,
    freshness: float | None,
    feeling_score: int | float | None,
    physiology_score: float | None,
    physiology_explanation: dict[str, Any] | None,
    response_context: dict[str, Any] | None = None,
    target_date: str | date | None = None,
) -> dict[str, Any]:
    """Compose readiness from available signal families without missing-data penalties.

    Load is exposed as context while freshness carries its score contribution,
    preventing the same load state from being counted twice. Response uses only
    comparable-session deviations, never absolute load inputs.
    """
    freshness_score = normalize_freshness(freshness)
    feeling_normalized = normalize_feeling(feeling_score)
    physiology_normalized = (
        _clamp(float(physiology_score), 0.0, 100.0)
        if physiology_score is not None
        else None
    )

    response = score_response_context(response_context, target_date=target_date)
    response_score = response["score"]
    response_weight = response["configured_weight"]
    recovery_evidence_budget = RECOVERY_EVIDENCE_WEIGHT - response_weight

    recovery_scores = {
        "feeling": feeling_normalized,
        "physiology": physiology_normalized,
    }
    available_recovery_evidence = [
        name for name, score in recovery_scores.items() if score is not None
    ]
    evidence_weight_each = (
        recovery_evidence_budget / len(available_recovery_evidence)
        if available_recovery_evidence
        else 0.0
    )

    configured_weights = {
        "freshness": FRESHNESS_CONFIGURED_WEIGHT if freshness_score is not None else 0.0,
        "response": response_weight,
        "feeling": evidence_weight_each if feeling_normalized is not None else 0.0,
        "physiology": evidence_weight_each if physiology_normalized is not None else 0.0,
    }
    configured_total = sum(configured_weights.values())
    if configured_total == 0.0:
        raise ValueError("at least one scored readiness signal must be available")

    effective_weights = {
        name: weight / configured_total for name, weight in configured_weights.items()
    }
    scored_values = {
        "freshness": freshness_score,
        "response": response_score,
        "feeling": feeling_normalized,
        "physiology": physiology_normalized,
    }
    contributions = {
        name: round((scored_values[name] or 0.0) * effective_weights[name], 3)
        for name in scored_values
    }
    readiness_score_raw = sum(contributions.values())
    readiness_score = _clamp(round(readiness_score_raw, 1), 0.0, 100.0)

    load_available = load_context is not None
    families = {
        "load": _family(
            availability="available" if load_available else "unavailable",
            used=False,
            score=None,
            configured_weight=0.0,
            effective_weight=0.0,
            contribution=0.0,
            reason_codes=[
                "load_context_exposed_via_freshness"
                if load_available
                else "load_state_unavailable"
            ],
            data=load_context,
        ),
        "freshness": _family(
            availability="available" if freshness_score is not None else "unavailable",
            used=freshness_score is not None,
            score=freshness_score,
            configured_weight=configured_weights["freshness"],
            effective_weight=effective_weights["freshness"],
            contribution=contributions["freshness"],
            reason_codes=[] if freshness_score is not None else ["freshness_unavailable"],
            data={"raw_freshness": freshness},
        ),
        "response": _family(
            availability="available" if response_context is not None else "unavailable",
            used=response_weight > 0.0,
            score=response_score,
            configured_weight=response_weight,
            effective_weight=effective_weights["response"],
            contribution=contributions["response"],
            reason_codes=response["reason_codes"],
            data=response["data"],
        ),
        "feeling": _family(
            availability="available" if feeling_normalized is not None else "unavailable",
            used=feeling_normalized is not None,
            score=feeling_normalized,
            configured_weight=configured_weights["feeling"],
            effective_weight=effective_weights["feeling"],
            contribution=contributions["feeling"],
            reason_codes=(
                [] if feeling_normalized is not None else ["morning_feeling_unavailable"]
            ),
            data={"scale": "1_5", "raw_score": feeling_score},
        ),
        "physiology": _family(
            availability="available" if physiology_normalized is not None else "unavailable",
            used=physiology_normalized is not None,
            score=physiology_normalized,
            configured_weight=configured_weights["physiology"],
            effective_weight=effective_weights["physiology"],
            contribution=contributions["physiology"],
            reason_codes=[] if physiology_normalized is not None else ["physiology_unavailable"],
            data={"explanation": physiology_explanation},
        ),
    }

    return {
        "readiness_score_raw": readiness_score_raw,
        "readiness_score": readiness_score,
        "signal_families": families,
        "reason_codes": [
            code
            for family in SIGNAL_FAMILIES
            for code in families[family]["reason_codes"]
        ],
        "model": {
            "name": READINESS_MODEL_NAME,
            "version": READINESS_MODEL_VERSION,
            "formula_version": READINESS_FORMULA_VERSION,
        },
    }
