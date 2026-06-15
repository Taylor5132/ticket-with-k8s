import pytest
from datetime import date
from unittest.mock import MagicMock
from fastapi.testclient import TestClient


def _setup_connect(mock_engine):
    mock_conn = MagicMock()
    mock_engine.connect.return_value.__enter__.return_value = mock_conn
    return mock_conn


def _setup_begin(mock_engine):
    mock_conn = MagicMock()
    mock_engine.begin.return_value.__enter__.return_value = mock_conn
    return mock_conn


def _perf_row(**kwargs):
    base = {
        "id": 1,
        "kopis_id": "PF001",
        "title": "테스트 공연",
        "poster_url": "http://example.com/poster.jpg",
        "venue_name": "테스트 홀",
        "province": "서울",
        "genre": "뮤지컬",
        "start_date": date(2026, 7, 1),
        "end_date": date(2026, 7, 31),
        "status": "공연중",
    }
    base.update(kwargs)
    return base


def _detail_row(**kwargs):
    base = {
        "id": 1,
        "kopis_id": "PF001",
        "title": "테스트 공연",
        "poster_url": "http://example.com/poster.jpg",
        "genre": "뮤지컬",
        "status": "공연중",
        "start_date": date(2026, 7, 1),
        "end_date": date(2026, 7, 31),
        "is_open_run": "N",
        "cast_text": "홍길동",
        "runtime": "120분",
        "age_rating": "전체관람가",
        "schedule": "금요일(19:30)",
        "description": "공연 설명",
        "intro_image_urls": "http://example.com/img1.jpg|http://example.com/img2.jpg",
        "venue_id": 1,
        "venue_kopis_id": "FC001",
        "venue_name": "테스트 홀",
        "address": "서울시 강남구",
        "province": "서울",
        "district": "강남구",
        "seat_capacity": 500,
        "phone": "02-1234-5678",
        "latitude": 37.5,
        "longitude": 127.0,
        "halls_text": "대극장",
    }
    base.update(kwargs)
    return base


@pytest.fixture
def mock_engine():
    return MagicMock()


@pytest.fixture
def client(mock_engine):
    import app.main as m

    original_engine = m.engine
    m.engine = mock_engine

    with TestClient(m.app) as c:
        yield c

    m.engine = original_engine


# ── /health ───────────────────────────────────────────────

def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ── /performances ─────────────────────────────────────────

def test_performances_empty(client, mock_engine):
    conn = _setup_connect(mock_engine)
    conn.execute.return_value.mappings.return_value.all.return_value = []

    resp = client.get("/performances")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


def test_performances_with_data(client, mock_engine):
    conn = _setup_connect(mock_engine)
    conn.execute.return_value.mappings.return_value.all.return_value = [_perf_row()]

    resp = client.get("/performances")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["title"] == "테스트 공연"
    assert items[0]["area"] == "서울"
    assert items[0]["start_date"] == "2026-07-01"


def test_performances_with_limit(client, mock_engine):
    conn = _setup_connect(mock_engine)
    conn.execute.side_effect = [
        MagicMock(**{"mappings.return_value.all.return_value": [_perf_row()]}),
        MagicMock(**{"scalar_one.return_value": 42}),
    ]

    resp = client.get("/performances?limit=10&offset=0")
    assert resp.status_code == 200
    assert resp.json()["total"] == 42


def test_performances_filter_genre_area_status(client, mock_engine):
    conn = _setup_connect(mock_engine)
    conn.execute.return_value.mappings.return_value.all.return_value = []

    resp = client.get("/performances?genre=뮤지컬&area=서울&status=공연중")
    assert resp.status_code == 200
    assert resp.json()["items"] == []


def test_performances_filter_ids(client, mock_engine):
    conn = _setup_connect(mock_engine)
    conn.execute.return_value.mappings.return_value.all.return_value = [_perf_row()]

    resp = client.get("/performances?ids=1,2,3")
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 1


def test_performances_null_dates(client, mock_engine):
    conn = _setup_connect(mock_engine)
    conn.execute.return_value.mappings.return_value.all.return_value = [
        _perf_row(start_date=None, end_date=None)
    ]

    resp = client.get("/performances")
    assert resp.status_code == 200
    item = resp.json()["items"][0]
    assert item["start_date"] is None
    assert item["end_date"] is None


# ── /performances/facets ──────────────────────────────────

def test_performances_facets(client, mock_engine):
    conn = _setup_connect(mock_engine)
    conn.execute.side_effect = [
        MagicMock(**{"scalar_one.return_value": 100}),
        MagicMock(**{"mappings.return_value.all.return_value": [{"name": "뮤지컬", "count": 50}]}),
        MagicMock(**{"mappings.return_value.all.return_value": [{"name": "서울", "count": 80}]}),
    ]

    resp = client.get("/performances/facets")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 100
    assert data["genres"][0]["name"] == "뮤지컬"
    assert data["genres"][0]["count"] == 50
    assert data["areas"][0]["name"] == "서울"
    assert data["areas"][0]["count"] == 80


