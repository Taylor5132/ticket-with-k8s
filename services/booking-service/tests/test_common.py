import pytest
import jwt
from unittest.mock import MagicMock
from fastapi import HTTPException

from app.common import (
    queue_key,
    seq_key,
    token_key,
    queue_member,
    generate_seats,
    current_user,
    ensure_admission_group,
    JWT_SECRET,
    JWT_ALGORITHM,
)


# ── Key helpers ───────────────────────────────────────────

def test_queue_key():
    assert queue_key("perf1", "2026-01-01") == "queue:perf1:2026-01-01"


def test_seq_key():
    assert seq_key("perf1", "2026-01-01") == "seq:perf1:2026-01-01"


def test_token_key():
    assert token_key("perf1", "2026-01-01", "u1") == "token:perf1:2026-01-01:u1"


def test_queue_member():
    assert queue_member("perf1", "2026-01-01") == "perf1:2026-01-01"


# ── generate_seats ────────────────────────────────────────

class TestGenerateSeats:
    def test_total_count(self):
        assert len(generate_seats()) == 80  # 8행 × 10번

    def test_all_available_by_default(self):
        assert all(s["status"] == "AVAILABLE" for s in generate_seats())

    def test_occupied_seats_marked(self):
        seats = {s["seat_id"]: s for s in generate_seats({"A-1", "C-3"})}
        assert seats["A-1"]["status"] == "OCCUPIED"
        assert seats["C-3"]["status"] == "OCCUPIED"
        assert seats["A-2"]["status"] == "AVAILABLE"

    def test_empty_occupied_set(self):
        seats = generate_seats(set())
        assert all(s["status"] == "AVAILABLE" for s in seats)

    def test_vip_grade_rows_ab(self):
        seats = {s["seat_id"]: s for s in generate_seats()}
        assert seats["A-1"]["grade"] == "VIP"
        assert seats["A-1"]["price"] == 150000
        assert seats["B-5"]["grade"] == "VIP"
        assert seats["B-5"]["price"] == 150000

    def test_r_grade_rows_cd(self):
        seats = {s["seat_id"]: s for s in generate_seats()}
        assert seats["C-1"]["grade"] == "R"
        assert seats["C-1"]["price"] == 120000
        assert seats["D-10"]["grade"] == "R"

    def test_s_grade_rows_ef(self):
        seats = {s["seat_id"]: s for s in generate_seats()}
        assert seats["E-1"]["grade"] == "S"
        assert seats["E-1"]["price"] == 90000
        assert seats["F-7"]["grade"] == "S"

    def test_a_grade_rows_gh(self):
        seats = {s["seat_id"]: s for s in generate_seats()}
        assert seats["G-1"]["grade"] == "A"
        assert seats["G-1"]["price"] == 60000
        assert seats["H-10"]["grade"] == "A"

    def test_seat_structure_keys(self):
        seat = generate_seats()[0]
        assert set(seat.keys()) == {"seat_id", "row", "number", "grade", "price", "status"}

    def test_seat_numbering(self):
        seats = generate_seats()
        numbers = [s["number"] for s in seats if s["row"] == "A"]
        assert numbers == list(range(1, 11))


# ── current_user ──────────────────────────────────────────

class TestCurrentUser:
    def _token(self, **overrides):
        payload = {"sub": "u1", "display_name": "Test", "provider": "test", **overrides}
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    def test_valid_token_returns_user(self):
        user = current_user(authorization=f"Bearer {self._token()}")
        assert user["id"] == "u1"
        assert user["display_name"] == "Test"
        assert user["provider"] == "test"

    def test_no_bearer_prefix_raises_401(self):
        with pytest.raises(HTTPException) as exc:
            current_user(authorization="some-token")
        assert exc.value.status_code == 401
        assert exc.value.detail["code"] == "UNAUTHORIZED"

    def test_empty_authorization_raises_401(self):
        with pytest.raises(HTTPException) as exc:
            current_user(authorization="")
        assert exc.value.status_code == 401

    def test_invalid_token_raises_401(self):
        with pytest.raises(HTTPException) as exc:
            current_user(authorization="Bearer not.a.real.token")
        assert exc.value.status_code == 401

    def test_wrong_secret_raises_401(self):
        bad_token = jwt.encode(
            {"sub": "u1", "display_name": "X", "provider": "t"},
            "wrong-secret",
            algorithm=JWT_ALGORITHM,
        )
        with pytest.raises(HTTPException) as exc:
            current_user(authorization=f"Bearer {bad_token}")
        assert exc.value.status_code == 401


# ── ensure_admission_group ────────────────────────────────

class TestEnsureAdmissionGroup:
    def test_creates_group(self):
        mock_r = MagicMock()
        ensure_admission_group(mock_r)
        mock_r.xgroup_create.assert_called_once()

    def test_busygroup_error_is_ignored(self):
        mock_r = MagicMock()
        mock_r.xgroup_create.side_effect = Exception("BUSYGROUP Consumer Group name already exists")
        ensure_admission_group(mock_r)  # 예외 없이 통과해야 함

    def test_other_error_propagates(self):
        mock_r = MagicMock()
        mock_r.xgroup_create.side_effect = Exception("WRONGTYPE Operation against a key")
        with pytest.raises(Exception, match="WRONGTYPE"):
            ensure_admission_group(mock_r)
