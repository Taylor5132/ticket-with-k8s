#test
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
from app.telemetry import configure_tracing; configure_tracing(app, "event-service")
from prometheus_fastapi_instrumentator import Instrumentator
Instrumentator().instrument(app).expose(app)
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
    limit: int | None = Query(default=None, ge=1, le=2000),
    offset: int = Query(default=0, ge=0),
) -> dict:
    # The dashboard fetches the FULL catalog once and derives every view
    # client-side (filters, "opening soon", grid), so the default must return
    # all rows — capping it hid most of the catalog and broke the homepage.
    # limit/offset are optional opt-in pagination for other clients. The OOM
    # risk that motivated a cap is mitigated elsewhere (memory 512Mi + the
    # load test no longer hammers this endpoint).
    clauses = []
    fparams: dict = {}
    if genre:
        clauses.append("p.genre = :genre")
        fparams["genre"] = genre
    if area:
        clauses.append("v.province = :area")
        fparams["area"] = area
    if status:
        clauses.append("p.status = :status")
        fparams["status"] = status
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"""
        SELECT p.id, p.kopis_id, p.title, p.poster_url, p.genre, p.status,
               p.start_date, p.end_date, v.name AS venue_name, v.province
        FROM performances p
        JOIN venues v ON v.id = p.venue_id
        {where}
        ORDER BY p.start_date ASC, p.id ASC
    """
    params = dict(fparams)
    if limit is not None:
        sql += " LIMIT :limit OFFSET :offset"
        params["limit"] = limit
        params["offset"] = offset
    # engine.connect() (not begin()): a read does not need a BEGIN/COMMIT txn.
    with engine.connect() as conn:
        rows = conn.execute(text(sql), params).mappings().all()
        # total for the active filter — lets the infinite-scroll client know
        # when to stop and show the result count without fetching every row.
        total = (
            conn.execute(
                text(f"SELECT count(*) FROM performances p JOIN venues v ON v.id = p.venue_id {where}"),
                fparams,
            ).scalar_one()
            if limit is not None
            else len(rows)
        )
    return {"items": [performance_card(row) for row in rows], "total": total}


@app.get("/performances/facets")
def performances_facets() -> dict:
    """Global filter facets (genre/area counts) + catalog total.

    Replaces the dashboard's client-side countBy over the full list, so the
    homepage no longer fetches all ~2,789 rows just to build the filter sidebar.
    """
    with engine.connect() as conn:
        total = conn.execute(text("SELECT count(*) FROM performances")).scalar_one()
        genres = conn.execute(text(
            "SELECT genre AS name, count(*) AS count FROM performances "
            "WHERE genre IS NOT NULL AND genre <> '' "
            "GROUP BY genre ORDER BY count DESC, name ASC LIMIT 12"
        )).mappings().all()
        areas = conn.execute(text(
            "SELECT v.province AS name, count(*) AS count "
            "FROM performances p JOIN venues v ON v.id = p.venue_id "
            "WHERE v.province IS NOT NULL AND v.province <> '' "
            "GROUP BY v.province ORDER BY count DESC, name ASC LIMIT 12"
        )).mappings().all()
    return {
        "total": total,
        "genres": [{"name": r["name"], "count": r["count"]} for r in genres],
        "areas": [{"name": r["name"], "count": r["count"]} for r in areas],
    }


@app.get("/performances/upcoming")
def performances_upcoming(
    genre: str | None = Query(default=None),
    area: str | None = Query(default=None),
) -> dict:
    """'오픈 예정' row: performances opening in the next 1-3 days (D-1..D-3),
    honoring the active genre/area filter. Replaces the client-side D-day scan.
    """
    clauses = ["p.status = '공연예정'", "p.start_date BETWEEN :lo AND :hi"]
    params: dict = {"lo": date.today() + timedelta(days=1), "hi": date.today() + timedelta(days=3)}
    if genre:
        clauses.append("p.genre = :genre")
        params["genre"] = genre
    if area:
        clauses.append("v.province = :area")
        params["area"] = area
    sql = f"""
        SELECT p.id, p.kopis_id, p.title, p.poster_url, p.genre, p.status,
               p.start_date, p.end_date, v.name AS venue_name, v.province
        FROM performances p
        JOIN venues v ON v.id = p.venue_id
        WHERE {' AND '.join(clauses)}
        ORDER BY p.start_date ASC, p.id ASC
    """
    with engine.connect() as conn:
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
