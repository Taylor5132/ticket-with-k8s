import os
import time
import uuid

import httpx
import redis
from redis.exceptions import ResponseError
from sqlalchemy import text

from .common import (
    CONSUMER_GROUP,
    EVENT_SERVICE_URL,
    PAYMENT_SERVICE_URL,
    REDIS_URL,
    SERVICE_TOKEN,
    STREAM_NAME,
    engine,
)


consumer_name = os.getenv("CONSUMER_NAME", f"worker-{uuid.uuid4().hex[:6]}")
r = redis.Redis.from_url(REDIS_URL, decode_responses=True, socket_timeout=None, socket_connect_timeout=5)


def ensure_group() -> None:
    try:
        r.xgroup_create(STREAM_NAME, CONSUMER_GROUP, id="0", mkstream=True)
    except ResponseError as exc:
        if "BUSYGROUP" not in str(exc):
            raise


def set_request_status(conn, request_id: str, status: str, failure_reason: str | None = None, booking_id: str | None = None) -> None:
    conn.execute(
        text(
            """
            UPDATE booking_requests
            SET status = :status,
                failure_reason = :failure_reason,
                booking_id = COALESCE(:booking_id, booking_id),
                updated_at = now()
            WHERE id = :id
            """
        ),
        {"id": request_id, "status": status, "failure_reason": failure_reason, "booking_id": booking_id},
    )


def mark_failed(request_id: str, reason: str) -> None:
    with engine.begin() as conn:
        set_request_status(conn, request_id, "FAILED", reason)


def payment_failure_reason(response: httpx.Response) -> str:
    try:
        detail = response.json().get("detail", {})
        if isinstance(detail, dict) and detail.get("code") == "INSUFFICIENT_POINTS":
            return "INSUFFICIENT_POINTS"
    except ValueError:
        pass
    return "PAYMENT_FAILED"


def process(fields: dict) -> None:
    request_id = fields["booking_request_id"]
    performance_id = fields["performance_id"]
    seat_id = fields["seat_id"]
    show_date = fields["show_date"]
    user_id = fields["user_id"]
    lock_key = f"{performance_id}:{show_date}:{seat_id}"

    with engine.begin() as conn:
        conn.execute(text("SELECT pg_advisory_xact_lock(hashtext(:lock_key))"), {"lock_key": lock_key})
        set_request_status(conn, request_id, "PROCESSING")

        occupied = conn.execute(
            text(
                "SELECT 1 FROM bookings WHERE performance_id = :performance_id AND performance_date = :show_date AND seat_id = :seat_id"
            ),
            {"performance_id": performance_id, "show_date": show_date, "seat_id": seat_id},
        ).first()
        if occupied:
            set_request_status(conn, request_id, "FAILED", "SEAT_ALREADY_BOOKED")
            return

        with httpx.Client(timeout=10.0) as client:
            performance_response = client.get(f"{EVENT_SERVICE_URL}/performances/{performance_id}")
            performance_response.raise_for_status()
            performance = performance_response.json()

            seat_response = client.get(f"{EVENT_SERVICE_URL}/internal/performances/{performance_id}/seats/{seat_id}")
            seat_response.raise_for_status()
            seat = seat_response.json()

            booking_id = f"booking-{uuid.uuid4().hex[:12]}"
            payment_response = client.post(
                f"{PAYMENT_SERVICE_URL}/payments/deduct",
                headers={"X-Service-Token": SERVICE_TOKEN},
                json={
                    "user_id": user_id,
                    "booking_request_id": request_id,
                    "booking_id": booking_id,
                    "amount": seat["price"],
                    "performance_title": performance["title"],
                },
            )
            if payment_response.status_code >= 400:
                set_request_status(conn, request_id, "FAILED", payment_failure_reason(payment_response))
                return

        inserted = conn.execute(
            text(
                """
                INSERT INTO bookings
                  (id, booking_request_id, user_id, performance_id, performance_title,
                   venue_name, performance_date, seat_id, seat_grade, paid_amount)
                VALUES
                  (:id, :booking_request_id, :user_id, :performance_id, :performance_title,
                   :venue_name, :performance_date, :seat_id, :seat_grade, :paid_amount)
                ON CONFLICT (performance_id, performance_date, seat_id) DO NOTHING
                RETURNING id
                """
            ),
            {
                "id": booking_id,
                "booking_request_id": request_id,
                "user_id": user_id,
                "performance_id": performance_id,
                "performance_title": performance["title"],
                "venue_name": performance["venue"]["name"],
                "performance_date": show_date,
                "seat_id": seat_id,
                "seat_grade": seat["grade"],
                "paid_amount": seat["price"],
            },
        ).first()
        if not inserted:
            set_request_status(conn, request_id, "FAILED", "SEAT_ALREADY_BOOKED")
            return
        set_request_status(conn, request_id, "CONFIRMED", booking_id=booking_id)


def main() -> None:
    ensure_group()
    while True:
        try:
            messages = r.xreadgroup(CONSUMER_GROUP, consumer_name, {STREAM_NAME: ">"}, count=1, block=5000)
        except Exception:
            continue
        if not messages:
            continue
        for _, stream_messages in messages:
            for message_id, fields in stream_messages:
                try:
                    process(fields)
                except Exception:
                    mark_failed(fields.get("booking_request_id", ""), "WORKER_ERROR")
                finally:
                    r.xack(STREAM_NAME, CONSUMER_GROUP, message_id)
        time.sleep(0.1)


if __name__ == "__main__":
    main()
