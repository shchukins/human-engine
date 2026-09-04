from contextlib import nullcontext
from datetime import date

import pytest

from backend.services.notification_service import (
    DailyReadinessDeliveryClaim,
    _incoming_daily_readiness_is_newer,
    build_briefing_text,
    build_daily_readiness_message,
    build_readiness_briefing_message,
    build_training_processed_message,
    build_readiness_comment,
    build_workout_comment,
    classify_workout_type,
    compute_readiness_score,
    compute_training_impact,
    describe_readiness,
    describe_freshness_trend,
    describe_training_impact,
    get_physiology_data_freshness,
    recommend_training,
    notify_training_processed,
    send_daily_readiness,
)


@pytest.fixture(autouse=True)
def _disable_daily_readiness_delivery_lock(monkeypatch):
    monkeypatch.setattr(
        "backend.services.notification_service._daily_readiness_delivery_lock",
        lambda user_id, notification_date: nullcontext(),
    )
    monkeypatch.setattr(
        "backend.services.notification_service.capture_decision_context_snapshot",
        lambda **kwargs: {"inserted": True, **kwargs},
    )

def test_compute_readiness_score_none():
    assert compute_readiness_score(None) is None


def test_compute_readiness_score_low_bound():
    assert compute_readiness_score(-10) == 0


def test_compute_readiness_score_middle():
    assert compute_readiness_score(0) == 50


def test_compute_readiness_score_positive():
    assert compute_readiness_score(5) == 75


def test_compute_readiness_score_high_bound():
    assert compute_readiness_score(20) == 100


def test_describe_readiness_low():
    assert describe_readiness(10) == "Высокая усталость"


def test_describe_readiness_load():
    assert describe_readiness(30) == "Нагрузка"


def test_describe_readiness_normal():
    assert describe_readiness(50) == "Нормальная готовность"


def test_describe_readiness_good():
    assert describe_readiness(70) == "Хорошая готовность"


def test_describe_readiness_very_fresh():
    assert describe_readiness(95) == "Очень свежий"


def test_describe_freshness_trend_improving():
    assert describe_freshness_trend([-8.0, -5.0, -2.0]) == "improving"


def test_describe_freshness_trend_declining():
    assert describe_freshness_trend([3.0, 0.0, -3.0]) == "declining"


def test_describe_freshness_trend_stable():
    assert describe_freshness_trend([-3.0, -2.5, -2.0]) == "stable"


def test_describe_freshness_trend_not_enough_data():
    assert describe_freshness_trend([1.0]) == "n/a"


def test_recommend_training_no_data():
    assert recommend_training(None, "n/a") == "Недостаточно данных"


def test_recommend_training_very_low_score():
    assert recommend_training(20, "declining") == "Отдых или очень легкое восстановление"


def test_recommend_training_low_score_improving():
    assert recommend_training(40, "improving") == "Легкая endurance тренировка, без интенсивности"


def test_recommend_training_low_score_default():
    assert recommend_training(40, "stable") == "Легкая тренировка в восстановительном темпе"


def test_recommend_training_mid_score_declining():
    assert recommend_training(55, "declining") == "Спокойная endurance тренировка, лучше без интервальной работы"


def test_recommend_training_mid_score_improving():
    assert recommend_training(55, "improving") == "Можно делать умеренную тренировку"


def test_recommend_training_good_score_improving():
    assert recommend_training(75, "improving") == "Хороший день для качественной тренировки"


def test_recommend_training_good_score_declining():
    assert recommend_training(75, "declining") == "Умеренная тренировка, но без максимальной интенсивности"


def test_recommend_training_very_high_score_declining():
    assert recommend_training(95, "declining") == "Можно тренироваться интенсивно, но стоит контролировать самочувствие"


def test_recommend_training_very_high_score_default():
    assert recommend_training(95, "stable") == "Подходит день для интенсивной тренировки"


def test_build_briefing_text_no_data():
    assert build_briefing_text(None, "n/a", None, None) == "Недостаточно данных для интерпретации состояния."


