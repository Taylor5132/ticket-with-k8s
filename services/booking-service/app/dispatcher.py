"""Dispatcher — 대기줄(Sorted Set)에서 앞 사람을 빼서 입장 처리 스트림(work-stream)으로 옮긴다.

제어 손잡이 1: 줄에서 빼는 속도(ADMISSION_RATE)가 결제/예매 시스템으로 가는 유입량을 결정한다.
ZPOPMIN+XADD는 비원자적이라 사이에 죽으면 일감이 증발하므로, Lua 스크립트로 원자 실행한다.

실행: uv run python -m app.dispatcher   (booking-service 이미지에서 별도 Deployment로)
"""
import os
import time

import redis

from .common import (
    ACTIVE_QUEUES_KEY,
    ADMISSION_RATE,
    DISPATCH_LUA,
    REDIS_URL,
    WORK_STREAM,
    queue_key,
)

TICK_SECONDS = float(os.getenv("DISPATCHER_TICK_SECONDS", "1.0"))

r = redis.Redis.from_url(REDIS_URL, decode_responses=True)
_dispatch = r.register_script(DISPATCH_LUA)


def dispatch_once() -> int:
    """활성 큐를 한 바퀴 돌며 각 큐에서 (ADMISSION_RATE × TICK)명을 핸드오프.
    빈 큐는 active-queues에서 제거. 반환: 이번 틱에 핸드오프한 총 인원."""
    members = r.smembers(ACTIVE_QUEUES_KEY)
    count_per_queue = max(1, int(ADMISSION_RATE * TICK_SECONDS))
    total_moved = 0
    for member in members:
        performance_id, _, show_date = member.partition(":")
        key = queue_key(performance_id, show_date)
        moved = _dispatch(keys=[key, WORK_STREAM], args=[count_per_queue, performance_id, show_date])
        total_moved += int(moved)
        if r.zcard(key) == 0:  # 다 빠진 큐는 순회 대상에서 제외
            r.srem(ACTIVE_QUEUES_KEY, member)
    return total_moved


def main() -> None:
    print(f"[dispatcher] start — rate={ADMISSION_RATE}/s tick={TICK_SECONDS}s stream={WORK_STREAM}", flush=True)
    while True:
        try:
            moved = dispatch_once()
            if moved:
                print(f"[dispatcher] handed off {moved}", flush=True)
        except Exception as exc:  # Redis 일시 장애 등 — 죽지 않고 재시도
            print(f"[dispatcher] error: {exc}", flush=True)
        time.sleep(TICK_SECONDS)


if __name__ == "__main__":
    main()
