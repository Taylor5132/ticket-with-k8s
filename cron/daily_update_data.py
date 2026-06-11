"""
KOPIS 공연 정보를 매일 event_db에 동기화하는 스크립트.

환경변수:
  DATABASE_URL  - PostgreSQL 접속 URL
  KOPIS_API_KEY - KOPIS OpenAPI 서비스 키 (기본값: 개발용 키)

수집 범위: 오늘 -30일 (현재 공연 포함) ~ 오늘 +365일 (예정 공연)
전략: kopis_id UNIQUE 제약을 이용해 INSERT ... ON CONFLICT DO UPDATE (upsert)
"""
import os
import time
import requests
import xml.etree.ElementTree as ET
import psycopg
from datetime import date, datetime, timedelta

API_KEY  = os.environ["KOPIS_API_KEY"]
BASE_URL = "http://www.kopis.or.kr/openApi/restful"
DB_URL   = os.environ["DATABASE_URL"]


def _conn_str(url: str) -> str:
    # SQLAlchemy prefix 제거 (postgresql+psycopg:// → postgresql://)
    return url.replace("postgresql+psycopg://", "postgresql://")


def get(url: str, params: dict, retries: int = 3):
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, timeout=15)
            r.raise_for_status()
            return r
        except Exception as exc:
            if attempt == retries - 1:
                print(f"[WARN] GET {url} → {exc}")
                return None
            time.sleep(1)


def parse_element(element) -> dict:
    return {child.tag: (child.text or "").strip() for child in element}


