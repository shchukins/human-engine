from backend.services.ingest_service import _is_retryable_error


def test_retryable_error_403():
    assert _is_retryable_error("403: strava api temporary error") is True


def test_retryable_error_502():
    assert _is_retryable_error("502: bad gateway") is True


def test_retryable_error_timeout():
    assert _is_retryable_error("request timeout while calling strava") is True


def test_retryable_error_connection():
    assert _is_retryable_error("connection reset by peer") is True


def test_non_retryable_error_404():
    assert _is_retryable_error('404: {"message":"Record Not Found"}') is False


def test_non_retryable_error_record_not_found():
    assert _is_retryable_error("Record Not Found") is False


def test_non_retryable_error_invalid():
    assert _is_retryable_error("invalid activity id") is False
