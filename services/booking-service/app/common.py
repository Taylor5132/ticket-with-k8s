import os

import jwt
from fastapi import Header, HTTPException
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@postgres:5432/booking_db")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
EVENT_SERVICE_URL = os.getenv("EVENT_SERVICE_URL", "http://event-service:8000")
PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL", "http://payment-service:8000")
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret")
SERVICE_TOKEN = os.getenv("SERVICE_TOKEN", "dev-service-token")
JWT_ALGORITHM = "HS256"
STREAM_NAME = "booking.requests"
CONSUMER_GROUP = "booking-workers"

engine: Engine = create_engine(DATABASE_URL, pool_pre_ping=True)

GRADE_RULES = {
    "A": ("VIP", 150000),
    "B": ("VIP", 150000),
    "C": ("R", 120000),
    "D": ("R", 120000),
    "E": ("S", 90000),
    "F": ("S", 90000),
    "G": ("A", 60000),
    "H": ("A", 60000),
}


def current_user(authorization: str = Header(default="")) -> dict:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "로그인이 필요한 기능입니다."})
    try:
        payload = jwt.decode(authorization.removeprefix("Bearer ").strip(), JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "로그인이 필요한 기능입니다."})
    return {"id": payload["sub"], "display_name": payload["display_name"], "provider": payload["provider"]}


def generate_seats(occupied: set[str] | None = None) -> list[dict]:
    occupied = occupied or set()
    seats = []
    for row in "ABCDEFGH":
        grade, price = GRADE_RULES[row]
        for number in range(1, 11):
            seat_id = f"{row}-{number}"
            seats.append(
                {
                    "seat_id": seat_id,
                    "row": row,
                    "number": number,
                    "grade": grade,
                    "price": price,
                    "status": "OCCUPIED" if seat_id in occupied else "AVAILABLE",
                }
            )
    return seats