def test_build_briefing_text_low_score_declining():
    assert build_briefing_text(20, "declining", 10.0, 20.0) == "Сегодня лучше восстановиться. Свежесть низкая, тренд ухудшается."


def test_build_briefing_text_low_score_heavy_recent_load():
    assert build_briefing_text(20, "stable", 65.0, 40.0) == "Сегодня лучше восстановиться. Недавняя нагрузка была высокой."


def test_build_briefing_text_low_score_default():
    assert build_briefing_text(20, "stable", 10.0, 20.0) == "Сегодня лучше восстановиться. Организм выглядит утомленным."


def test_build_briefing_text_mid_low_improving():
    assert build_briefing_text(40, "improving", 10.0, 20.0) == "Состояние еще ограничено, но есть признаки восстановления."


def test_build_briefing_text_mid_low_default():
    assert build_briefing_text(40, "stable", 10.0, 20.0) == "Состояние умеренно утомленное. Лучше держать нагрузку легкой."


def test_build_briefing_text_mid_declining():
    assert build_briefing_text(55, "declining", 10.0, 20.0) == "Состояние нормальное, но тренд ухудшается. Лучше не форсировать нагрузку."


def test_build_briefing_text_mid_improving():
    assert build_briefing_text(55, "improving", 10.0, 20.0) == "Состояние нормальное и улучшается. Подходит день для умеренной тренировки."


def test_build_briefing_text_mid_default():
    assert build_briefing_text(55, "stable", 10.0, 20.0) == "Состояние нормальное. Подходит день для спокойной endurance тренировки."


def test_build_briefing_text_good_declining():
    assert build_briefing_text(75, "declining", 10.0, 20.0) == "Состояние хорошее, но тренд не улучшается. Лучше избегать максимальной интенсивности."


def test_build_briefing_text_good_heavy_recent_load():
    assert build_briefing_text(75, "stable", 65.0, 40.0) == "Состояние хорошее, но недавняя нагрузка была заметной. Контролируй самочувствие."


def test_build_briefing_text_good_default():
    assert build_briefing_text(75, "stable", 10.0, 20.0) == "Хороший день для качественной работы."


def test_build_briefing_text_very_good_declining():
    assert build_briefing_text(95, "declining", 10.0, 20.0) == "Состояние очень хорошее, но тренд снижается. Интенсивность допустима, но без лишнего риска."


def test_build_briefing_text_very_good_default():
    assert build_briefing_text(95, "stable", 10.0, 20.0) == "Очень хороший день для интенсивной тренировки."


def test_build_readiness_comment_without_breakdown():
    assert (
        build_readiness_comment(
            freshness=2.0,
            recovery_score_simple=58.0,
            recovery_explanation=None,
        )
        == "Восстановление выглядит стабильно, но деталей по breakdown пока недостаточно."
    )


def test_build_readiness_comment_sleep_is_lowest():
    assert (
        build_readiness_comment(
            freshness=1.0,
            recovery_score_simple=56.5,
            recovery_explanation={
                "sleep_score": 42.0,
                "hrv_score": 61.0,
                "rhr_score": 58.0,
            },
        )
        == "Основной ограничивающий фактор сегодня — сон."
    )


def test_build_readiness_comment_hrv_is_lowest():
    assert (
        build_readiness_comment(
            freshness=0.5,
            recovery_score_simple=56.5,
            recovery_explanation={
                "sleep_score": 82.8,
                "hrv_score": 42.1,
                "rhr_score": 49.5,
            },
        )
        == "HRV ниже baseline, восстановление выглядит неполным."
    )


def test_build_readiness_comment_rhr_is_lowest():
    assert (
        build_readiness_comment(
            freshness=0.0,
            recovery_score_simple=56.5,
            recovery_explanation={
                "sleep_score": 82.8,
                "hrv_score": 72.0,
                "rhr_score": 41.0,
            },
        )
        == "Пульс покоя выше обычного, это может указывать на неполное восстановление."
    )


