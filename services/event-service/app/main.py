import os

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
        LIMIT 100
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
