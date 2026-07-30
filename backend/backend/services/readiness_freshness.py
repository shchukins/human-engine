from __future__ import annotations

from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def _as_date(value: date | datetime | str | None) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        except ValueError:
            return None


def _evaluation_date(
    value: date | datetime | str,
    timezone_name: str,
) -> date | None:
    if isinstance(value, str):
        try:
            parsed_value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return _as_date(value)
        if parsed_value.tzinfo is None:
            return None
        value = parsed_value
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return None
        timezone_name = timezone_name.rsplit(" ", 1)[-1]
        try:
            local_timezone = ZoneInfo(timezone_name)
        except (ZoneInfoNotFoundError, ValueError):
            return None
        return value.astimezone(local_timezone).date()
    return _as_date(value)


def classify_readiness_freshness(
    *,
    readiness_date: date | str,
    readiness_computed_at: datetime | str | None,
    recovery_source_at: date | datetime | str | None,
    training_source_at: date | datetime | str | None,
    evaluation_date: date | datetime | str,
    timezone: str,
    data_quality: dict[str, Any],
) -> dict[str, Any]:
    """Classify source-data freshness using only supplied, snapshotted evidence.

    A source is current when its local/source date equals the readiness target
    date. Older evidence is stale; missing or unusable evidence is missing.
    Supported one-family readiness fallbacks are partial when their available
    family is current.
    """
    target_date = _as_date(readiness_date)
    recovery_date = _as_date(recovery_source_at)
    training_date = _as_date(training_source_at)
    local_evaluation_date = _evaluation_date(evaluation_date, timezone)
    computed_date = (
        _evaluation_date(readiness_computed_at, timezone)
        if readiness_computed_at is not None
        else None
    )
    fallback_mode = data_quality.get("fallback_mode")
    reasons: list[str] = []

    if target_date is None or local_evaluation_date is None:
        return {
            "freshness_state": "missing",
            "freshness_reason_codes": ["readiness_freshness_context_invalid"],
        }

    if readiness_computed_at is None or computed_date is None:
        reasons.append("readiness_computed_at_missing")
    elif computed_date < target_date:
        reasons.append("readiness_computed_at_before_readiness_date")

    if target_date < local_evaluation_date:
        reasons.append("readiness_date_before_local_today")
    elif target_date > local_evaluation_date:
        reasons.append("readiness_date_after_local_today")

    if recovery_source_at is None or recovery_date is None:
        reasons.append("recovery_source_missing")
    elif recovery_date < target_date:
        reasons.append("recovery_source_stale")
    elif recovery_date > target_date:
        reasons.append("recovery_source_after_readiness_date")

    if training_source_at is None or training_date is None:
        reasons.append("training_source_missing")
    elif training_date < target_date:
        reasons.append("training_source_stale")
    elif training_date > target_date:
        reasons.append("training_source_after_readiness_date")

    missing_reasons = {
        "readiness_computed_at_missing",
        "recovery_source_missing",
        "training_source_missing",
        "readiness_date_after_local_today",
        "recovery_source_after_readiness_date",
        "training_source_after_readiness_date",
    }
    stale_reasons = {
        "readiness_computed_at_before_readiness_date",
        "readiness_date_before_local_today",
        "recovery_source_stale",
        "training_source_stale",
    }

    supported_missing_reason = None
    if fallback_mode == "recovery_only":
        supported_missing_reason = "training_source_missing"
        reasons.append("fallback_recovery_only")
    elif fallback_mode == "load_only":
        supported_missing_reason = "recovery_source_missing"
        reasons.append("fallback_load_only")

    unsupported_missing = {
        reason for reason in reasons if reason in missing_reasons
    } - ({supported_missing_reason} if supported_missing_reason else set())

    if unsupported_missing:
        state = "missing"
    elif any(reason in stale_reasons for reason in reasons):
        state = "stale"
    elif supported_missing_reason in reasons:
        state = "partial"
    else:
        state = "fresh"

    return {
        "freshness_state": state,
        "freshness_reason_codes": reasons,
    }