def test_build_readiness_comment_good_recovery_and_freshness():
    assert (
        build_readiness_comment(
            freshness=6.0,
            recovery_score_simple=78.0,
            recovery_explanation={
                "sleep_score": 85.0,
                "hrv_score": 79.0,
                "rhr_score": 77.0,
            },
        )
        == "Состояние выглядит хорошим: и свежесть, и восстановление на хорошем уровне."
    )


def test_build_readiness_comment_negative_freshness():
    assert (
        build_readiness_comment(
            freshness=-6.0,
            recovery_score_simple=72.0,
            recovery_explanation={
                "sleep_score": 85.0,
                "hrv_score": 79.0,
                "rhr_score": 77.0,
            },
        )
        == "Есть признаки накопленной усталости, сегодня лучше контролировать нагрузку."
    )


def test_build_readiness_briefing_message_uses_model_v2_fields():
    message = build_readiness_briefing_message(
        notification_date="2026-04-17",
        recovery_date="2026-04-17",
        readiness_score=56.5,
        status_text="Нормальная готовность",
        good_day_probability=0.565,
        freshness=5.0,
        recovery_score_simple=56.5,
        recovery_explanation={
            "sleep_score": 82.8,
            "hrv_score": 42.1,
            "rhr_score": 49.5,
        },
    )

    assert message == (
        "WHATTE · Today\n\n"
        "Дата briefing: 2026-04-17\n"
        "Дата physiology-данных: 2026-04-17\n"
        "Physiology: unavailable (optional)\n\n"
        "Готовность: 56.5\n"
        "Статус: Нормальная готовность\n"
        "Вероятность хорошего дня: 56%\n\n"
        "Свежесть: 5.0\n"
        "Восстановление: 56.5\n\n"
        "Восстановление:\n"
        "• Сон: 82.8\n"
        "• HRV: 42.1\n"
        "• Пульс покоя: 49.5\n\n"
        "Комментарий:\n"
        "HRV ниже baseline, восстановление выглядит неполным."
    )


class _FakeDailyReadinessCursor:
    def __init__(self) -> None:
        self.execute_calls: list[tuple[str, tuple]] = []
        self._last_query = ""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, query, params):
        self.execute_calls.append((query, params))
        self._last_query = query

    def fetchone(self):
        if "from readiness_daily" in self._last_query:
            return (
                "2026-04-17",
                56.5,
                0.565,
                "Нормальная готовность",
                {
                    "freshness": 5.0,
                    "recovery_score_simple": 56.5,
                    "recovery_explanation": {
                        "sleep_score": 82.8,
                        "hrv_score": 42.1,
                        "rhr_score": 49.5,
                    },
                    "source_timestamps": {
                        "recovery_source_at": "2026-04-17",
                    },
                },
            )
        raise AssertionError(f"unexpected fetchone query: {self._last_query}")

    def fetchall(self):
        raise AssertionError(f"unexpected fetchall query: {self._last_query}")


class _FakeDailyReadinessConn:
    def __init__(self, cursor) -> None:
        self._cursor = cursor

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return self._cursor


def test_build_daily_readiness_message_prefers_readiness_daily_v2(monkeypatch):
    fake_cursor = _FakeDailyReadinessCursor()
    fake_conn = _FakeDailyReadinessConn(fake_cursor)

    monkeypatch.setattr(
        "backend.services.notification_service.get_conn",
        lambda: fake_conn,
    )

    message = build_daily_readiness_message(
        user_id="user-1",
        data_freshness={"state": "fresh", "provider": "healthkit"},
    )

    assert message == (
        "WHATTE · Today\n\n"
        "Дата briefing: 2026-04-17\n"
        "Дата physiology-данных: 2026-04-17\n"
        "Physiology: available · historical\n\n"
        "Готовность: 56.5\n"
        "Статус: Нормальная готовность\n"
        "Вероятность хорошего дня: 56%\n\n"
        "Свежесть: 5.0\n"
        "Восстановление: 56.5\n\n"
        "Восстановление:\n"
        "• Сон: 82.8\n"
        "• HRV: 42.1\n"
        "• Пульс покоя: 49.5\n\n"
        "Комментарий:\n"
        "Сегодня нормальная готовность. Рекомендуется спокойная аэробная тренировка."
    )

    assert len(fake_cursor.execute_calls) == 1
    assert "from readiness_daily" in fake_cursor.execute_calls[0][0]


