import math

import requests

from backend.config import settings
from backend.db import get_conn


def _format_duration(seconds: int | None) -> str:
    if not seconds or seconds <= 0:
        return "n/a"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"

    return f"{minutes}:{secs:02d}"


def _fmt(value: float | None, digits: int = 1) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float) and math.isnan(value):
        return "n/a"
    return f"{value:.{digits}f}"


def compute_readiness_score(freshness: float | None) -> int | None:
    if freshness is None:
        return None

    score = round(50 + freshness * 5)
    score = max(0, min(100, score))
    return score


def describe_readiness(score: int | None) -> str:
    if score is None:
        return "n/a"
    if score <= 24:
        return "Высокая усталость"
    if score <= 44:
        return "Нагрузка"
    if score <= 64:
        return "Нормальная готовность"
    if score <= 84:
        return "Хорошая готовность"
    return "Очень свежий"


def build_training_processed_message(user_id: str, activity_id: int) -> str:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select
                    r.name,
                    r.start_date,
                    m.duration_s,
                    m.tss,
                    m.normalized_power,
                    m.intensity_factor,
                    m.avg_power,
                    m.avg_heartrate
                from strava_activity_raw r
                left join activity_metrics m
                  on m.strava_activity_id = r.strava_activity_id
                 and m.version = 'v1'
                where r.strava_activity_id = %s;
                """,
                (activity_id,),
            )
            activity_row = cur.fetchone()

            cur.execute(
                """
                select
                    fitness_signal,
                    fatigue_signal,
                    freshness_signal
                from daily_fitness_state
                where user_id = %s
                order by date desc
                limit 1;
                """,
                (user_id,),
            )
            state_row = cur.fetchone()

    if not activity_row:
        return f"Human Engine\n\nТренировка обработана\nactivity_id={activity_id}"

    (
        name,
        start_date,
        duration_s,
        tss,
        normalized_power,
        intensity_factor,
        avg_power,
        avg_heartrate,
    ) = activity_row

    fitness = None
    fatigue = None
    freshness = None

    if state_row:
        fitness, fatigue, freshness = state_row

    readiness_score = compute_readiness_score(freshness)
    readiness_text = describe_readiness(readiness_score)

    lines = [
        "Human Engine",
        "",
        "✅ Тренировка обработана",
        f"{name or 'Без названия'}",
        "",
        f"Дата: {start_date}",
        f"Длительность: {_format_duration(duration_s)}",
        f"TSS: {_fmt(tss, 1)}",
        f"NP: {_fmt(normalized_power, 1)} W",
        f"IF: {_fmt(intensity_factor, 2)}",
        f"Avg Power: {_fmt(avg_power, 1)} W",
        f"Avg HR: {_fmt(avg_heartrate, 1)}",
        "",
        "Состояние после обновления",
        f"Fitness: {_fmt(fitness, 2)}",
        f"Fatigue: {_fmt(fatigue, 2)}",
        f"Freshness: {_fmt(freshness, 2)}",
        "",
        f"Readiness: {readiness_score if readiness_score is not None else 'n/a'}/100",
        f"Статус: {readiness_text}",
        "",
        f"activity_id: {activity_id}",
    ]

    return "\n".join(lines)


def send_telegram_message(text: str) -> None:
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        return

    response = requests.post(
        f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
        json={
            "chat_id": settings.telegram_chat_id,
            "text": text,
        },
        timeout=30,
    )
    response.raise_for_status()


def notify_training_processed(user_id: str, activity_id: int) -> None:
    text = build_training_processed_message(user_id=user_id, activity_id=activity_id)
    send_telegram_message(text)