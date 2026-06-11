import os
import re
from datetime import date, timedelta

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@postgres:5432/event_db")
engine: Engine = create_engine(DATABASE_URL, pool_pre_ping=True)
app = FastAPI(title="event-service")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

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

# Korean day names → Python weekday (0=Mon … 6=Sun)
_KO_DOW = {"월": 0, "화": 1, "수": 2, "목": 3, "금": 4, "토": 5, "일": 6}


def _schedule_days(schedule_text: str) -> set[int]:
    """
    Parse KOPIS-style schedule text and return the set of weekday ints the
    performance runs on (0=Monday … 6=Sunday).

    Handles:
      "금요일(19:30)"
      "토요일 ~ 일요일(14:00)"
      "화요일 ~ 금요일(19:30), 토요일 ~ 일요일(15:00)"
    Falls back to weekends {5, 6} when the text is empty or unparseable.
    """
    if not schedule_text:
        return {5, 6}
    cleaned = re.sub(r"\([^)]*\)", "", schedule_text)
    days: set[int] = set()
    for m in re.finditer(r"([월화수목금토일])요일\s*~\s*([월화수목금토일])요일", cleaned):
        s, e = _KO_DOW[m.group(1)], _KO_DOW[m.group(2)]
        days.update(range(s, e + 1) if e >= s else list(range(s, 7)) + list(range(0, e + 1)))
    for m in re.finditer(r"([월화수목금토일])요일", cleaned):
        days.add(_KO_DOW[m.group(1)])
    return days or {5, 6}


def compute_schedules(start: date | None, end: date | None, schedule_text: str | None, max_dates: int = 20) -> list[str]:
    if not start or not end:
        return []
    days = _schedule_days(schedule_text or "")
    result: list[str] = []
    cur = start
    while cur <= end and len(result) < max_dates:
        if cur.weekday() in days:
            result.append(cur.isoformat())
        cur += timedelta(days=1)
    return result


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


def list_intro_images(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [item for item in raw.split("|") if item]


def price_text() -> str:
    return "VIP석 150,000원, R석 120,000원, S석 90,000원, A석 60,000원"


def performance_card(row) -> dict:
    return {
        "id": str(row["id"]),
        "kopis_id": row["kopis_id"],
        "title": row["title"],
        "poster_url": row["poster_url"],
        "venue_name": row["venue_name"],
        "area": row["province"],
        "genre": row["genre"],
        "start_date": row["start_date"].isoformat() if row["start_date"] else None,
        "end_date": row["end_date"].isoformat() if row["end_date"] else None,
        "status": row["status"],
    }


@app.get("/performances")
def performances(
    genre: str | None = Query(default=None),
    area: str | None = Query(default=None),
    status: str | None = Query(default=None),
) -> dict:
    clauses = []
    params = {}
    if genre:
        clauses.append("p.genre = :genre")
        params["genre"] = genre
    if area:
        clauses.append("v.province = :area")
        params["area"] = area
    if status:
        clauses.append("p.status = :status")
        params["status"] = status
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"""
        SELECT p.id, p.kopis_id, p.title, p.poster_url, p.genre, p.status,
               p.start_date, p.end_date, v.name AS venue_name, v.province
        FROM performances p
        JOIN venues v ON v.id = p.venue_id
        {where}
        ORDER BY p.start_date ASC, p.id ASC
    """
    with engine.begin() as conn:
        rows = conn.execute(text(sql), params).mappings().all()
    return {"items": [performance_card(row) for row in rows]}


@app.get("/performances/{performance_id}")
def performance_detail(performance_id: str) -> dict:
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT p.*, v.kopis_id AS venue_kopis_id, v.name AS venue_name,
                       v.address, v.province, v.district, v.seat_capacity,
                       v.phone, v.latitude, v.longitude, v.halls_text
                FROM performances p
                JOIN venues v ON v.id = p.venue_id
                WHERE p.id = :id
                """
            ),
            {"id": performance_id},
        ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "요청한 정보를 찾을 수 없습니다."})
    guidance = row["schedule"] or row["description"] or ""
    schedules = compute_schedules(row["start_date"], row["end_date"], row["schedule"])
    return {
        "id": str(row["id"]),
        "kopis_id": row["kopis_id"],
        "title": row["title"],
        "poster_url": row["poster_url"],
        "genre": row["genre"],
        "status": row["status"],
        "start_date": row["start_date"].isoformat() if row["start_date"] else None,
        "end_date": row["end_date"].isoformat() if row["end_date"] else None,
        "is_open_run": row["is_open_run"] == "Y",
        "cast_text": row["cast_text"],
        "runtime": row["runtime"],
        "age_rating": row["age_rating"],
        "price_text": price_text(),
        "guidance_text": guidance,
        "intro_image_urls": list_intro_images(row["intro_image_urls"]),
        "schedules": schedules,
        "venue": {
            "id": str(row["venue_id"]),
            "kopis_id": row["venue_kopis_id"],
            "name": row["venue_name"],
            "address": row["address"],
            "province": row["province"],
            "district": row["district"],
            "seat_capacity": row["seat_capacity"],
            "phone": row["phone"],
            "latitude": float(row["latitude"]) if row["latitude"] is not None else None,
            "longitude": float(row["longitude"]) if row["longitude"] is not None else None,
            "halls_text": row["halls_text"],
        },
    }


@app.get("/internal/performances/{performance_id}/seats/{seat_id}")
def seat_definition(performance_id: str, seat_id: str) -> dict:
    row = seat_id.split("-", 1)[0]
    if row not in GRADE_RULES:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "요청한 정보를 찾을 수 없습니다."})
    grade, price = GRADE_RULES[row]
    return {"performance_id": performance_id, "seat_id": seat_id, "grade": grade, "price": price}