def test_build_readiness_briefing_message_marks_stale_data():
    message = build_readiness_briefing_message(
        notification_date="2026-04-17",
        recovery_date="2026-04-16",
        readiness_score=50.0,
        status_text="Нормальная готовность",
        good_day_probability=0.5,
        freshness=0.0,
        recovery_score_simple=50.0,
        recovery_explanation={},
        data_freshness={"state": "stale"},
    )

    assert "Physiology: unavailable for this date" in message


class _FakeFreshnessCursor:
    def __init__(self, recovery_row):
        self.recovery_row = recovery_row

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, query, params):
        return None

    def fetchone(self):
        return self.recovery_row


@pytest.mark.parametrize(
    ("recovery_row", "expected_state"),
    [
        ((date(2026, 4, 17), "recovery-updated-at"), "fresh"),
        (None, "missing"),
    ],
)
def test_get_physiology_data_freshness_uses_exact_date_only(
    monkeypatch,
    recovery_row,
    expected_state,
):
    cursor = _FakeFreshnessCursor(recovery_row=recovery_row)
    connection = _FakeDailyReadinessConn(cursor)
    monkeypatch.setattr(
        "backend.services.notification_service.get_conn",
        lambda: connection,
    )

    result = get_physiology_data_freshness(
        user_id="user-1",
        for_date=date(2026, 4, 17),
    )

    assert result["state"] == expected_state
    assert result["provider"] == ("healthkit" if recovery_row else None)


def test_send_daily_readiness_claim_prevents_duplicate(monkeypatch):
    telegram_calls = []

    monkeypatch.setattr(
        "backend.services.notification_service.claim_daily_readiness",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        "backend.services.notification_service.build_daily_readiness_message",
        lambda **kwargs: "briefing",
    )
    monkeypatch.setattr(
        "backend.services.notification_service.send_telegram_message",
        lambda text: telegram_calls.append(text),
    )

    sent = send_daily_readiness(
        "user-1",
        notification_date=date(2026, 4, 17),
        data_freshness={"state": "fresh"},
    )

    assert sent is False
    assert telegram_calls == []


def test_send_daily_readiness_releases_claim_when_delivery_fails(monkeypatch):
    released = []

    monkeypatch.setattr(
        "backend.services.notification_service.claim_daily_readiness",
        lambda **kwargs: DailyReadinessDeliveryClaim(action="send"),
    )
    monkeypatch.setattr(
        "backend.services.notification_service.build_daily_readiness_message",
        lambda **kwargs: "briefing",
    )
    monkeypatch.setattr(
        "backend.services.notification_service.send_telegram_message",
        lambda text: (_ for _ in ()).throw(RuntimeError("telegram unavailable")),
    )
    monkeypatch.setattr(
        "backend.services.notification_service.release_daily_readiness_claim",
        lambda **kwargs: released.append(kwargs),
    )

    with pytest.raises(RuntimeError, match="telegram unavailable"):
        send_daily_readiness(
            "user-1",
            notification_date=date(2026, 4, 17),
            data_freshness={"state": "fresh"},
        )

    assert released == [
        {
            "user_id": "user-1",
            "notification_date": date(2026, 4, 17),
            "previous_delivery_status": None,
        }
    ]


