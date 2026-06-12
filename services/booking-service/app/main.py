import os
import time
import uuid

import redis
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text

from .common import REDIS_URL, STREAM_NAME, current_user, engine, generate_seats


r = redis.Redis.from_url(REDIS_URL, decode_responses=True)
app = FastAPI(title="booking-service")
from app.telemetry import configure_tracing; configure_tracing(app, "booking-service")

QUEUE_ADMISSION_RATE = float(os.getenv("QUEUE_ADMISSION_RATE", "3"))  # users admitted per second
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class BookingRequestCreate(BaseModel):
    performance_id: str
    seat_id: str
    show_date: str  # YYYY-MM-DD


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/performances/{performance_id}/seat-availability")
def seat_availability(performance_id: str, show_date: str = Query(...)) -> dict:
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                "SELECT seat_id FROM bookings WHERE performance_id = :pid AND performance_date = :show_date"
            ),
            {"pid": performance_id, "show_date": show_date},
        ).all()
    occupied = {row.seat_id for row in rows}
    return {"performance_id": performance_id, "show_date": show_date, "seats": generate_seats(occupied)}


@app.post("/booking-requests")
def create_booking_request(body: BookingRequestCreate, user: dict = Depends(current_user)) -> dict:
    valid_seat_ids = {seat["seat_id"] for seat in generate_seats()}
    if body.seat_id not in valid_seat_ids:
        raise HTTPException(status_code=400, detail={"code": "INVALID_SEAT", "message": "좌석을 선택해 주세요."})

    request_id = f"br-{uuid.uuid4().hex[:12]}"
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO booking_requests (id, user_id, performance_id, seat_id, show_date, status)
                VALUES (:id, :user_id, :performance_id, :seat_id, :show_date, 'PENDING')
                """
            ),
            {
                "id": request_id,
                "user_id": user["id"],
                "performance_id": body.performance_id,
                "seat_id": body.seat_id,
                "show_date": body.show_date,
            },
        )
    r.xadd(
        STREAM_NAME,
        {
            "booking_request_id": request_id,
            "performance_id": body.performance_id,
            "seat_id": body.seat_id,
            "show_date": body.show_date,
            "user_id": user["id"],
        },
    )
    return {"request_id": request_id, "status": "PENDING"}


@app.get("/booking-requests/{request_id}")
def booking_request(request_id: str, user: dict = Depends(current_user)) -> dict:
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT id, status, failure_reason, booking_id, show_date
                FROM booking_requests
                WHERE id = :id AND user_id = :user_id
                """
            ),
            {"id": request_id, "user_id": user["id"]},
        ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "요청한 정보를 찾을 수 없습니다."})
    return {
        "request_id": row["id"],
        "status": row["status"],
        "failure_reason": row["failure_reason"],
        "booking_id": row["booking_id"],
        "show_date": row["show_date"].isoformat() if row["show_date"] else None,
    }


@app.post("/queue/join")
def queue_join(performance_id: str, show_date: str, user: dict = Depends(current_user)) -> dict:
    key = f"queue:{performance_id}:{show_date}"
    r.zadd(key, {user["id"]: time.time()}, nx=True)  # nx=True: don't overwrite existing score
    r.expire(key, 3600)
    position = r.zrank(key, user["id"])
    total = r.zcard(key)
    return {"position": int(position) + 1, "total": int(total)}


@app.get("/queue/status")
def queue_status(performance_id: str, show_date: str, user: dict = Depends(current_user)) -> dict:
    key = f"queue:{performance_id}:{show_date}"
    if r.zscore(key, user["id"]) is None:
        return {"admitted": True, "position": 0, "total": 0}

    # Advance queue: remove users admitted since the first joiner entered
    earliest = r.zrange(key, 0, 0, withscores=True)
    if earliest:
        elapsed = time.time() - earliest[0][1]
        admitted_count = int(elapsed * QUEUE_ADMISSION_RATE)
        if admitted_count > 0:
            r.zremrangebyrank(key, 0, admitted_count - 1)

    position = r.zrank(key, user["id"])
    if position is None:
        return {"admitted": True, "position": 0, "total": 0}
    total = r.zcard(key)
    return {"admitted": False, "position": int(position) + 1, "total": int(total)}


@app.get("/bookings/me")
def my_bookings(user: dict = Depends(current_user)) -> dict:
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT id, performance_id, performance_title, venue_name, performance_date,
                       seat_id, seat_grade, paid_amount, booked_at
                FROM bookings
                WHERE user_id = :user_id
                ORDER BY booked_at DESC
                """
            ),
            {"user_id": user["id"]},
        ).mappings().all()
    return {
        "items": [
            {
                **dict(row),
                "performance_date": row["performance_date"].isoformat(),
                "booked_at": row["booked_at"].isoformat(),
            }
            for row in rows
        ]
    }

