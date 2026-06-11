# KOPIS 공연 데이터 동기화 CronJob

KOPIS OpenAPI에서 공연 정보를 매일 `event_db`에 동기화하는 스크립트 모음입니다.

## 파일 구조

```
cron/
├── daily_update_data.py   # KOPIS API → DB 동기화
├── daily_delete_data.py   # 만료 공연 삭제
├── pyproject.toml         # Python 의존성
└── Dockerfile             # 컨테이너 이미지 빌드
```

---

## 스크립트 설명

### daily_update_data.py

KOPIS OpenAPI에서 공연 정보를 수집해 `event_db`에 upsert합니다.

**수집 범위**: 오늘 ~ 오늘 +365일

**동작 순서**
1. 공연 목록 수집 (31일 단위 윈도우로 페이지네이션)
2. 공연별 상세 정보 조회 (출연진, 런타임, 소개 이미지 등)
3. 새 공연장(`venues`) 발견 시 API 조회 후 insert
4. `kopis_id` UNIQUE 제약 기반 upsert — 기존 데이터는 UPDATE, 신규 데이터는 INSERT

**연동 테이블**

| 테이블 | 주요 컬럼 |
|---|---|
| `venues` | kopis_id, name, address, province, district, seat_capacity, phone, latitude, longitude |
| `performances` | kopis_id, venue_id, title, start_date, end_date, poster_url, genre, status, is_open_run, cast_text, runtime, age_rating, description, intro_image_urls, schedule |

**KOPIS API 엔드포인트**

| 용도 | 엔드포인트 |
|---|---|
| 공연 목록 | `GET /pblprfr?service=&stdate=&eddate=&cpage=&rows=` |
| 공연 상세 | `GET /pblprfr/{mt20id}?service=` |
| 공연장 상세 | `GET /prfplc/{mt10id}?service=` |

---

### daily_delete_data.py

`end_date`가 오늘 이전인 공연을 `performances` 테이블에서 삭제합니다.

```sql
DELETE FROM performances WHERE end_date < 오늘
```

---

## 환경변수

| 변수명 | 설명 | 예시 |
|---|---|---|
| `DATABASE_URL` | PostgreSQL 접속 URL | `postgresql://postgres:postgres@postgres:5432/event_db` |
| `KOPIS_API_KEY` | KOPIS OpenAPI 서비스 키 | `0f4460e0934c4fd19f5dbb034c66bafa` |

---

## 로컬 실행

```bash
pip install requests "psycopg[binary]"

# 동기화
DATABASE_URL=postgresql://postgres:비밀번호@localhost:5432/event_db \
KOPIS_API_KEY=발급받은키 \
python daily_update_data.py

# 삭제
DATABASE_URL=postgresql://postgres:비밀번호@localhost:5432/event_db \
python daily_delete_data.py
```

---

## Docker 이미지 빌드

```bash
docker build -t 192.168.0.237/booking_ticket/kopis-sync:latest .
docker push 192.168.0.237/booking_ticket/kopis-sync:latest
```

---

## Kubernetes 배포 계획

동일 이미지를 사용하는 CronJob 2개로 구성합니다.

| CronJob | 스케줄 | 실행 명령 |
|---|---|---|
| `kopis-daily-update` | `0 3 * * *` (매일 새벽 3시) | `python daily_update_data.py` |
| `kopis-daily-delete` | `0 4 * * *` (매일 새벽 4시) | `python daily_delete_data.py` |

- `DATABASE_URL`, `KOPIS_API_KEY`는 K8s Secret으로 주입
- Namespace: `booking`
- Image: `192.168.0.237/booking_ticket/kopis-sync:latest`
