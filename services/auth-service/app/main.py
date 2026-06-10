import json
import os
import re
import secrets
import urllib.parse
from datetime import datetime, timedelta, timezone

import bcrypt
import httpx
import jwt
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@postgres:5432/auth_db")
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret")
JWT_ALGORITHM = "HS256"

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:5173/api/auth/google/callback")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

engine: Engine = create_engine(DATABASE_URL, pool_pre_ping=True)
app = FastAPI(title="auth-service")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
def migrate():
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash TEXT"))


class DevLoginRequest(BaseModel):
    provider: str
    login_id: str
    display_name: str


class SignupRequest(BaseModel):
    login_id: str
    password: str
    display_name: str


class LocalLoginRequest(BaseModel):
    login_id: str
    password: str


def make_user_id(login_id: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in login_id)
    return f"user-{safe}"


def issue_token(user: dict) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user["id"],
        "provider": user["provider"],
        "display_name": user["display_name"],
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=12)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def upsert_user(conn, id: str, provider: str, login_id: str, display_name: str) -> dict:
    conn.execute(
        text(
            """
            INSERT INTO users (id, provider, login_id, display_name)
            VALUES (:id, :provider, :login_id, :display_name)
            ON CONFLICT (provider, login_id)
            DO UPDATE SET display_name = EXCLUDED.display_name, updated_at = now()
            """
        ),
        {"id": id, "provider": provider, "login_id": login_id, "display_name": display_name},
    )
    row = conn.execute(
        text("SELECT id, provider, login_id, display_name FROM users WHERE provider = :provider AND login_id = :login_id"),
        {"provider": provider, "login_id": login_id},
    ).mappings().one()
    return dict(row)


def current_user(authorization: str = Header(default="")) -> dict:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "로그인이 필요한 기능입니다."})
    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "로그인이 필요한 기능입니다."})
    return {
        "id": payload["sub"],
        "provider": payload["provider"],
        "display_name": payload["display_name"],
    }


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/auth/dev-login")
def dev_login(body: DevLoginRequest) -> dict:
    user_id = make_user_id(body.login_id)
    with engine.begin() as conn:
        user = upsert_user(conn, user_id, body.provider, body.login_id, body.display_name)
    return {"access_token": issue_token(user), "token_type": "bearer", "user": user}


@app.post("/auth/signup")
def signup(body: SignupRequest) -> dict:
    if not re.fullmatch(r"[a-zA-Z0-9_]{4,20}", body.login_id):
        raise HTTPException(status_code=400, detail={"code": "INVALID_ID", "message": "아이디는 4~20자 영문·숫자·밑줄만 사용할 수 있습니다."})
    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail={"code": "WEAK_PASSWORD", "message": "비밀번호는 8자 이상이어야 합니다."})
    if not body.display_name.strip():
        raise HTTPException(status_code=400, detail={"code": "INVALID_NAME", "message": "닉네임을 입력해 주세요."})

    pw_hash = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
    user_id = make_user_id(f"local-{body.login_id}")
    try:
        with engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO users (id, provider, login_id, display_name, password_hash)
                    VALUES (:id, 'local', :login_id, :display_name, :password_hash)
                """),
                {"id": user_id, "login_id": body.login_id, "display_name": body.display_name.strip(), "password_hash": pw_hash},
            )
            row = conn.execute(
                text("SELECT id, provider, login_id, display_name FROM users WHERE provider = 'local' AND login_id = :login_id"),
                {"login_id": body.login_id},
            ).mappings().one()
    except Exception:
        raise HTTPException(status_code=409, detail={"code": "ID_TAKEN", "message": "이미 사용 중인 아이디입니다."})
    user = dict(row)
    return {"access_token": issue_token(user), "token_type": "bearer", "user": user}


@app.post("/auth/login")
def local_login(body: LocalLoginRequest) -> dict:
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT id, provider, login_id, display_name, password_hash FROM users WHERE provider = 'local' AND login_id = :login_id"),
            {"login_id": body.login_id},
        ).mappings().first()
    if not row or not row["password_hash"]:
        raise HTTPException(status_code=401, detail={"code": "INVALID_CREDENTIALS", "message": "아이디 또는 비밀번호가 올바르지 않습니다."})
    if not bcrypt.checkpw(body.password.encode(), row["password_hash"].encode()):
        raise HTTPException(status_code=401, detail={"code": "INVALID_CREDENTIALS", "message": "아이디 또는 비밀번호가 올바르지 않습니다."})
    user = {"id": row["id"], "provider": row["provider"], "login_id": row["login_id"], "display_name": row["display_name"]}
    return {"access_token": issue_token(user), "token_type": "bearer", "user": user}


@app.get("/auth/me")
def me(user: dict = Depends(current_user)) -> dict:
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT id, provider, login_id, display_name FROM users WHERE id = :id"),
            {"id": user["id"]},
        ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "요청한 정보를 찾을 수 없습니다."})
    return dict(row)


# ── Google OAuth ──────────────────────────────────────────────────────────────

@app.get("/auth/google")
def google_login():
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail={"code": "OAUTH_NOT_CONFIGURED", "message": "Google 로그인이 설정되지 않았습니다."})
    state = secrets.token_urlsafe(16)
    params = urllib.parse.urlencode({
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
    })
    response = RedirectResponse(f"{GOOGLE_AUTH_URL}?{params}")
    response.set_cookie("oauth_state", state, httponly=True, max_age=300, samesite="lax")
    return response


@app.get("/auth/google/callback")
def google_callback(request: Request, code: str = Query(default=""), state: str = Query(default=""), error: str = Query(default="")):
    if error:
        return RedirectResponse(f"{FRONTEND_URL}/?oauth_error={urllib.parse.quote(error)}")

    stored_state = request.cookies.get("oauth_state")
    if not stored_state or stored_state != state:
        return RedirectResponse(f"{FRONTEND_URL}/?oauth_error=invalid_state")

    try:
        with httpx.Client(timeout=10.0) as client:
            token_resp = client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "redirect_uri": GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code",
                },
            )
            token_resp.raise_for_status()
            access_token = token_resp.json()["access_token"]

            userinfo_resp = client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            userinfo_resp.raise_for_status()
            userinfo = userinfo_resp.json()
    except Exception:
        return RedirectResponse(f"{FRONTEND_URL}/?oauth_error=google_api_error")

    google_sub = userinfo["sub"]
    display_name = userinfo.get("name") or userinfo.get("email", "Google 사용자")
    user_id = make_user_id(google_sub)

    with engine.begin() as conn:
        user = upsert_user(conn, user_id, "google", google_sub, display_name)

    jwt_token = issue_token(user)
    user_param = urllib.parse.quote(json.dumps(user, ensure_ascii=False))
    response = RedirectResponse(f"{FRONTEND_URL}/?token={jwt_token}&user={user_param}")
    response.delete_cookie("oauth_state")
    return response
