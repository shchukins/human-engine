from backend.services.notification_service import (
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