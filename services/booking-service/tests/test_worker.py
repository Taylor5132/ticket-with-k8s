import pytest
from contextlib import contextmanager
from unittest.mock import MagicMock
import httpx

from app.worker import payment_failure_reason, set_request_status, mark_failed


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