def parse_date(s: str) -> date | None:
    if not s:
        return None
    try:
        return datetime.strptime(s.replace(".", "-").strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


# ─── KOPIS 수집 ──────────────────────────────────────────────────────────────

def fetch_performance_list(stdate: date, eddate: date) -> list[dict]:
    """공연 목록을 31일 단위 윈도우로 페이지네이션해서 수집."""
    performances, seen = [], set()
    cur = stdate
    while cur <= eddate:
        win_end = min(cur + timedelta(days=30), eddate)
        s, e = cur.strftime("%Y%m%d"), win_end.strftime("%Y%m%d")
        for page in range(1, 1000):
            resp = get(f"{BASE_URL}/pblprfr", {
                "service": API_KEY, "stdate": s, "eddate": e,
                "cpage": page, "rows": 100,
            })
            if resp is None:
                break
            items = ET.fromstring(resp.content.decode("utf-8")).findall(".//db")
            for item in items:
                d = parse_element(item)
                mid = d.get("mt20id", "")
                if mid and mid not in seen:
                    seen.add(mid)
                    performances.append(d)
            if len(items) < 100:
                break
            time.sleep(0.2)
        print(f"  {s}~{e}: 누적 {len(performances)}건")
        cur = win_end + timedelta(days=1)
        time.sleep(0.3)
    return performances


def fetch_detail(mt20id: str) -> dict | None:
    resp = get(f"{BASE_URL}/pblprfr/{mt20id}", {"service": API_KEY})
    if resp is None:
        return None
    item = ET.fromstring(resp.content.decode("utf-8")).find(".//db")
    if item is None:
        return None
    d = parse_element(item)
    d["styurls"] = "|".join(
        img.text.strip() for img in item.findall(".//styurl") if img.text
    )
    return d


def fetch_venue_detail(mt10id: str) -> dict | None:
    resp = get(f"{BASE_URL}/prfplc/{mt10id}", {"service": API_KEY})
    if resp is None:
        return None
    item = ET.fromstring(resp.content.decode("utf-8")).find(".//db")
    if item is None:
        return None
    d = parse_element(item)
    d["halls"] = "|".join(
        f"{mt13.findtext('mt13nm', '').strip()}:{mt13.findtext('seatscale', '').strip()}"
        for mt13 in item.findall(".//mt13s")
    )
    return d


# ─── DB upsert ───────────────────────────────────────────────────────────────

_VENUE_UPSERT = """
    INSERT INTO venues (kopis_id, name, address, province, district,
        seat_capacity, phone, latitude, longitude, halls_text)
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    ON CONFLICT (kopis_id) DO UPDATE SET
        name          = EXCLUDED.name,
        address       = EXCLUDED.address,
        province      = EXCLUDED.province,
        district      = EXCLUDED.district,
        seat_capacity = EXCLUDED.seat_capacity,
        phone         = EXCLUDED.phone,
        latitude      = EXCLUDED.latitude,
        longitude     = EXCLUDED.longitude,
        halls_text    = EXCLUDED.halls_text
    RETURNING id
"""

_PERF_UPSERT = """
    INSERT INTO performances (
        kopis_id, venue_id, title, start_date, end_date,
        poster_url, genre, status, is_open_run, cast_text,
        runtime, age_rating, description, intro_image_urls, schedule
    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    ON CONFLICT (kopis_id) DO UPDATE SET
        venue_id         = EXCLUDED.venue_id,
        title            = EXCLUDED.title,
        start_date       = EXCLUDED.start_date,
        end_date         = EXCLUDED.end_date,
        poster_url       = EXCLUDED.poster_url,
        genre            = EXCLUDED.genre,
        status           = EXCLUDED.status,
        is_open_run      = EXCLUDED.is_open_run,
        cast_text        = EXCLUDED.cast_text,
        runtime          = EXCLUDED.runtime,
        age_rating       = EXCLUDED.age_rating,
        description      = EXCLUDED.description,
        intro_image_urls = EXCLUDED.intro_image_urls,
        schedule         = EXCLUDED.schedule
"""


def _upsert_venue(cur, mt10id: str, vd: dict) -> int | None:
    seat = vd.get("seatscale") or None
    if seat:
        try:
            seat = int(str(seat).replace(",", "").strip())
        except ValueError:
            seat = None
    cur.execute(_VENUE_UPSERT, (
        mt10id,
        vd.get("fcltynm", ""),
        vd.get("adres", ""),
        vd.get("sidonm", ""),
        vd.get("gugunnm", ""),
        seat,
        vd.get("telno", ""),
        vd.get("la") or None,
        vd.get("lo") or None,
        vd.get("halls", ""),
    ))
    row = cur.fetchone()
    return row[0] if row else None


# ─── 메인 ────────────────────────────────────────────────────────────────────

def main():
    today      = date.today()
    sync_start = today
    sync_end   = today + timedelta(days=365)  # 향후 1년

    print(f"[kopis-sync] 시작: {today}")
    print(f"수집 범위: {sync_start} ~ {sync_end}\n")

    print("[1/3] 공연 목록 수집...")
    performances = fetch_performance_list(sync_start, sync_end)
    print(f"→ 총 {len(performances)}건\n")

    cnt_perf = cnt_venue = cnt_err = 0

    with psycopg.connect(_conn_str(DB_URL)) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT kopis_id, id FROM venues")
            venue_map: dict[str, int] = {r[0]: r[1] for r in cur.fetchall()}

        print(f"[2/3] 상세 수집 및 DB upsert ({len(performances)}건)...")
        for i, p in enumerate(performances, 1):
            mt20id = p.get("mt20id", "")
            if not mt20id:
                continue

            detail = fetch_detail(mt20id) or {}
            mt10id = detail.get("mt10id", "")

            # 새 공연장이면 API 조회 후 insert
            if mt10id and mt10id not in venue_map:
                vd = fetch_venue_detail(mt10id)
                if vd:
                    try:
                        with conn.cursor() as cur:
                            vid = _upsert_venue(cur, mt10id, vd)
                        conn.commit()
                        if vid:
                            venue_map[mt10id] = vid
                            cnt_venue += 1
                    except Exception as exc:
                        print(f"  [venue 오류] {mt10id}: {exc}")
                        conn.rollback()

            venue_id = venue_map.get(mt10id)

            try:
                with conn.cursor() as cur:
                    cur.execute(_PERF_UPSERT, (
                        mt20id,
                        venue_id,
                        p.get("prfnm") or detail.get("prfnm", ""),
                        parse_date(p.get("prfpdfrom") or detail.get("prfpdfrom")),
                        parse_date(p.get("prfpdto") or detail.get("prfpdto")),
                        p.get("poster") or detail.get("poster", ""),
                        p.get("genrenm") or detail.get("genrenm", ""),
                        p.get("prfstate") or detail.get("prfstate", ""),
                        p.get("openrun") or detail.get("openrun", ""),
                        detail.get("prfcast", ""),
                        detail.get("prfruntime", ""),
                        detail.get("prfage", ""),
                        detail.get("sty", ""),
                        detail.get("styurls", ""),
                        detail.get("dtguidance", ""),
                    ))
                conn.commit()
                cnt_perf += 1
            except Exception as exc:
                print(f"  [perf 오류] {mt20id}: {exc}")
                conn.rollback()
                cnt_err += 1

            if i % 50 == 0:
                print(f"  {i}/{len(performances)} 처리 완료")

            time.sleep(0.15)

    print(f"\n[3/3] 완료")
    print(f"  공연 upsert  : {cnt_perf}건")
    print(f"  공연장 upsert: {cnt_venue}건")
    print(f"  오류         : {cnt_err}건")


if __name__ == "__main__":
    main()
