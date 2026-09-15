"""月末自動締めの対象月判定を、DB なしで検証する。"""
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.services import monthly_close
from app.services.monthly_close import close_due_month, year_month_due_for_close


@pytest.mark.parametrize(
    ("now", "expected"),
    [
        (datetime(2026, 9, 15, 23, 59, tzinfo=UTC), "2026-08"),
        (datetime(2026, 9, 30, 23, 58, tzinfo=UTC), "2026-08"),
        (datetime(2026, 9, 30, 23, 59, tzinfo=UTC), "2026-09"),
        (datetime(2026, 2, 28, 23, 59, tzinfo=UTC), "2026-02"),
        (datetime(2026, 10, 1, 8, 0, tzinfo=UTC), "2026-09"),
        (datetime(2026, 1, 1, 0, 0, tzinfo=UTC), "2025-12"),
    ],
)
def test_自動締めの対象月を判定する(now: datetime, expected: str):
    assert year_month_due_for_close(now) == expected


def test_進行中ならシステムユーザーとして締める(monkeypatch: pytest.MonkeyPatch):
    session = Mock()
    settlement = SimpleNamespace(status="in_progress")
    get_or_create = Mock(return_value=settlement)
    close = Mock()
    monkeypatch.setattr(monthly_close.q, "get_or_create_settlement", get_or_create)
    monkeypatch.setattr(monthly_close, "close_month", close)

    result = close_due_month(
        session, datetime(2026, 9, 30, 23, 59, tzinfo=UTC)
    )

    assert result == ("2026-09", True)
    close.assert_called_once_with(session, user=None, year_month="2026-09")


@pytest.mark.parametrize("status", ["closed", "partially_confirmed", "settled"])
def test_締め済みなら何もしない(
    monkeypatch: pytest.MonkeyPatch, status: str
):
    session = Mock()
    monkeypatch.setattr(
        monthly_close.q,
        "get_or_create_settlement",
        Mock(return_value=SimpleNamespace(status=status)),
    )
    close = Mock()
    monkeypatch.setattr(monthly_close, "close_month", close)

    result = close_due_month(
        session, datetime(2026, 10, 1, 8, 0, tzinfo=UTC)
    )

    assert result == ("2026-09", False)
    close.assert_not_called()