def test_performances_facets_empty(client, mock_engine):
    conn = _setup_connect(mock_engine)
    conn.execute.side_effect = [
        MagicMock(**{"scalar_one.return_value": 0}),
        MagicMock(**{"mappings.return_value.all.return_value": []}),
        MagicMock(**{"mappings.return_value.all.return_value": []}),
    ]

    resp = client.get("/performances/facets")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["genres"] == []
    assert data["areas"] == []


# ── /performances/upcoming ────────────────────────────────

def test_performances_upcoming_empty(client, mock_engine):
    conn = _setup_connect(mock_engine)
    conn.execute.return_value.mappings.return_value.all.return_value = []

    resp = client.get("/performances/upcoming")
    assert resp.status_code == 200
    assert resp.json()["items"] == []


def test_performances_upcoming_with_data(client, mock_engine):
    conn = _setup_connect(mock_engine)
    conn.execute.return_value.mappings.return_value.all.return_value = [
        _perf_row(status="공연예정", start_date=date(2026, 6, 16))
    ]

    resp = client.get("/performances/upcoming")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["status"] == "공연예정"


def test_performances_upcoming_with_filters(client, mock_engine):
    conn = _setup_connect(mock_engine)
    conn.execute.return_value.mappings.return_value.all.return_value = []

    resp = client.get("/performances/upcoming?genre=뮤지컬&area=서울")
    assert resp.status_code == 200
    assert resp.json()["items"] == []


# ── /performances/{id} ────────────────────────────────────

def test_performance_detail_not_found(client, mock_engine):
    conn = _setup_begin(mock_engine)
    conn.execute.return_value.mappings.return_value.first.return_value = None

    resp = client.get("/performances/999")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "NOT_FOUND"


def test_performance_detail_found(client, mock_engine):
    conn = _setup_begin(mock_engine)
    conn.execute.return_value.mappings.return_value.first.return_value = _detail_row()

    resp = client.get("/performances/1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "테스트 공연"
    assert data["is_open_run"] is False
    assert data["price_text"] == "VIP석 150,000원, R석 120,000원, S석 90,000원, A석 60,000원"
    assert len(data["intro_image_urls"]) == 2
    assert data["venue"]["province"] == "서울"


def test_performance_detail_null_coords(client, mock_engine):
    conn = _setup_begin(mock_engine)
    conn.execute.return_value.mappings.return_value.first.return_value = _detail_row(
        latitude=None, longitude=None, start_date=None, end_date=None
    )

    resp = client.get("/performances/1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["venue"]["latitude"] is None
    assert data["venue"]["longitude"] is None
    assert data["start_date"] is None
    assert data["schedules"] == []


# ── /internal/performances/{id}/seats/{seat_id} ──────────

@pytest.mark.parametrize("seat_id,grade,price", [
    ("A-1", "VIP", 150000),
    ("B-2", "VIP", 150000),
    ("C-3", "R",   120000),
    ("E-5", "S",   90000),
    ("G-7", "A",   60000),
])
def test_seat_definition_valid(client, seat_id, grade, price):
    resp = client.get(f"/internal/performances/1/seats/{seat_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["grade"] == grade
    assert data["price"] == price


def test_seat_definition_invalid(client):
    resp = client.get("/internal/performances/1/seats/Z-1")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "NOT_FOUND"


# ── 헬퍼 함수 ─────────────────────────────────────────────

def test_schedule_days_empty():
    from app.main import _schedule_days
    assert _schedule_days("") == {5, 6}


def test_schedule_days_single():
    from app.main import _schedule_days
    assert _schedule_days("금요일(19:30)") == {4}


def test_schedule_days_range():
    from app.main import _schedule_days
    assert _schedule_days("토요일 ~ 일요일(14:00)") == {5, 6}


def test_schedule_days_multiple():
    from app.main import _schedule_days
    result = _schedule_days("화요일 ~ 금요일(19:30), 토요일 ~ 일요일(15:00)")
    assert result == {1, 2, 3, 4, 5, 6}


def test_compute_schedules_no_dates():
    from app.main import compute_schedules
    assert compute_schedules(None, None, "") == []


def test_compute_schedules_with_dates():
    from app.main import compute_schedules
    result = compute_schedules(date(2026, 6, 15), date(2026, 6, 21), "월요일(19:30)")
    assert "2026-06-15" in result


def test_list_intro_images_none():
    from app.main import list_intro_images
    assert list_intro_images(None) == []


def test_list_intro_images_pipe():
    from app.main import list_intro_images
    result = list_intro_images("a.jpg|b.jpg|c.jpg")
    assert result == ["a.jpg", "b.jpg", "c.jpg"]
