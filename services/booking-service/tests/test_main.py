import pytest
from contextlib import contextmanager
from datetime import date, datetime
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from app.common import current_user


def _fake_user():
    return {"id": "user-1", "display_name": "Test User", "provider": "test"}


def _setup_conn(mock_engine):
    """mock_engine.begin()을 context manager로 연결하고 mock conn 반환."""
    mock_conn = MagicMock()

    @contextmanager
    def fake_begin():
        yield mock_conn

    mock_engine.begin = fake_begin
    return mock_conn


@pytest.fixture
def mock_r():
    return MagicMock()


@pytest.fixture
def mock_engine():
    return MagicMock()


@pytest.fixture
def client(mock_r, mock_engine):
    import app.main as m

    original_r = m.r
    original_engine = m.engine
    original_enforce = m.ENFORCE_ADMISSION_TOKEN

    m.r = mock_r
    m.engine = mock_engine
    m.ENFORCE_ADMISSION_TOKEN = False
    m.app.dependency_overrides[current_user] = _fake_user

    with TestClient(m.app) as c:
        yield c

    m.r = original_r
    m.engine = original_engine
    m.ENFORCE_ADMISSION_TOKEN = original_enforce
    m.app.dependency_overrides.clear()


# ── /health ───────────────────────────────────────────────

def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ── 좌석 가용성 ────────────────────────────────────────────

def test_seat_availability_all_empty(client, mock_engine):
    conn = _setup_conn(mock_engine)
    conn.execute.return_value.all.return_value = []

    resp = client.get("/performances/perf1/seat-availability?show_date=2026-01-01")
    assert resp.status_code == 200
    data = resp.json()
    assert data["performance_id"] == "perf1"
    assert data["show_date"] == "2026-01-01"
    assert len(data["seats"]) == 80
    assert all(s["status"] == "AVAILABLE" for s in data["seats"])


def test_seat_availability_with_occupied(client, mock_engine):
    conn = _setup_conn(mock_engine)
    row = MagicMock()
    row.seat_id = "A-1"
    conn.execute.return_value.all.return_value = [row]

    resp = client.get("/api/performances/perf1/seat-availability?show_date=2026-01-01")
    assert resp.status_code == 200
    seats = {s["seat_id"]: s for s in resp.json()["seats"]}
    assert seats["A-1"]["status"] == "OCCUPIED"
    assert seats["B-1"]["status"] == "AVAILABLE"


# ── 대기열 진입 ────────────────────────────────────────────

def test_queue_join_new_user(client, mock_r):
    mock_r.get.return_value = None
    mock_r.zscore.return_value = None
    mock_r.incr.return_value = 1
    mock_r.zrank.return_value = 0
    mock_r.zcard.return_value = 1

    resp = client.post("/queue/join?performance_id=perf1&show_date=2026-01-01")
    assert resp.status_code == 200
    data = resp.json()
    assert data["admitted"] is False
    assert data["position"] == 1
    assert data["total"] == 1


def test_queue_join_already_in_queue(client, mock_r):
    mock_r.get.return_value = None
    mock_r.zscore.return_value = 2  # 이미 번호표 있음
    mock_r.zrank.return_value = 1
    mock_r.zcard.return_value = 3

    resp = client.post("/queue/join?performance_id=perf1&show_date=2026-01-01")
    assert resp.status_code == 200
    data = resp.json()
    assert data["admitted"] is False
    assert data["position"] == 2


def test_queue_join_already_admitted(client, mock_r):
    mock_r.get.return_value = "valid"  # 입장 토큰 있음

    resp = client.post("/queue/join?performance_id=perf1&show_date=2026-01-01")
    assert resp.status_code == 200
    assert resp.json()["admitted"] is True


# ── 대기열 상태 ────────────────────────────────────────────

def test_queue_status_admitted(client, mock_r):
    mock_r.get.return_value = "valid"

    resp = client.get("/queue/status?performance_id=perf1&show_date=2026-01-01")
    assert resp.status_code == 200
    assert resp.json()["admitted"] is True


def test_queue_status_waiting(client, mock_r):
    mock_r.get.return_value = None
    mock_r.zrank.return_value = 4
    mock_r.zcard.return_value = 10

    resp = client.get("/queue/status?performance_id=perf1&show_date=2026-01-01")
    assert resp.status_code == 200
    data = resp.json()
    assert data["admitted"] is False
    assert data["position"] == 5
    assert data["total"] == 10


