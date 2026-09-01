from __future__ import annotations

import json
from typing import Any


HISTORICAL_PHYSIOLOGY_PROVIDER = "healthkit"


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def load_physiology_signal(
    cur: Any,
    *,
    user_id: str,
    target_date: str,
) -> dict[str, Any]:
    """Load optional physiology through a provider-neutral readiness boundary.

    HealthKit collection is retired. Existing exact-date recovery rows remain
    valid historical evidence, but are never carried forward to a later date.
    """
    cur.execute(
        """
        select
            recovery_score_simple,
            recovery_explanation_json,
            updated_at
        from health_recovery_daily
        where user_id = %s
          and date = %s;
        """,
        (user_id, target_date),
    )
    row = cur.fetchone()
    if row is None:
        return {
            "availability": "unavailable",
            "score": None,
            "explanation": None,
            "source_date": None,
            "provider": None,
            "updated_at": None,
        }

    score, raw_explanation, updated_at = row
    explanation = _as_dict(raw_explanation)
    explanation["provider"] = HISTORICAL_PHYSIOLOGY_PROVIDER
    explanation["collection_status"] = "historical"
    return {
        "availability": "available",
        "score": score,
        "explanation": explanation,
        "source_date": target_date,
        "provider": HISTORICAL_PHYSIOLOGY_PROVIDER,
        "updated_at": updated_at,
    }