def test_send_daily_readiness_keeps_claim_after_successful_delivery(monkeypatch):
    released = []

    monkeypatch.setattr(
        "backend.services.notification_service.claim_daily_readiness",
        lambda **kwargs: DailyReadinessDeliveryClaim(action="send"),
    )
    monkeypatch.setattr(
        "backend.services.notification_service.build_daily_readiness_message",
        lambda **kwargs: "briefing",
    )
    monkeypatch.setattr(
        "backend.services.notification_service.send_telegram_message",
        lambda text: None,
    )
    monkeypatch.setattr(
        "backend.services.notification_service.mark_daily_readiness_sent",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("database unavailable")),
    )
    monkeypatch.setattr(
        "backend.services.notification_service.release_daily_readiness_claim",
        lambda **kwargs: released.append(kwargs),
    )

    with pytest.raises(RuntimeError, match="database unavailable"):
        send_daily_readiness(
            "user-1",
            notification_date=date(2026, 4, 17),
            data_freshness={"state": "fresh"},
        )

    assert released == []


def test_no_briefing_fresh_sync_sends_message(monkeypatch):
    sent_messages = []
    marked = []
    snapshots = []
    monkeypatch.setattr(
        "backend.services.notification_service.capture_decision_context_snapshot",
        lambda **kwargs: snapshots.append(kwargs),
    )
    monkeypatch.setattr(
        "backend.services.notification_service.build_daily_readiness_message",
        lambda **kwargs: "fresh briefing",
    )
    monkeypatch.setattr(
        "backend.services.notification_service.claim_daily_readiness",
        lambda **kwargs: DailyReadinessDeliveryClaim(action="send"),
    )
    monkeypatch.setattr(
        "backend.services.notification_service.send_telegram_message",
        lambda text: sent_messages.append(text)
        or {"result": {"message_id": 101, "chat": {"id": 202}}},
    )
    monkeypatch.setattr(
        "backend.services.notification_service.mark_daily_readiness_sent",
        lambda **kwargs: marked.append(kwargs),
    )

    assert send_daily_readiness(
        "user-1",
        notification_date=date(2026, 8, 2),
        recovery_date=date(2026, 8, 2),
        data_freshness={"state": "fresh", "recovery_date": "2026-08-02"},
    ) is True

    assert sent_messages == ["fresh briefing"]
    assert marked[0]["delivery_status"] == "sent"
    assert marked[0]["telegram_chat_id"] == 202
    assert marked[0]["telegram_message_id"] == 101
    assert snapshots == [{
        "user_id": "user-1",
        "snapshot_date": date(2026, 8, 2),
        "event_type": "daily_readiness_delivery",
        "reference_key": "daily_readiness:user-1:2026-08-02",
    }]


def test_stale_fallback_then_fresh_sync_edits_existing_message(monkeypatch):
    edits = []
    ordinary_messages = []
    marked = []
    monkeypatch.setattr(
        "backend.services.notification_service.build_daily_readiness_message",
        lambda **kwargs: "fresh score 50.8",
    )
    monkeypatch.setattr(
        "backend.services.notification_service.claim_daily_readiness",
        lambda **kwargs: DailyReadinessDeliveryClaim(
            action="edit",
            previous_delivery_status="sent",
            telegram_chat_id="chat-1",
            telegram_message_id=303,
        ),
    )
    monkeypatch.setattr(
        "backend.services.notification_service.edit_telegram_message",
        lambda chat_id, message_id, text: edits.append((chat_id, message_id, text))
        or {"result": {"message_id": message_id, "chat": {"id": chat_id}}},
    )
    monkeypatch.setattr(
        "backend.services.notification_service.send_telegram_message",
        lambda text: ordinary_messages.append(text),
    )
    monkeypatch.setattr(
        "backend.services.notification_service.mark_daily_readiness_sent",
        lambda **kwargs: marked.append(kwargs),
    )

    assert send_daily_readiness(
        "user-1",
        notification_date=date(2026, 8, 2),
        recovery_date=date(2026, 8, 2),
        data_freshness={"state": "fresh", "recovery_date": "2026-08-02"},
    ) is True

    assert edits == [("chat-1", 303, "fresh score 50.8")]
    assert ordinary_messages == []
    assert marked[0]["delivery_status"] == "updated"


