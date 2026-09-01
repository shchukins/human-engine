from __future__ import annotations

from typing import Any

from backend.services.load_state_v2 import recompute_load_state_daily_v2
from backend.services.readiness_daily import recompute_readiness_daily_for_date


def recompute_daily_readiness(
    *,
    user_id: str,
    target_date: str,
) -> dict[str, Any]:
    """Materialize the core daily loop without requiring physiology data."""
    load_state = recompute_load_state_daily_v2(
        user_id=user_id,
        through_date=target_date,
    )
    readiness = recompute_readiness_daily_for_date(
        user_id=user_id,
        target_date=target_date,
    )
    return {
        "ok": True,
        "user_id": user_id,
        "date": target_date,
        "load_state": load_state,
        "readiness": readiness,
    }
