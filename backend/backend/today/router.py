from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Annotated
from urllib.parse import urlsplit

from fastapi import APIRouter, HTTPException, Path as FastAPIPath, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from backend.config import settings
from backend.services.subjective_feedback_service import (
    FEEDBACK_SOURCE_WEB,
    upsert_activity_subjective_feedback,
    upsert_next_day_recovery_feedback,
)

from . import service as today_service

router = APIRouter(prefix="/today", tags=["today"])
templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parents[1] / "templates")
)
FeedbackScore = Annotated[int, FastAPIPath(ge=1, le=5)]


def _reject_cross_site_request(request: Request) -> None:
    # Basic Auth protects the route at the edge. Sec-Fetch-Site adds a small,
    # deterministic CSRF boundary for state-changing native form submissions.
    if request.headers.get("sec-fetch-site", "").lower() == "cross-site":
        raise HTTPException(status_code=403, detail="cross-site form submission rejected")
    origin = request.headers.get("origin")
    if origin and urlsplit(origin).hostname != request.url.hostname:
        raise HTTPException(status_code=403, detail="cross-site form submission rejected")


def _redirect_to_today(*, saved: str, activity_id: int | None = None) -> RedirectResponse:
    location = f"/today?saved={saved}"
    if activity_id is not None:
        location += f"&activity_id={activity_id}"
    return RedirectResponse(location, status_code=303)


@router.get("")
@router.get("/")
def today_index(
    request: Request,
    activity_id: int | None = Query(default=None, ge=1),
    saved: str | None = Query(default=None),
):
    data = today_service.get_today_data(
        settings.daily_readiness_user_id,
        preferred_activity_id=activity_id,
    )
    return templates.TemplateResponse(
        request=request,
        name="today/index.html",
        context={
            "page_title": "Whatte Today",
            "saved": saved if saved in {"recovery", "rpe"} else None,
            **asdict(data),
        },
    )


@router.post("/recovery/{score}")
def submit_recovery(request: Request, score: FeedbackScore):
    _reject_cross_site_request(request)
    target_date = today_service.get_local_today()
    upsert_next_day_recovery_feedback(
        user_id=settings.daily_readiness_user_id,
        target_date=target_date,
        score=score,
        source=FEEDBACK_SOURCE_WEB,
    )
    return _redirect_to_today(saved="recovery")


@router.post("/rpe/{activity_id}/{score}")
def submit_rpe(
    request: Request,
    activity_id: Annotated[int, FastAPIPath(ge=1)],
    score: FeedbackScore,
):
    _reject_cross_site_request(request)
    activity = today_service.get_today_activity(
        settings.daily_readiness_user_id,
        preferred_activity_id=activity_id,
    )
    if activity is None:
        raise HTTPException(status_code=404, detail="eligible activity not found")
    upsert_activity_subjective_feedback(
        activity_id=activity_id,
        score=score,
        source=FEEDBACK_SOURCE_WEB,
    )
    return _redirect_to_today(saved="rpe", activity_id=activity_id)
