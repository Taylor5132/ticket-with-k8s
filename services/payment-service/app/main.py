# test
import os
import uuid

import jwt
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@postgres:5432/payment_db")
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret")
SERVICE_TOKEN = os.getenv("SERVICE_TOKEN", "dev-service-token")
JWT_ALGORITHM = "HS256"

engine: Engine = create_engine(DATABASE_URL, pool_pre_ping=True)
app = FastAPI(title="payment-service")
from app.telemetry import configure_tracing; configure_tracing(app, "payment-service")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class DeductRequest(BaseModel):
    user_id: str
    booking_request_id: str
    booking_id: str
    amount: int
    performance_title: str


def default_balance(user_id: str) -> int:
    return 300000 if "demo-rich" in user_id else 100000


def current_user(authorization: str = Header(default="")) -> dict:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "로그인이 필요한 기능입니다."})
    try:
        payload = jwt.decode(authorization.removeprefix("Bearer ").strip(), JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "로그인이 필요한 기능입니다."})
    return {"id": payload["sub"], "display_name": payload["display_name"], "provider": payload["provider"]}


def ensure_balance(conn, user_id: str) -> int:
    row = conn.execute(text("SELECT balance FROM point_balances WHERE user_id = :user_id"), {"user_id": user_id}).first()
    if row:
        return int(row.balance)
    balance = default_balance(user_id)
    conn.execute(text("INSERT INTO point_balances (user_id, balance) VALUES (:user_id, :balance)"), {"user_id": user_id, "balance": balance})
    return balance


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/payments/me/balance")
def balance(user: dict = Depends(current_user)) -> dict:
    with engine.begin() as conn:
        balance_value = ensure_balance(conn, user["id"])
    return {"balance": balance_value}


@app.get("/payments/me/history")
def history(user: dict = Depends(current_user)) -> dict:
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT id, booking_request_id, booking_id, performance_title, amount, status, paid_at
                FROM payment_history
                WHERE user_id = :user_id
                ORDER BY paid_at DESC
                """
            ),
            {"user_id": user["id"]},
        ).mappings().all()
    return {
        "items": [
            {
                **dict(row),
                "paid_at": row["paid_at"].isoformat(),
            }
            for row in rows
        ]
    }


@app.post("/payments/deduct")
def deduct(body: DeductRequest, x_service_token: str = Header(default="")) -> dict:
    if x_service_token != SERVICE_TOKEN:
        raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "요청 권한이 없습니다."})
    with engine.begin() as conn:
        existing = conn.execute(
            text("SELECT id, user_id, amount FROM payment_history WHERE booking_request_id = :booking_request_id"),
            {"booking_request_id": body.booking_request_id},
        ).mappings().first()
        if existing:
            return {"payment_id": existing["id"], "balance_after": ensure_balance(conn, existing["user_id"])}

        ensure_balance(conn, body.user_id)
        row = conn.execute(
            text("SELECT balance FROM point_balances WHERE user_id = :user_id FOR UPDATE"),
            {"user_id": body.user_id},
        ).first()
        balance_value = int(row.balance)
        if balance_value < body.amount:
            raise HTTPException(status_code=409, detail={"code": "INSUFFICIENT_POINTS", "message": "보유 포인트가 부족합니다."})

        balance_after = balance_value - body.amount
        payment_id = f"pay-{uuid.uuid4().hex[:12]}"
        conn.execute(
            text("UPDATE point_balances SET balance = :balance, updated_at = now() WHERE user_id = :user_id"),
            {"balance": balance_after, "user_id": body.user_id},
        )
        conn.execute(
            text(
                """
                INSERT INTO payment_history
                  (id, user_id, booking_request_id, booking_id, performance_title, amount, status)
                VALUES
                  (:id, :user_id, :booking_request_id, :booking_id, :performance_title, :amount, 'PAID')
                """
            ),
            {
                "id": payment_id,
                "user_id": body.user_id,
                "booking_request_id": body.booking_request_id,
                "booking_id": body.booking_id,
                "performance_title": body.performance_title,
                "amount": body.amount,
            },
        )
    return {"payment_id": payment_id, "balance_after": balance_after}
