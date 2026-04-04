from backend.services.notification_service import (
    build_briefing_text,
    compute_readiness_score,
    describe_readiness,
    describe_freshness_trend,
    recommend_training,
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