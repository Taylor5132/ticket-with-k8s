import pytest
from contextlib import contextmanager
from unittest.mock import MagicMock, patch
import httpx
from redis.exceptions import ResponseError

from app.worker import payment_failure_reason, set_request_status, mark_failed, ensure_group, process


# ── payment_failure_reason ────────────────────────────────

class TestPaymentFailureReason:
    def _resp(self, json_data=None, raises=False):
        mock = MagicMock(spec=httpx.Response)
        if raises:
            mock.json.side_effect = ValueError("no JSON")
        else:
            mock.json.return_value = json_data or {}
        return mock

    def test_insufficient_points_code(self):
        resp = self._resp({"detail": {"code": "INSUFFICIENT_POINTS"}})
        assert payment_failure_reason(resp) == "INSUFFICIENT_POINTS"

    def test_other_error_code(self):
        resp = self._resp({"detail": {"code": "OTHER_ERROR"}})
        assert payment_failure_reason(resp) == "PAYMENT_FAILED"

    def test_string_detail(self):
        resp = self._resp({"detail": "something went wrong"})
        assert payment_failure_reason(resp) == "PAYMENT_FAILED"

    def test_empty_response(self):
        resp = self._resp({})
        assert payment_failure_reason(resp) == "PAYMENT_FAILED"

    def test_invalid_json_falls_back(self):
        resp = self._resp(raises=True)
        assert payment_failure_reason(resp) == "PAYMENT_FAILED"

    def test_detail_missing_code_key(self):
        resp = self._resp({"detail": {"msg": "no code"}})
        assert payment_failure_reason(resp) == "PAYMENT_FAILED"


# ── set_request_status ────────────────────────────────────

class TestSetRequestStatus:
    def test_basic_status_update(self):
        conn = MagicMock()
        set_request_status(conn, "req-1", "PROCESSING")
        conn.execute.assert_called_once()

    def test_status_with_failure_reason(self):
        conn = MagicMock()
        set_request_status(conn, "req-1", "FAILED", failure_reason="SEAT_ALREADY_BOOKED")
        conn.execute.assert_called_once()

    def test_status_with_booking_id(self):
        conn = MagicMock()
        set_request_status(conn, "req-1", "CONFIRMED", booking_id="booking-123")
        conn.execute.assert_called_once()

    def test_all_params(self):
        conn = MagicMock()
        set_request_status(conn, "req-1", "CONFIRMED", failure_reason=None, booking_id="b-1")
        conn.execute.assert_called_once()


# ── mark_failed ───────────────────────────────────────────

class TestMarkFailed:
    def test_calls_execute(self):
        import app.worker as m

        mock_conn = MagicMock()

        @contextmanager
        def fake_begin():
            yield mock_conn

        original = m.engine
        m.engine = MagicMock()
        m.engine.begin = fake_begin

        mark_failed("req-1", "SEAT_ALREADY_BOOKED")
        mock_conn.execute.assert_called_once()

        m.engine = original


# ── ensure_group ──────────────────────────────────────────

class TestEnsureGroup:
    def test_creates_group(self):
        import app.worker as m
        original_r = m.r
        mock_r = MagicMock()
        m.r = mock_r

        ensure_group()

        mock_r.xgroup_create.assert_called_once()
        m.r = original_r

    def test_busygroup_ignored(self):
        import app.worker as m
        original_r = m.r
        mock_r = MagicMock()
        mock_r.xgroup_create.side_effect = ResponseError("BUSYGROUP Consumer Group already exists")
        m.r = mock_r

        ensure_group()  # 예외 없이 통과해야 함

        m.r = original_r

    def test_other_error_propagates(self):
        import app.worker as m
        original_r = m.r
        mock_r = MagicMock()
        mock_r.xgroup_create.side_effect = ResponseError("WRONGTYPE Operation against a key")
        m.r = mock_r

        with pytest.raises(ResponseError, match="WRONGTYPE"):
            ensure_group()

        m.r = original_r


# ── process ───────────────────────────────────────────────

SAMPLE_FIELDS = {
    "booking_request_id": "br-001",
    "performance_id": "perf1",
    "seat_id": "A-1",
    "show_date": "2026-01-01",
    "user_id": "user-1",
}