def test_fresh_briefing_repeated_sync_is_noop(monkeypatch):
    sends = []
    edits = []
    monkeypatch.setattr(
        "backend.services.notification_service.build_daily_readiness_message",
        lambda **kwargs: "same fresh briefing",
    )
    monkeypatch.setattr(
        "backend.services.notification_service.claim_daily_readiness",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        "backend.services.notification_service.send_telegram_message",
        lambda text: sends.append(text),
    )
    monkeypatch.setattr(
        "backend.services.notification_service.edit_telegram_message",
        lambda *args: edits.append(args),
    )

    assert send_daily_readiness(
        "user-1",
        notification_date=date(2026, 8, 2),
        recovery_date=date(2026, 8, 2),
        data_freshness={"state": "fresh", "recovery_date": "2026-08-02"},
    ) is False
    assert sends == []
    assert edits == []


def test_newer_recovery_date_is_an_update():
    assert _incoming_daily_readiness_is_newer(
        current_recovery_date=date(2026, 8, 1),
        current_freshness_status="stale",
        current_content_fingerprint="old",
        incoming_recovery_date=date(2026, 8, 2),
        incoming_freshness_status="fresh",
        incoming_content_fingerprint="new",
    ) is True


def test_same_recovery_date_updates_only_when_content_fingerprint_changes():
    common = {
        "current_recovery_date": date(2026, 8, 2),
        "current_freshness_status": "fresh",
        "incoming_recovery_date": date(2026, 8, 2),
        "incoming_freshness_status": "fresh",
    }
    assert _incoming_daily_readiness_is_newer(
        **common,
        current_content_fingerprint="score-50.8",
        incoming_content_fingerprint="score-50.8",
    ) is False
    assert _incoming_daily_readiness_is_newer(
        **common,
        current_content_fingerprint="score-52.2",
        incoming_content_fingerprint="score-50.8",
    ) is True


def test_repeated_identical_sync_after_update_is_noop():
    assert _incoming_daily_readiness_is_newer(
        current_recovery_date=date(2026, 8, 2),
        current_freshness_status="fresh",
        current_content_fingerprint="updated-content",
        incoming_recovery_date=date(2026, 8, 2),
        incoming_freshness_status="fresh",
        incoming_content_fingerprint="updated-content",
    ) is False


def test_telegram_edit_failure_sends_one_fallback_update(monkeypatch):
    claims = iter(
        [
            DailyReadinessDeliveryClaim(
                action="edit",
                previous_delivery_status="sent",
                telegram_chat_id="chat-1",
                telegram_message_id=303,
            ),
            None,
        ]
    )
    fallback_messages = []
    marked = []
    monkeypatch.setattr(
        "backend.services.notification_service.build_daily_readiness_message",
        lambda **kwargs: "fresh score 50.8",
    )
    monkeypatch.setattr(
        "backend.services.notification_service.claim_daily_readiness",
        lambda **kwargs: next(claims),
    )
    monkeypatch.setattr(
        "backend.services.notification_service.edit_telegram_message",
        lambda *args: (_ for _ in ()).throw(RuntimeError("message cannot be edited")),
    )
    monkeypatch.setattr(
        "backend.services.notification_service.send_telegram_message",
        lambda text: fallback_messages.append(text)
        or {"result": {"message_id": 404, "chat": {"id": "chat-1"}}},
    )
    monkeypatch.setattr(
        "backend.services.notification_service.mark_daily_readiness_sent",
        lambda **kwargs: marked.append(kwargs),
    )

    kwargs = {
        "notification_date": date(2026, 8, 2),
        "recovery_date": date(2026, 8, 2),
        "data_freshness": {"state": "fresh", "recovery_date": "2026-08-02"},
    }
    assert send_daily_readiness("user-1", **kwargs) is True
    assert send_daily_readiness("user-1", **kwargs) is False

    assert fallback_messages == ["ОБНОВЛЕНИЕ\n\nfresh score 50.8"]
    assert marked[0]["delivery_status"] == "superseded"
    assert marked[0]["telegram_message_id"] == 404


