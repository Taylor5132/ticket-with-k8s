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

# ── 대기열(Waiting Queue) 파이프라인 상수 ──────────────────────────
# 설계 근거: docs/ops/redis-queue-architecture.md
WORK_STREAM = "work-stream"            # 입장 처리 스트림 (단일, 전 공연 공용)
ADMISSION_GROUP = "admission-workers"  # 입장 워커 Consumer Group
ADMISSION_RATE = float(os.getenv("QUEUE_ADMISSION_RATE", "3"))     # 큐당 초당 입장 인원
ADMISSION_TOKEN_TTL = int(os.getenv("ADMISSION_TOKEN_TTL", "600")) # 입장 토큰 수명(초)
QUEUE_TTL = int(os.getenv("QUEUE_TTL", "3600"))                    # 유휴 큐 자동 만료(초)
ENFORCE_ADMISSION_TOKEN = os.getenv("ENFORCE_ADMISSION_TOKEN", "false").lower() == "true"
ACTIVE_QUEUES_KEY = "active-queues"    # Dispatcher가 순회할 활성 큐 레지스트리(Set)


def queue_key(performance_id: str, show_date: str) -> str:
    return f"queue:{performance_id}:{show_date}"


def seq_key(performance_id: str, show_date: str) -> str:
    return f"seq:{performance_id}:{show_date}"


def token_key(performance_id: str, show_date: str, user_id: str) -> str:
    return f"token:{performance_id}:{show_date}:{user_id}"


def queue_member(performance_id: str, show_date: str) -> str:
    """active-queues Set에 넣는 멤버 식별자."""
    return f"{performance_id}:{show_date}"


# Dispatcher 원자 핸드오프: ZSET 앞 N명을 빼서 work-stream에 XADD.
# ZPOPMIN과 XADD 사이에 죽어도 일감이 증발하지 않도록 Lua 단일 실행으로 원자화.
#   KEYS[1] = queue:{perf}:{date}   (대기줄 ZSET)
#   KEYS[2] = work-stream           (입장 처리 스트림)
#   ARGV[1] = count                 (이번에 뺄 인원)
#   ARGV[2] = performance_id
#   ARGV[3] = show_date
# 반환: 실제로 핸드오프한 인원 수
DISPATCH_LUA = """
local popped = redis.call('ZPOPMIN', KEYS[1], tonumber(ARGV[1]))
local moved = 0
for i = 1, #popped, 2 do
  local user_id = popped[i]
  redis.call('XADD', KEYS[2], '*',
    'user_id', user_id,
    'performance_id', ARGV[2],
    'show_date', ARGV[3])
  moved = moved + 1
end
return moved
"""

engine: Engine = create_engine(DATABASE_URL, pool_pre_ping=True)


def ensure_admission_group(client) -> None:
    """work-stream의 Consumer Group을 멱등하게 생성 (이미 있으면 무시).
    MKSTREAM으로 스트림이 없어도 함께 생성한다."""
    try:
        client.xgroup_create(WORK_STREAM, ADMISSION_GROUP, id="0", mkstream=True)
    except Exception as exc:  # redis.exceptions.ResponseError: BUSYGROUP
        if "BUSYGROUP" not in str(exc):
            raise

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
