#test
from typing import Annotated
import uuid

import redis
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text

from .common import (
    ENFORCE_ADMISSION_TOKEN,
    QUEUE_TTL,
    REDIS_URL,
    STREAM_NAME,
    ACTIVE_QUEUES_KEY,
    current_user,
    engine,
    ensure_admission_group,
    generate_seats,
    queue_key,
    queue_member,
    seq_key,
    token_key,
)


r = redis.Redis.from_url(REDIS_URL, decode_responses=True)
app = FastAPI(title="booking-service")
from app.telemetry import configure_tracing; configure_tracing(app, "booking-service")
from prometheus_fastapi_instrumentator import Instrumentator
Instrumentator().instrument(app).expose(app)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
def _init_admission() -> None:
    # work-stream Consumer Group 멱등 생성 (Dispatcher/Worker 배포 전이라도 안전)
    try:
        ensure_admission_group(r)
    except Exception:
        pass  # Redis 미가용 시 기동은 막지 않음 (워커가 재시도)


class BookingRequestCreate(BaseModel):
    performance_id: str
    seat_id: str
    show_date: str  # YYYY-MM-DD


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/performances/{performance_id}/seat-availability")
@app.get("/performances/{performance_id}/seat-availability")
def seat_availability(performance_id: str, show_date: Annotated[str, Query()]) -> dict:
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
def create_booking_request(body: BookingRequestCreate, user: Annotated[dict, Depends(current_user)]) -> dict:
    # 입장 토큰 게이트: ENFORCE_ADMISSION_TOKEN=true일 때만 강제 (기본 off → 기존 프론트 안 깨짐)
    if ENFORCE_ADMISSION_TOKEN and r.get(token_key(body.performance_id, body.show_date, user["id"])) is None:
        raise HTTPException(status_code=403, detail={"code": "NO_ADMISSION_TOKEN", "message": "대기열을 통과한 뒤 예매할 수 있습니다."})

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
def booking_request(request_id: str, user: Annotated[dict, Depends(current_user)]) -> dict:
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
def queue_join(performance_id: str, show_date: str, user: Annotated[dict, Depends(current_user)]) -> dict:
    """대기줄 진입. 번호표(INCR seq)를 score로 ZADD → 선착순 FIFO.
    이미 입장 토큰이 있으면 바로 admitted."""
    uid = user["id"]
    if r.get(token_key(performance_id, show_date, uid)) is not None:
        return {"admitted": True, "position": 0, "total": 0}

    key = queue_key(performance_id, show_date)
    if r.zscore(key, uid) is None:  # 처음 진입한 사람만 번호표 발급
        seq = r.incr(seq_key(performance_id, show_date))  # 원자적 — 번호 안 겹침
        r.zadd(key, {uid: seq}, nx=True)
        r.sadd(ACTIVE_QUEUES_KEY, queue_member(performance_id, show_date))  # Dispatcher 순회 대상 등록
    r.expire(key, QUEUE_TTL)
    r.expire(seq_key(performance_id, show_date), QUEUE_TTL)

    position = r.zrank(key, uid)
    total = r.zcard(key)
    return {"admitted": False, "position": int(position) + 1 if position is not None else 0, "total": int(total)}


@app.get("/queue/status")
def queue_status(performance_id: str, show_date: str, user: Annotated[dict, Depends(current_user)]) -> dict:
    """입장 여부는 '토큰 존재'로 판정 (Dispatcher가 줄에서 빼고 Worker가 토큰 발급).
    줄에도 없고 토큰도 없으면(아직 토큰 발급 전 in-flight 등) 대기 상태로 응답."""
    uid = user["id"]
    if r.get(token_key(performance_id, show_date, uid)) is not None:
        return {"admitted": True, "position": 0, "total": 0}

    key = queue_key(performance_id, show_date)
    position = r.zrank(key, uid)
    total = r.zcard(key)
    if position is None:
        # 줄에서 빠졌지만 아직 토큰 미발급(스트림 처리 중) → 잠시 대기로 응답
        return {"admitted": False, "position": 0, "total": int(total)}
    return {"admitted": False, "position": int(position) + 1, "total": int(total)}


@app.get("/bookings/me")
def my_bookings(user: Annotated[dict, Depends(current_user)]) -> dict:
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

