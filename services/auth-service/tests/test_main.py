import pytest
import jwt
import time
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

JWT_SECRET = "dev-secret"
JWT_ALGORITHM = "HS256"


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

def test_make_user_id_simple():
    from app.main import make_user_id
    assert make_user_id("alice") == "user-alice"


def test_make_user_id_special_chars():
    from app.main import make_user_id
    assert make_user_id("hello world!") == "user-hello-world-"


def test_issue_token():
    from app.main import issue_token
    token = issue_token({"id": "u1", "provider": "local", "display_name": "Alice"})
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    assert payload["sub"] == "u1"
    assert payload["provider"] == "local"


# ── current_user 의존성 ───────────────────────────────────

def test_current_user_no_header(client):
    resp = client.get("/auth/me")
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == "UNAUTHORIZED"


def test_current_user_invalid_token(client):
    resp = client.get("/auth/me", headers={"Authorization": "Bearer invalid.token"})
    assert resp.status_code == 401


# ── /auth/dev-login ───────────────────────────────────────

def test_dev_login(client, mock_engine):
    conn = _setup_begin(mock_engine)
    conn.execute.return_value.mappings.return_value.one.return_value = {
        "id": "user-alice",
        "provider": "dev",
        "login_id": "alice",
        "display_name": "Alice",
    }

    resp = client.post("/auth/dev-login", json={
        "provider": "dev",
        "login_id": "alice",
        "display_name": "Alice",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["id"] == "user-alice"


# ── /auth/signup ──────────────────────────────────────────

def test_signup_invalid_id(client):
    resp = client.post("/auth/signup", json={
        "login_id": "ab",
        "password": "password123",
        "display_name": "Alice",
    })
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "INVALID_ID"


def test_signup_weak_password(client):
    resp = client.post("/auth/signup", json={
        "login_id": "alice123",
        "password": "short",
        "display_name": "Alice",
    })
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "WEAK_PASSWORD"


def test_signup_invalid_name(client):
    resp = client.post("/auth/signup", json={
        "login_id": "alice123",
        "password": "password123",
        "display_name": "   ",
    })
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "INVALID_NAME"


def test_signup_success(client, mock_engine):
    conn = _setup_begin(mock_engine)
    conn.execute.return_value.mappings.return_value.one.return_value = {
        "id": "user-local-alice123",
        "provider": "local",
        "login_id": "alice123",
        "display_name": "Alice",
    }

    with patch("app.main.bcrypt.hashpw", return_value=b"$2b$12$fakehash"):
        resp = client.post("/auth/signup", json={
            "login_id": "alice123",
            "password": "password123",
            "display_name": "Alice",
        })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["user"]["provider"] == "local"


def test_signup_duplicate(client, mock_engine):
    conn = _setup_begin(mock_engine)
    conn.execute.side_effect = Exception("duplicate key")

    with patch("app.main.bcrypt.hashpw", return_value=b"$2b$12$fakehash"):
        resp = client.post("/auth/signup", json={
            "login_id": "alice123",
            "password": "password123",
            "display_name": "Alice",
        })
    assert resp.status_code == 409
    assert resp.json()["detail"]["code"] == "ID_TAKEN"


# ── /auth/login ───────────────────────────────────────────

def test_local_login_not_found(client, mock_engine):
    conn = _setup_begin(mock_engine)
    conn.execute.return_value.mappings.return_value.first.return_value = None

    resp = client.post("/auth/login", json={"login_id": "nobody", "password": "pass1234"})
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == "INVALID_CREDENTIALS"


def test_local_login_no_password_hash(client, mock_engine):
    conn = _setup_begin(mock_engine)
    conn.execute.return_value.mappings.return_value.first.return_value = {
        "id": "user-alice123",
        "provider": "local",
        "login_id": "alice123",
        "display_name": "Alice",
        "password_hash": None,
    }

    resp = client.post("/auth/login", json={"login_id": "alice123", "password": "pass1234"})
    assert resp.status_code == 401


def test_local_login_wrong_password(client, mock_engine):
    conn = _setup_begin(mock_engine)
    conn.execute.return_value.mappings.return_value.first.return_value = {
        "id": "user-alice123",
        "provider": "local",
        "login_id": "alice123",
        "display_name": "Alice",
        "password_hash": "$2b$12$fakehash",
    }

    with patch("app.main.bcrypt.checkpw", return_value=False):
        resp = client.post("/auth/login", json={"login_id": "alice123", "password": "wrongpass"})
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == "INVALID_CREDENTIALS"


def test_local_login_success(client, mock_engine):
    conn = _setup_begin(mock_engine)
    conn.execute.return_value.mappings.return_value.first.return_value = {
        "id": "user-alice123",
        "provider": "local",
        "login_id": "alice123",
        "display_name": "Alice",
        "password_hash": "$2b$12$fakehash",
    }

    with patch("app.main.bcrypt.checkpw", return_value=True):
        resp = client.post("/auth/login", json={"login_id": "alice123", "password": "password123"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


# ── /auth/me ──────────────────────────────────────────────

def test_me_found(client, mock_engine, auth_headers):
    conn = _setup_begin(mock_engine)
    conn.execute.return_value.mappings.return_value.first.return_value = {
        "id": "user-1",
        "provider": "local",
        "login_id": "alice123",
        "display_name": "Test User",
    }

    resp = client.get("/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == "user-1"


def test_me_not_found(client, mock_engine, auth_headers):
    conn = _setup_begin(mock_engine)
    conn.execute.return_value.mappings.return_value.first.return_value = None

    resp = client.get("/auth/me", headers=auth_headers)
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "NOT_FOUND"


# ── /auth/google ──────────────────────────────────────────

def test_google_login_not_configured(client):
    import app.main as m
    original = m.GOOGLE_CLIENT_ID
    m.GOOGLE_CLIENT_ID = ""

    resp = client.get("/auth/google", follow_redirects=False)
    assert resp.status_code == 503
    assert resp.json()["detail"]["code"] == "OAUTH_NOT_CONFIGURED"

    m.GOOGLE_CLIENT_ID = original


def test_google_login_redirects(client):
    import app.main as m
    original = m.GOOGLE_CLIENT_ID
    m.GOOGLE_CLIENT_ID = "test-client-id"

    resp = client.get("/auth/google", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert "accounts.google.com" in resp.headers["location"]

    m.GOOGLE_CLIENT_ID = original


# ── /auth/google/callback ─────────────────────────────────

def test_google_callback_error_param(client):
    resp = client.get("/auth/google/callback?error=access_denied", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert "oauth_error" in resp.headers["location"]


def test_google_callback_invalid_state(client):
    resp = client.get(
        "/auth/google/callback?code=abc&state=wrong",
        cookies={"oauth_state": "correct"},
        follow_redirects=False,
    )
    assert resp.status_code in (302, 307)
    assert "invalid_state" in resp.headers["location"]


def test_google_callback_no_state_cookie(client):
    resp = client.get(
        "/auth/google/callback?code=abc&state=somestate",
        follow_redirects=False,
    )
    assert resp.status_code in (302, 307)
    assert "invalid_state" in resp.headers["location"]


def test_google_callback_httpx_error(client):
    mock_http = MagicMock()
    mock_http.__enter__.return_value.post.side_effect = Exception("network error")

    with patch("app.main.httpx.Client", return_value=mock_http):
        resp = client.get(
            "/auth/google/callback?code=abc&state=validstate",
            cookies={"oauth_state": "validstate"},
            follow_redirects=False,
        )
    assert resp.status_code in (302, 307)
    assert "google_api_error" in resp.headers["location"]


def test_google_callback_success(client, mock_engine):
    conn = _setup_begin(mock_engine)
    conn.execute.return_value.mappings.return_value.one.return_value = {
        "id": "user-12345",
        "provider": "google",
        "login_id": "12345",
        "display_name": "Google User",
    }

    mock_token_resp = MagicMock()
    mock_token_resp.json.return_value = {"access_token": "gtoken"}
    mock_userinfo_resp = MagicMock()
    mock_userinfo_resp.json.return_value = {"sub": "12345", "name": "Google User"}

    mock_http = MagicMock()
    mock_http.__enter__.return_value.post.return_value = mock_token_resp
    mock_http.__enter__.return_value.get.return_value = mock_userinfo_resp

    with patch("app.main.httpx.Client", return_value=mock_http):
        resp = client.get(
            "/auth/google/callback?code=authcode&state=validstate",
            cookies={"oauth_state": "validstate"},
            follow_redirects=False,
        )
    assert resp.status_code in (302, 307)
    assert "token=" in resp.headers["location"]
