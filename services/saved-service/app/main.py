#test
from typing import Annotated
import os

import httpx
import jwt
import redis
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware


REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
EVENT_SERVICE_URL = os.getenv("EVENT_SERVICE_URL", "http://event-service:8000")
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret")
JWT_ALGORITHM = "HS256"

r = redis.Redis.from_url(REDIS_URL, decode_responses=True)
app = FastAPI(title="saved-service")
from app.telemetry import configure_tracing; configure_tracing(app, "saved-service")
from prometheus_fastapi_instrumentator import Instrumentator
Instrumentator().instrument(app).expose(app)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def current_user(authorization: Annotated[str, Header()] = "") -> dict:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "로그인이 필요한 기능입니다."})
    try:
        payload = jwt.decode(authorization.removeprefix("Bearer ").strip(), JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "로그인이 필요한 기능입니다."})
    return {"id": payload["sub"]}


def key(user_id: str) -> str:
    return f"saved:user:{user_id}"


def card(detail: dict) -> dict:
    venue = detail.get("venue") or {}
    return {
        "id": detail["id"],
        "title": detail["title"],
        "poster_url": detail["poster_url"],
        "venue_name": venue.get("name"),
        "area": venue.get("province"),
        "genre": detail["genre"],
        "start_date": detail["start_date"],
        "end_date": detail["end_date"],
    }


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/saved/me")
def saved(user: Annotated[dict, Depends(current_user)]) -> dict:
    ids = sorted(r.smembers(key(user["id"])), key=lambda item: int(item) if item.isdigit() else item)
    items = []
    with httpx.Client(timeout=5.0) as client:
        for performance_id in ids:
            response = client.get(f"{EVENT_SERVICE_URL}/performances/{performance_id}")
            if response.status_code == 200:
                items.append(card(response.json()))
    return {"items": items}


@app.post("/saved/performances/{performance_id}")
def add_saved(performance_id: str, user: Annotated[dict, Depends(current_user)]) -> dict:
    r.sadd(key(user["id"]), performance_id)
    return {"performance_id": performance_id, "saved": True}


@app.delete("/saved/performances/{performance_id}")
def delete_saved(performance_id: str, user: Annotated[dict, Depends(current_user)]) -> dict:
    r.srem(key(user["id"]), performance_id)
    return {"performance_id": performance_id, "saved": False}
