"""Admission Worker — work-stream을 소비해 입장 토큰을 발급한다.

Consumer Group으로 일감을 나눠 받고, 토큰 발급 후 XACK한다.
처리 도중 죽으면 일감이 PEL에 남으므로, 주기적으로 XAUTOCLAIM으로 회수해 무유실을 보장한다.
KEDA는 이 워커(Deployment)를 work-stream lag 기준으로 스케일한다.

실행: uv run python -m app.admission_worker
"""
import os
import socket
import time

import redis

from .common import (
    ADMISSION_GROUP,
    ADMISSION_TOKEN_TTL,
    REDIS_URL,
    WORK_STREAM,
    ensure_admission_group,
    token_key,
)

CONSUMER_NAME = os.getenv("CONSUMER_NAME", f"admission-{socket.gethostname()}")
BATCH = int(os.getenv("ADMISSION_BATCH", "10"))
BLOCK_MS = int(os.getenv("ADMISSION_BLOCK_MS", "5000"))
CLAIM_MIN_IDLE_MS = int(os.getenv("ADMISSION_CLAIM_MIN_IDLE_MS", "30000"))  # 30s 방치된 일감 회수
CLAIM_EVERY = int(os.getenv("ADMISSION_CLAIM_EVERY", "10"))  # N 루프마다 회수 시도

r = redis.Redis.from_url(REDIS_URL, decode_responses=True)


def issue_token(fields: dict) -> None:
    """일감 = 입장 처리. 핵심 작업은 '입장 토큰 발급'(TTL)."""
    performance_id = fields["performance_id"]
    show_date = fields["show_date"]
    user_id = fields["user_id"]
    r.set(token_key(performance_id, show_date, user_id), "valid", ex=ADMISSION_TOKEN_TTL)


def process_entries(entries) -> int:
    """[(id, fields), ...]를 처리하고 XACK. 반환: 처리 건수."""
    done = 0
    for message_id, fields in entries:
        try:
            issue_token(fields)
        except Exception as exc:
            print(f"[admission] process error {message_id}: {exc}", flush=True)
            continue  # XACK 안 함 → PEL에 남아 다음 회수 때 재처리
        r.xack(WORK_STREAM, ADMISSION_GROUP, message_id)
        done += 1
    return done


def reclaim_stale() -> int:
    """XAUTOCLAIM: 죽은 워커가 PEL에 남긴 idle 일감을 회수해 재처리.
    이게 없으면 워커 장애 시 해당 일감이 영원히 PEL에 묶여 입장 불가."""
    reclaimed = 0
    cursor = "0-0"
    while True:
        cursor, entries, _ = r.xautoclaim(
            WORK_STREAM, ADMISSION_GROUP, CONSUMER_NAME,
            min_idle_time=CLAIM_MIN_IDLE_MS, start_id=cursor, count=BATCH,
        )
        if entries:
            reclaimed += process_entries(entries)
        if cursor == "0-0" or not entries:
            break
    return reclaimed


def main() -> None:
    ensure_admission_group(r)
    print(f"[admission] start — consumer={CONSUMER_NAME} stream={WORK_STREAM} group={ADMISSION_GROUP}", flush=True)
    loop = 0
    while True:
        loop += 1
        try:
            resp = r.xreadgroup(
                ADMISSION_GROUP, CONSUMER_NAME, {WORK_STREAM: ">"},
                count=BATCH, block=BLOCK_MS,
            )
            if resp:
                for _stream, entries in resp:
                    n = process_entries(entries)
                    if n:
                        print(f"[admission] issued {n} tokens", flush=True)
            if loop % CLAIM_EVERY == 0:  # 주기적 회수 루프
                rc = reclaim_stale()
                if rc:
                    print(f"[admission] reclaimed {rc} stale", flush=True)
        except Exception as exc:
            print(f"[admission] loop error: {exc}", flush=True)
            time.sleep(1)


if __name__ == "__main__":
    main()