def test_queue_status_in_flight(client, mock_r):
    """줄에서 빠졌지만 아직 토큰 미발급 상태."""
    mock_r.get.return_value = None
    mock_r.zrank.return_value = None
    mock_r.zcard.return_value = 0

    resp = client.get("/queue/status?performance_id=perf1&show_date=2026-01-01")
    assert resp.status_code == 200
    data = resp.json()
    assert data["admitted"] is False
    assert data["position"] == 0


# ── 예매 요청 조회 ──────────────────────────────────────────

def test_booking_request_not_found(client, mock_engine):
    conn = _setup_conn(mock_engine)
    conn.execute.return_value.mappings.return_value.first.return_value = None

    resp = client.get("/booking-requests/br-nonexistent")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "NOT_FOUND"


def test_booking_request_found(client, mock_engine):
    conn = _setup_conn(mock_engine)
    conn.execute.return_value.mappings.return_value.first.return_value = {
        "id": "br-123",
        "status": "CONFIRMED",
        "failure_reason": None,
        "booking_id": "booking-456",
        "show_date": date(2026, 1, 1),
    }

    resp = client.get("/booking-requests/br-123")
    assert resp.status_code == 200
    data = resp.json()
    assert data["request_id"] == "br-123"
    assert data["status"] == "CONFIRMED"
    assert data["show_date"] == "2026-01-01"
    assert data["booking_id"] == "booking-456"


def test_booking_request_no_show_date(client, mock_engine):
    conn = _setup_conn(mock_engine)
    conn.execute.return_value.mappings.return_value.first.return_value = {
        "id": "br-123",
        "status": "PENDING",
        "failure_reason": None,
        "booking_id": None,
        "show_date": None,
    }

    resp = client.get("/booking-requests/br-123")
    assert resp.status_code == 200
    assert resp.json()["show_date"] is None


# ── 예매 요청 생성 ──────────────────────────────────────────

def test_create_booking_request_invalid_seat(client):
    resp = client.post("/booking-requests", json={
        "performance_id": "perf1",
        "seat_id": "Z-99",
        "show_date": "2026-01-01",
    })
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "INVALID_SEAT"


def test_create_booking_request_no_admission_token(client, mock_r):
    import app.main as m
    m.ENFORCE_ADMISSION_TOKEN = True
    mock_r.get.return_value = None  # 토큰 없음

    resp = client.post("/booking-requests", json={
        "performance_id": "perf1",
        "seat_id": "A-1",
        "show_date": "2026-01-01",
    })
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "NO_ADMISSION_TOKEN"
    m.ENFORCE_ADMISSION_TOKEN = False


def test_create_booking_request_success(client, mock_r, mock_engine):
    conn = _setup_conn(mock_engine)
    mock_r.xadd.return_value = "stream-id-1"

    resp = client.post("/booking-requests", json={
        "performance_id": "perf1",
        "seat_id": "A-1",
        "show_date": "2026-01-01",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "PENDING"
    assert data["request_id"].startswith("br-")
    mock_r.xadd.assert_called_once()


# ── 내 예매 목록 ────────────────────────────────────────────

def test_my_bookings_empty(client, mock_engine):
    conn = _setup_conn(mock_engine)
    conn.execute.return_value.mappings.return_value.all.return_value = []

    resp = client.get("/bookings/me")
    assert resp.status_code == 200
    assert resp.json()["items"] == []


def test_my_bookings_with_data(client, mock_engine):
    conn = _setup_conn(mock_engine)
    conn.execute.return_value.mappings.return_value.all.return_value = [{
        "id": "booking-1",
        "performance_id": "perf1",
        "performance_title": "Test Concert",
        "venue_name": "Test Hall",
        "performance_date": date(2026, 7, 1),
        "seat_id": "A-1",
        "seat_grade": "VIP",
        "paid_amount": 150000,
        "booked_at": datetime(2026, 6, 14, 10, 0, 0),
    }]

    resp = client.get("/bookings/me")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["performance_date"] == "2026-07-01"
    assert items[0]["seat_grade"] == "VIP"