@pytest.fixture
def mock_worker_engine():
    import app.worker as m
    original = m.engine
    mock_conn = MagicMock()

    @contextmanager
    def fake_begin():
        yield mock_conn

    mock_engine = MagicMock()
    mock_engine.begin = fake_begin
    m.engine = mock_engine

    yield mock_conn

    m.engine = original


def _make_http_client(perf_data, seat_data, payment_status=200, payment_json=None):
    perf_resp = MagicMock(spec=httpx.Response)
    perf_resp.json.return_value = perf_data

    seat_resp = MagicMock(spec=httpx.Response)
    seat_resp.json.return_value = seat_data

    pay_resp = MagicMock(spec=httpx.Response)
    pay_resp.status_code = payment_status
    if payment_json:
        pay_resp.json.return_value = payment_json

    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.get.side_effect = [perf_resp, seat_resp]
    mock_client.post.return_value = pay_resp
    return mock_client


class TestProcess:
    def test_seat_already_occupied(self, mock_worker_engine):
        conn = mock_worker_engine
        occupied_result = MagicMock()
        occupied_result.first.return_value = MagicMock()  # truthy = 이미 예약됨

        conn.execute.side_effect = [
            MagicMock(),      # pg_advisory_xact_lock
            MagicMock(),      # set_request_status PROCESSING
            occupied_result,  # SELECT seat → truthy
            MagicMock(),      # set_request_status FAILED
        ]

        process(SAMPLE_FIELDS)
        assert conn.execute.call_count == 4

    def test_payment_failed(self, mock_worker_engine):
        conn = mock_worker_engine
        not_occupied = MagicMock()
        not_occupied.first.return_value = None  # 좌석 비어 있음

        conn.execute.side_effect = [
            MagicMock(),   # pg_advisory_xact_lock
            MagicMock(),   # set_request_status PROCESSING
            not_occupied,  # SELECT occupied → None
            MagicMock(),   # set_request_status FAILED (결제 실패)
        ]

        mock_client = _make_http_client(
            {"title": "Concert", "venue": {"name": "Hall"}},
            {"grade": "VIP", "price": 150000},
            payment_status=402,
            payment_json={"detail": {"code": "INSUFFICIENT_POINTS"}},
        )
        with patch("app.worker.httpx.Client", return_value=mock_client):
            process(SAMPLE_FIELDS)

        assert conn.execute.call_count == 4

    def test_success(self, mock_worker_engine):
        conn = mock_worker_engine
        not_occupied = MagicMock()
        not_occupied.first.return_value = None
        inserted = MagicMock()
        inserted.first.return_value = MagicMock()  # INSERT 성공

        conn.execute.side_effect = [
            MagicMock(),   # pg_advisory_xact_lock
            MagicMock(),   # set_request_status PROCESSING
            not_occupied,  # SELECT occupied → None
            inserted,      # INSERT → id 반환
            MagicMock(),   # set_request_status CONFIRMED
        ]

        mock_client = _make_http_client(
            {"title": "Concert", "venue": {"name": "Hall"}},
            {"grade": "VIP", "price": 150000},
            payment_status=200,
        )
        with patch("app.worker.httpx.Client", return_value=mock_client):
            process(SAMPLE_FIELDS)

        assert conn.execute.call_count == 5

    def test_insert_conflict(self, mock_worker_engine):
        conn = mock_worker_engine
        not_occupied = MagicMock()
        not_occupied.first.return_value = None
        conflict = MagicMock()
        conflict.first.return_value = None  # ON CONFLICT DO NOTHING

        conn.execute.side_effect = [
            MagicMock(),   # pg_advisory_xact_lock
            MagicMock(),   # set_request_status PROCESSING
            not_occupied,  # SELECT occupied → None
            conflict,      # INSERT → None (충돌)
            MagicMock(),   # set_request_status FAILED
        ]

        mock_client = _make_http_client(
            {"title": "Concert", "venue": {"name": "Hall"}},
            {"grade": "VIP", "price": 150000},
            payment_status=200,
        )
        with patch("app.worker.httpx.Client", return_value=mock_client):
            process(SAMPLE_FIELDS)

        assert conn.execute.call_count == 5
