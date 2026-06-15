import pytest
import jwt
import time
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

JWT_SECRET = "dev-secret"
JWT_ALGORITHM = "HS256"


def make_token(user_id="user-1"):
    now = int(time.time())
    return jwt.encode(
        {"sub": user_id, "iat": now, "exp": now + 3600},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )


@pytest.fixture
def mock_r():
    return MagicMock()


@pytest.fixture
def client(mock_r):
    import app.main as m

    original_r = m.r
    m.r = mock_r

    with TestClient(m.app) as c:
        yield c

    m.r = original_r


@pytest.fixture
def auth_headers():
    return {"Authorization": f"Bearer {make_token()}"}


# ── /health ───────────────────────────────────────────────

def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ── 헬퍼 함수 ─────────────────────────────────────────────

def test_key():
    from app.main import key
    assert key("user-1") == "saved:user:user-1"


def test_card_with_venue():
    from app.main import card
    detail = {
        "id": "1",
        "title": "Test Concert",
        "poster_url": "http://example.com/poster.jpg",
        "venue": {"name": "Test Hall", "province": "서울"},
        "genre": "뮤지컬",
        "start_date": "2026-07-01",
        "end_date": "2026-07-31",
    }
    result = card(detail)
    assert result["id"] == "1"
    assert result["title"] == "Test Concert"
    assert result["venue_name"] == "Test Hall"
    assert result["area"] == "서울"


def test_card_no_venue():
    from app.main import card
    detail = {
        "id": "2",
        "title": "Test",
        "poster_url": "url",
        "venue": None,
        "genre": "연극",
        "start_date": None,
        "end_date": None,
    }
    result = card(detail)
    assert result["venue_name"] is None
    assert result["area"] is None


# ── current_user 의존성 ───────────────────────────────────

def test_current_user_no_auth(client):
    resp = client.get("/saved/me")
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == "UNAUTHORIZED"


def test_current_user_invalid_token(client):
    resp = client.get("/saved/me", headers={"Authorization": "Bearer invalid"})
    assert resp.status_code == 401


# ── GET /saved/me ─────────────────────────────────────────

def test_saved_me_empty(client, mock_r, auth_headers):
    mock_r.smembers.return_value = set()

    resp = client.get("/saved/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["items"] == []
    mock_r.smembers.assert_called_once_with("saved:user:user-1")


def test_saved_me_with_data(client, mock_r, auth_headers):
    mock_r.smembers.return_value = {"1", "2"}

    perf_data = {
        "id": "1",
        "title": "Test Concert",
        "poster_url": "http://example.com/poster.jpg",
        "venue": {"name": "Test Hall", "province": "서울"},
        "genre": "뮤지컬",
        "start_date": "2026-07-01",
        "end_date": "2026-07-31",
    }

    mock_ok = MagicMock()
    mock_ok.status_code = 200
    mock_ok.json.return_value = perf_data

    mock_404 = MagicMock()
    mock_404.status_code = 404

    mock_http = MagicMock()
    mock_http.__enter__.return_value.get.side_effect = [mock_ok, mock_404]

    with patch("app.main.httpx.Client", return_value=mock_http):
        resp = client.get("/saved/me", headers=auth_headers)

    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["title"] == "Test Concert"
    assert items[0]["venue_name"] == "Test Hall"


def test_saved_me_all_404(client, mock_r, auth_headers):
    mock_r.smembers.return_value = {"99"}

    mock_404 = MagicMock()
    mock_404.status_code = 404

    mock_http = MagicMock()
    mock_http.__enter__.return_value.get.return_value = mock_404

    with patch("app.main.httpx.Client", return_value=mock_http):
        resp = client.get("/saved/me", headers=auth_headers)

    assert resp.status_code == 200
    assert resp.json()["items"] == []


# ── POST /saved/performances/{id} ────────────────────────

def test_add_saved(client, mock_r, auth_headers):
    resp = client.post("/saved/performances/42", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == {"performance_id": "42", "saved": True}
    mock_r.sadd.assert_called_once_with("saved:user:user-1", "42")


def test_add_saved_no_auth(client):
    resp = client.post("/saved/performances/42")
    assert resp.status_code == 401


# ── DELETE /saved/performances/{id} ──────────────────────

def test_delete_saved(client, mock_r, auth_headers):
    resp = client.delete("/saved/performances/42", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == {"performance_id": "42", "saved": False}
    mock_r.srem.assert_called_once_with("saved:user:user-1", "42")


def test_delete_saved_no_auth(client):
    resp = client.delete("/saved/performances/42")
    assert resp.status_code == 401
