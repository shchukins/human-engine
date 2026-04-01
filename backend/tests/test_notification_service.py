from backend.services.notification_service import (
    compute_readiness_score,
    describe_readiness,
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