def test_fallback_worker_cannot_overwrite_newer_fresh_briefing():
    assert _incoming_daily_readiness_is_newer(
        current_recovery_date=date(2026, 8, 2),
        current_freshness_status="fresh",
        current_content_fingerprint="fresh-content",
        incoming_recovery_date=date(2026, 7, 30),
        incoming_freshness_status="stale",
        incoming_content_fingerprint="stale-content",
    ) is False


def test_classify_workout_type_unknown():
    assert classify_workout_type(None, 50.0, 3600) == "unknown"


def test_classify_workout_type_recovery():
    assert classify_workout_type(0.50, 20.0, 3600) == "recovery"


def test_classify_workout_type_endurance():
    assert classify_workout_type(0.73, 60.0, 4200) == "endurance"


def test_classify_workout_type_long_endurance():
    assert classify_workout_type(0.70, 90.0, 8000) == "long_endurance"


def test_classify_workout_type_tempo():
    assert classify_workout_type(0.80, 70.0, 3600) == "tempo"


def test_classify_workout_type_threshold():
    assert classify_workout_type(0.90, 85.0, 3600) == "threshold"


def test_classify_workout_type_vo2():
    assert classify_workout_type(0.98, 95.0, 3600) == "vo2"


def test_build_workout_comment_recovery():
    assert build_workout_comment("recovery", 20.0) == "Легкая восстановительная сессия"


def test_build_workout_comment_endurance_default():
    assert build_workout_comment("endurance", 60.0) == "Хорошая аэробная работа"


def test_build_workout_comment_endurance_high_tss():
    assert build_workout_comment("endurance", 85.0) == "Хорошая аэробная работа с заметной нагрузкой"


def test_build_workout_comment_long_endurance():
    assert build_workout_comment("long_endurance", 90.0) == "Длинная аэробная сессия"


def test_build_workout_comment_tempo():
    assert build_workout_comment("tempo", 70.0) == "Умеренно интенсивная работа"


def test_build_workout_comment_threshold():
    assert build_workout_comment("threshold", 85.0) == "Пороговая нагрузка"


def test_build_workout_comment_vo2():
    assert build_workout_comment("vo2", 100.0) == "Высокоинтенсивная тренировка"


def test_build_workout_comment_unknown():
    assert build_workout_comment("unknown", 50.0) == "Тип нагрузки пока не определен"


def test_compute_training_impact_no_data():
    result = compute_training_impact(None, None, 10.0, -5.0)

    assert result["delta_fatigue"] is None
    assert result["delta_freshness"] is None


def test_compute_training_impact_with_values():
    result = compute_training_impact(
        prev_fatigue=20.0,
        prev_freshness=-4.0,
        new_fatigue=27.5,
        new_freshness=-10.5,
    )

    assert result["delta_fatigue"] == 7.5
    assert result["delta_freshness"] == -6.5


def test_describe_training_impact_no_data():
    assert describe_training_impact(None, None) == "Недостаточно данных для оценки влияния"


def test_describe_training_impact_strong_load():
    assert describe_training_impact(9.0, -7.0) == "Сильная нагрузка, значительный рост усталости"


def test_describe_training_impact_noticeable_load():
    assert describe_training_impact(5.0, -4.0) == "Заметная тренировочная нагрузка"


def test_describe_training_impact_moderate_load():
    assert describe_training_impact(2.0, -2.0) == "Умеренная нагрузка"


def test_describe_training_impact_light_load():
    assert describe_training_impact(0.5, -0.5) == "Легкая нагрузка"


