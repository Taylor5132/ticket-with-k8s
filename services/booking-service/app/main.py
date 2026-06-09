import uuid

import redis
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text

from .common import REDIS_URL, STREAM_NAME, current_user, engine, generate_seats


r = redis.Redis.from_url(REDIS_URL, decode_responses=True)
app = FastAPI(title="booking-service")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class BookingRequestCreate(BaseModel):
    performance_id: str
    seat_id: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/performances/{performance_id}/seat-availability")
def seat_availability(performance_id: str) -> dict:
    with engine.begin() as conn:
        rows = conn.execute(
            text("SELECT seat_id FROM bookings WHERE performance_id = :performance_id"),
            {"performance_id": performance_id},
        ).all()
    occupied = {row.seat_id for row in rows}
    return {"performance_id": performance_id, "seats": generate_seats(occupied)}


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
                INSERT INTO booking_requests (id, user_id, performance_id, seat_id, status)
                VALUES (:id, :user_id, :performance_id, :seat_id, 'PENDING')
                """
            ),
            {"id": request_id, "user_id": user["id"], "performance_id": body.performance_id, "seat_id": body.seat_id},
        )
    r.xadd(
        STREAM_NAME,
        {
            "booking_request_id": request_id,
            "performance_id": body.performance_id,
            "seat_id": body.seat_id,
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
                SELECT id, status, failure_reason, booking_id
                FROM booking_requests
                WHERE id = :id AND user_id = :user_id
                """
            ),
            {"id": request_id, "user_id": user["id"]},
        ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "요청한 정보를 찾을 수 없습니다."})
    return {"request_id": row["id"], "status": row["status"], "failure_reason": row["failure_reason"], "booking_id": row["booking_id"]}


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
