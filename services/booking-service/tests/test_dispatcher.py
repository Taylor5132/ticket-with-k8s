import pytest
from unittest.mock import MagicMock


@pytest.fixture(autouse=True)
def reset_dispatcher_mocks():
    import app.dispatcher as m

    original_r = m.r
    original_dispatch = m._dispatch

    mock_r = MagicMock()
    mock_dispatch = MagicMock()
    m.r = mock_r
    m._dispatch = mock_dispatch

    yield mock_r, mock_dispatch

    m.r = original_r
    m._dispatch = original_dispatch


def test_dispatch_once_no_active_queues(reset_dispatcher_mocks):
    mock_r, _ = reset_dispatcher_mocks
    mock_r.smembers.return_value = set()

    from app.dispatcher import dispatch_once
    assert dispatch_once() == 0


def test_dispatch_once_moves_users_and_removes_empty_queue(reset_dispatcher_mocks):
    mock_r, mock_dispatch = reset_dispatcher_mocks
    mock_r.smembers.return_value = {"perf1:2026-01-01"}
    mock_dispatch.return_value = 3
    mock_r.zcard.return_value = 0  # 큐가 비워짐

    from app.dispatcher import dispatch_once
    result = dispatch_once()
    assert result == 3
    mock_r.srem.assert_called_once_with("active-queues", "perf1:2026-01-01")


def test_dispatch_once_does_not_remove_nonempty_queue(reset_dispatcher_mocks):
    mock_r, mock_dispatch = reset_dispatcher_mocks
    mock_r.smembers.return_value = {"perf1:2026-01-01"}
    mock_dispatch.return_value = 2
    mock_r.zcard.return_value = 5  # 아직 대기자 있음

    from app.dispatcher import dispatch_once
    result = dispatch_once()
    assert result == 2
    mock_r.srem.assert_not_called()


def test_dispatch_once_multiple_queues(reset_dispatcher_mocks):
    mock_r, mock_dispatch = reset_dispatcher_mocks
    mock_r.smembers.return_value = {"perf1:2026-01-01", "perf2:2026-01-02"}
    mock_dispatch.return_value = 1
    mock_r.zcard.return_value = 0

    from app.dispatcher import dispatch_once
    result = dispatch_once()
    assert result == 2  # 큐 2개 × 1명
    assert mock_r.srem.call_count == 2


def test_dispatch_once_zero_moved(reset_dispatcher_mocks):
    mock_r, mock_dispatch = reset_dispatcher_mocks
    mock_r.smembers.return_value = {"perf1:2026-01-01"}
    mock_dispatch.return_value = 0
    mock_r.zcard.return_value = 0

    from app.dispatcher import dispatch_once
    assert dispatch_once() == 0