class _FakeTrainingProcessedCursor:
    def __init__(self, activity_row, state_rows) -> None:
        self.activity_row = activity_row
        self.state_rows = state_rows
        self._last_query = ""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, query, params):
        self._last_query = query

    def fetchone(self):
        if "from strava_activity_raw" in self._last_query:
            return self.activity_row
        if "from daily_fitness_state" in self._last_query:
            return self.state_rows[0] if self.state_rows else None
        raise AssertionError(f"unexpected fetchone query: {self._last_query}")

    def fetchall(self):
        if "from daily_fitness_state" in self._last_query:
            return self.state_rows
        raise AssertionError(f"unexpected fetchall query: {self._last_query}")


class _FakeTrainingProcessedConn:
    def __init__(self, cursor) -> None:
        self._cursor = cursor

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return self._cursor


def test_build_training_processed_message_for_unsupported_activity(monkeypatch):
    fake_cursor = _FakeTrainingProcessedCursor(
        activity_row=(
            "Table Tennis",
            "2026-04-17T18:00:00Z",
            "TableTennis",
            3600,
            None,
            None,
            None,
            None,
            128.0,
        ),
        state_rows=[],
    )
    fake_conn = _FakeTrainingProcessedConn(fake_cursor)

    monkeypatch.setattr(
        "backend.services.notification_service.get_conn",
        lambda: fake_conn,
    )

    message = build_training_processed_message(user_id="user-1", activity_id=42)

    assert "Type: unsupported" in message
    assert "Load model: unsupported" in message
    assert (
        "Comment: Activity stored, but excluded from daily load aggregation and readiness impact because reliable load estimate is not available."
        in message
    )
    assert "Impact:\nUnsupported and excluded" in message
    assert "Fatigue Δ" not in message
    assert "Freshness Δ" not in message
    assert "Легкая нагрузка" not in message


def test_build_training_processed_message_for_supported_cycling_activity(monkeypatch):
    fake_cursor = _FakeTrainingProcessedCursor(
        activity_row=(
            "Evening Ride",
            "2026-04-17T18:00:00Z",
            "Ride",
            5400,
            72.5,
            210.0,
            0.84,
            185.0,
            142.0,
        ),
        state_rows=[
            (55.0, 31.0, -4.0),
            (53.0, 26.0, 0.5),
        ],
    )
    fake_conn = _FakeTrainingProcessedConn(fake_cursor)

    monkeypatch.setattr(
        "backend.services.notification_service.get_conn",
        lambda: fake_conn,
    )

    message = build_training_processed_message(user_id="user-1", activity_id=43)

    assert "Type: tempo" in message
    assert "Load model: power_tss" in message
    assert "Fatigue Δ: 5.00" in message
    assert "Freshness Δ: -4.50" in message


def test_notify_training_processed_sends_feedback_prompt(monkeypatch):
    sent_messages: list[str] = []
    feedback_prompts: list[int] = []

    monkeypatch.setattr(
        "backend.services.notification_service.build_training_processed_message",
        lambda user_id, activity_id: f"processed:{user_id}:{activity_id}",
    )
    monkeypatch.setattr(
        "backend.services.notification_service.send_telegram_message",
        lambda text: sent_messages.append(text),
    )
    monkeypatch.setattr(
        "backend.services.notification_service.send_post_ride_rpe_request",
        lambda activity_id: feedback_prompts.append(activity_id),
    )
    monkeypatch.setattr(
        "backend.services.notification_service.get_activity_deduplication_state",
        lambda activity_id: {
            "activity_id": activity_id,
            "canonical_activity_id": activity_id,
            "user_id": "user-1",
            "is_excluded": False,
            "exclusion_reason": None,
        },
    )
    monkeypatch.setattr(
        "backend.services.notification_service.claim_activity_delivery",
        lambda **kwargs: True,
    )
    monkeypatch.setattr(
        "backend.services.notification_service.mark_activity_delivery_sent",
        lambda **kwargs: None,
    )

    notify_training_processed(user_id="user-1", activity_id=43)

    assert sent_messages == ["processed:user-1:43"]
    assert feedback_prompts == [43]
