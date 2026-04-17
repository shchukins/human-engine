from datetime import date

from backend.services import load_state_v2


class _FakeCursor:
    def __init__(self) -> None:
        self.query_log: list[str] = []
        self.insert_params: list[tuple] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, query, params):
        self.query_log.append(query)
        if "insert into load_state_daily_v2" in query:
            self.insert_params.append(params)

    def fetchall(self):
        return [
            (date(2026, 4, 9), 75.0),
            (date(2026, 4, 10), 0.0),
            (date(2026, 4, 11), 0.0),
        ]


class _FakeConn:
    def __init__(self, cursor: _FakeCursor) -> None:
        self._cursor = cursor
        self.committed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return self._cursor

    def commit(self):
        self.committed = True


def test_recompute_load_state_daily_v2_uses_training_and_recovery_bounds(monkeypatch):
    fake_cursor = _FakeCursor()
    fake_conn = _FakeConn(fake_cursor)

    monkeypatch.setattr(load_state_v2, "get_conn", lambda: fake_conn)

    result = load_state_v2.recompute_load_state_daily_v2(user_id="user-1")

    bounds_query = fake_cursor.query_log[0]
    assert "with source_dates as" in bounds_query
    assert "from daily_training_load" in bounds_query
    assert "union" in bounds_query
    assert "from health_recovery_daily" in bounds_query

    assert result["days_processed"] == 3
    assert result["last_date"] == "2026-04-11"
    assert result["last_freshness"] is not None

    assert len(fake_cursor.insert_params) == 3
    assert fake_cursor.insert_params[1][2] == 0.0
    assert fake_cursor.insert_params[2][2] == 0.0
    assert fake_conn.committed is True
