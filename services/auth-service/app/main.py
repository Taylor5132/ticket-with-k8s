import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@postgres:5432/auth_db")
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret")
JWT_ALGORITHM = "HS256"

engine: Engine = create_engine(DATABASE_URL, pool_pre_ping=True)
app = FastAPI(title="auth-service")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class DevLoginRequest(BaseModel):
    provider: str
    login_id: str
    display_name: str


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
        conn.execute(
            text(
                """
                INSERT INTO users (id, provider, login_id, display_name)
                VALUES (:id, :provider, :login_id, :display_name)
                ON CONFLICT (provider, login_id)
                DO UPDATE SET display_name = EXCLUDED.display_name, updated_at = now()
                """
            ),
            {"id": user_id, "provider": body.provider, "login_id": body.login_id, "display_name": body.display_name},
        )
        row = conn.execute(
            text("SELECT id, provider, login_id, display_name FROM users WHERE provider = :provider AND login_id = :login_id"),
            {"provider": body.provider, "login_id": body.login_id},
        ).mappings().one()
    user = dict(row)
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
