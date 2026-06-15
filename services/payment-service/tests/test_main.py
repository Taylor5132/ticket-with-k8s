import pytest
import jwt
import time
from datetime import datetime
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

JWT_SECRET = "dev-secret"
JWT_ALGORITHM = "HS256"
SERVICE_TOKEN = "dev-service-token"


def make_token(user_id="user-1", provider="local", display_name="Test User"):
    now = int(time.time())
    return jwt.encode(
        {"sub": user_id, "provider": provider, "display_name": display_name,
         "iat": now, "exp": now + 3600},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )


def _setup_begin(mock_engine):
    mock_conn = MagicMock()
    mock_engine.begin.return_value.__enter__.return_value = mock_conn
    return mock_conn


def _balance_row(balance=100000):
    row = MagicMock()
    row.balance = balance
    return row


@pytest.fixture
def mock_engine():
    return MagicMock()


@pytest.fixture
def client(mock_engine):
    import app.main as m

    original_engine = m.engine
    m.engine = mock_engine

    with TestClient(m.app) as c:
        yield c

    m.engine = original_engine


@pytest.fixture
def auth_headers():
    return {"Authorization": f"Bearer {make_token()}"}


# ── /health ───────────────────────────────────────────────

def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ── 헬퍼 함수 ─────────────────────────────────────────────

def test_default_balance_normal():
    from app.main import default_balance
    assert default_balance("user-1") == 100000


def test_default_balance_rich():
    from app.main import default_balance
    assert default_balance("demo-rich-user") == 300000


# ── current_user 의존성 ───────────────────────────────────

def test_current_user_no_auth(client):
    resp = client.get("/payments/me/balance")
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == "UNAUTHORIZED"


def test_current_user_invalid_token(client):
    resp = client.get("/payments/me/balance", headers={"Authorization": "Bearer invalid"})
    assert resp.status_code == 401


# ── /payments/me/balance ──────────────────────────────────

def test_balance_existing_user(client, mock_engine, auth_headers):
    conn = _setup_begin(mock_engine)
    conn.execute.return_value.first.return_value = _balance_row(75000)

    resp = client.get("/payments/me/balance", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["balance"] == 75000


def test_balance_new_user(client, mock_engine, auth_headers):
    conn = _setup_begin(mock_engine)
    conn.execute.return_value.first.return_value = None

    resp = client.get("/payments/me/balance", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["balance"] == 100000


def test_balance_new_user_rich(client, mock_engine):
    conn = _setup_begin(mock_engine)
    conn.execute.return_value.first.return_value = None

    headers = {"Authorization": f"Bearer {make_token(user_id='demo-rich-user')}"}
    resp = client.get("/payments/me/balance", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["balance"] == 300000


# ── /payments/me/history ──────────────────────────────────

def test_history_empty(client, mock_engine, auth_headers):
    conn = _setup_begin(mock_engine)
    conn.execute.return_value.mappings.return_value.all.return_value = []

    resp = client.get("/payments/me/history", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["items"] == []


def test_history_with_data(client, mock_engine, auth_headers):
    conn = _setup_begin(mock_engine)
    conn.execute.return_value.mappings.return_value.all.return_value = [{
        "id": "pay-1",
        "booking_request_id": "br-1",
        "booking_id": "booking-1",
        "performance_title": "테스트 공연",
        "amount": 50000,
        "status": "PAID",
        "paid_at": datetime(2026, 6, 14, 10, 0, 0),
    }]

    resp = client.get("/payments/me/history", headers=auth_headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["performance_title"] == "테스트 공연"
    assert items[0]["paid_at"] == "2026-06-14T10:00:00"
    assert items[0]["amount"] == 50000


# ── /payments/deduct ──────────────────────────────────────

def test_deduct_wrong_service_token(client):
    resp = client.post("/payments/deduct",
        json={"user_id": "user-1", "booking_request_id": "br-1",
              "booking_id": "b-1", "amount": 50000, "performance_title": "Test"},
        headers={"x-service-token": "wrong-token"},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "FORBIDDEN"


def test_deduct_idempotent(client, mock_engine):
    conn = _setup_begin(mock_engine)
    existing = {"id": "pay-existing", "user_id": "user-1", "amount": 50000}

    conn.execute.side_effect = [
        MagicMock(**{"mappings.return_value.first.return_value": existing}),
        MagicMock(**{"first.return_value": _balance_row(50000)}),
    ]

    resp = client.post("/payments/deduct",
        json={"user_id": "user-1", "booking_request_id": "br-1",
              "booking_id": "b-1", "amount": 50000, "performance_title": "Test"},
        headers={"x-service-token": SERVICE_TOKEN},
    )
    assert resp.status_code == 200
    assert resp.json()["payment_id"] == "pay-existing"
    assert resp.json()["balance_after"] == 50000


def test_deduct_insufficient_balance(client, mock_engine):
    conn = _setup_begin(mock_engine)
    conn.execute.side_effect = [
        MagicMock(**{"mappings.return_value.first.return_value": None}),
        MagicMock(**{"first.return_value": _balance_row(10000)}),
        MagicMock(**{"first.return_value": _balance_row(10000)}),
    ]

    resp = client.post("/payments/deduct",
        json={"user_id": "user-1", "booking_request_id": "br-2",
              "booking_id": "b-2", "amount": 50000, "performance_title": "Test"},
        headers={"x-service-token": SERVICE_TOKEN},
    )
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "INSUFFICIENT_POINTS"


def test_deduct_success(client, mock_engine):
    conn = _setup_begin(mock_engine)
    conn.execute.side_effect = [
        MagicMock(**{"mappings.return_value.first.return_value": None}),
        MagicMock(**{"first.return_value": _balance_row(100000)}),
        MagicMock(**{"first.return_value": _balance_row(100000)}),
        MagicMock(),
        MagicMock(),
    ]

    resp = client.post("/payments/deduct",
        json={"user_id": "user-1", "booking_request_id": "br-3",
              "booking_id": "b-3", "amount": 50000, "performance_title": "Test"},
        headers={"x-service-token": SERVICE_TOKEN},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["payment_id"].startswith("pay-")
    assert data["balance_after"] == 50000
