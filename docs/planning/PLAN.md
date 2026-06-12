# One-Day Ticket Booking Demo Plan

> **2026-06-12 현행화**: 원래 1일 빌드 계획 문서다. 이후 구현이 진행되며 달라진 사실(실계정 인증, 날짜별 예매, 대기열, KOPIS 실연동 등)을 반영해 수정했고, 아직 실행되지 않은 계획은 "(예정)"으로 남겨두었다. 원본 이력은 git을 참조.

## Goal

Build a Korean-localized working demo slice for ticket booking: users browse performances, save performances, select a mock seat, pay with internal points, and view booking/payment history in My Page.

## Product Scope

Included:
- Korean UI inspired by Interpark NOL Ticket and YES24 Ticket structure, with a distinct theme.
- Performance dashboard and detail pages backed by local KOPIS-shaped data.
- Local account signup/login (bcrypt) and real Google OAuth, with dev login kept as a fallback. (The Kakao-style button was removed in the login redesign.)
- Saved Performances (`관심공연`) backed by Redis.
- Mock seat selection with demo-owned seat maps, seat grades, and different prices.
- Redis Streams-backed asynchronous Booking Request processing.
- Point Payment through synchronous payment-service call from booking-worker.
- My Page with Booking history, Payment History, Point Balance, and Saved Performances.

Excluded:
- Admin page.
- Cancellation and refunds.
- Real settlement.
- Real payment gateway.
- Production OAuth edge cases.
- Complex distributed transactions.
- ~~Full KOPIS ETL~~ → 이후 구현됨: `cron/`의 일일 KOPIS OpenAPI 동기화 배치 (`cron/README.md` 참조).
- Recommendation algorithms.
- KOPIS raw seat text parsing.

## Services

- `frontend`: React Korean-localized UI.
- `auth-service`: dev login, JWT, user profile.
- `event-service`: Performance Metadata, seeded from a real KOPIS dump and kept fresh by the daily KOPIS sync batch (`cron/`, see `cron/README.md`).
- `saved-service`: Redis-backed Saved Performances.
- `booking-service`: Booking API plus Redis Streams worker in separate pods.
- `payment-service`: Point Balance and Payment History.

FastAPI services may duplicate tiny infrastructure helpers such as JWT verification, settings, and DB session setup to avoid shared Python packaging overhead during the one-day build. Domain logic and database schemas remain service-owned.

## Backend Tooling

- Python dependency and command runner: `uv`
- FastAPI server: `uvicorn`
- PostgreSQL access: SQLAlchemy plus psycopg.
- Redis access: `redis-py`.
- Service-to-service HTTP: `httpx`.
- Request/response validation: Pydantic through FastAPI.
- Prototype testing: prioritize smoke checks over broad automated test coverage.

## Frontend Stack

- Vite
- React
- TypeScript
- React Router
- TanStack Query — 설치돼 있으나 미사용. 현재 코드는 자체 fetch 헬퍼(`src/api.ts`)만 쓴다. (도입 검토용으로 의존성 유지)
- simple auth token state
- CSS Modules or plain CSS

## Data Stores

Exact table and Redis structures live in `docs/reference/DB_SCHEMA.md`.

- PostgreSQL runs as one Kubernetes instance with service-owned databases:
  - `auth_db`
  - `event_db`
  - `booking_db`
  - `payment_db`
- Redis stores Saved Performances and carries Booking Requests through Redis Streams.

## Database Migration Approach

- Use plain SQL init files for the Docker Compose prototype.
- 실제 채택된 구조: 서비스별 `sql/` 디렉토리 대신 `infra/docker-compose/postgres/init/`에 통합되었다.
  - `001_create_databases.sql` — auth_db / booking_db / payment_db 생성 (event_db는 POSTGRES_DB 기본값)
  - `005_service_schemas.sql` — 서비스별 테이블 스키마
  - `010_ticketing.sql` — 실제 KOPIS 데이터 덤프 (venues 87건, performances 100건+)
  - `020_fix_event_sequences.sql` — 시퀀스 보정
- auth-service는 기동 시 런타임 `ALTER TABLE` 마이그레이션도 수행한다 (`app/main.py` 시작부).
- Defer Alembic until after the prototype if schema changes become frequent. (예정)

## Event-Service Metadata Schema

Use normalized KOPIS-shaped tables instead of app-level `concert` naming.

### `performances`

- `id`: internal Performance id.
- `kopis_id`: KOPIS `mt20id`, unique.
- `venue_id`: foreign key to `venues.id`.
- `title`: KOPIS `prfnm`.
- `start_date`: KOPIS `prfpdfrom`.
- `end_date`: KOPIS `prfpdto`.
- `poster_url`: KOPIS `poster`.
- `genre`: KOPIS `genrenm`.
- `status`: KOPIS `prfstate`.
- `is_open_run`: normalized from KOPIS `openrun`.
- `cast_text`: KOPIS `prfcast`.
- `runtime`: KOPIS `prfruntime`.
- `age_rating`: KOPIS `prfage`.
- `description`: 상세 설명 텍스트. (계획했던 `price_text`/`guidance_text` 컬럼은 채택되지 않음 — 가격 안내는 event-service 코드에 하드코딩, 관람안내는 `schedule`/`description`으로 대체)
- `schedule`: 공연 시간 안내 텍스트. event-service가 이를 파싱해 날짜별 회차를 계산한다 (`compute_schedules`).
- `intro_image_urls`: KOPIS `styurls` — 파이프(`|`) 구분 TEXT로 저장 (JSON/JSONB 미채택).

### `venues`

- `id`: internal Venue id.
- `kopis_id`: KOPIS `mt10id`, unique.
- `name`: KOPIS `fcltynm`.
- `address`: KOPIS `adres`.
- `province`: KOPIS `sidonm`.
- `district`: KOPIS `gugunnm`.
- `seat_capacity`: KOPIS `seatscale`.
- `phone`: KOPIS `telno`.
- `latitude`: KOPIS latitude.
- `longitude`: KOPIS longitude.
- `halls_text`: KOPIS `halls`, display-only unless later normalized.

KOPIS `sty` is dropped because it is often null and not needed for the demo flow. KOPIS `pcseguidance` and `halls` are not used for booking price or seat inventory. Booking prices and seats come from the demo-owned Mock Seat Map.

## Core User Flow

1. User opens the Korean performance dashboard.
2. User views Performance detail.
3. User logs in with a local account (signup/login) or Google OAuth; demo account chips remain for quick testing.
4. User optionally saves the Performance as `관심공연`.
5. User selects a show date (날짜 선택), then clicks `예매하기`.
6. User enters the seat page — a virtual waiting queue (`/api/queue`, 2초 폴링) gates entry — then selects one or more Seats from the demo-owned Mock Seat Map.
7. User clicks `결제하기`.
8. booking-api creates a Booking Request and appends it to Redis Streams.
9. booking-worker consumes the request, checks seat uniqueness, calls payment-service synchronously, and confirms or fails the Booking.
10. User sees completion or failure.
11. User opens My Page to view Booking history, Payment History, Point Balance, and Saved Performances.

## Minimum API Surface

Exact request and response shapes live in `docs/reference/API_CONTRACTS.md`.

### auth-service

- `POST /auth/dev-login` (폴백용으로 유지)
- `POST /auth/signup`
- `POST /auth/login`
- `GET /auth/google` / `GET /auth/google/callback` (Google OAuth)
- `GET /auth/me`

### event-service

- `GET /performances`
- `GET /performances/{performance_id}`

### saved-service

- `GET /saved/me`
- `POST /saved/performances/{performance_id}`
- `DELETE /saved/performances/{performance_id}`

### booking-service

- `POST /booking-requests`
- `GET /booking-requests/{request_id}`
- `GET /bookings/me`
- `GET /performances/{performance_id}/seat-availability?show_date=` (필수 파라미터; 동일 핸들러의 `/api/...` 별칭 라우트도 존재 — 게이트웨이 regex 재작성과 짝)
- `POST /queue/join` / `GET /queue/status` (가상 대기열)

### payment-service

- `GET /payments/me/balance`
- `GET /payments/me/history`
- `POST /payments/deduct` for internal service use.

## Auth Contract

JWT payload:
- `sub`: user id
- `provider`: `dev`, `local`, or `google` (kakao 라벨은 로그인 개편 때 제거됨)
- `display_name`: display name
- `iat`: issued-at timestamp
- `exp`: expiration timestamp

Request header:
- `Authorization: Bearer <token>`

Dev-login request (폴백용으로 유지 — 실서비스 경로는 signup/login):
- `provider`: `dev`, `local`, or `google`
- `login_id`: demo login identifier, such as `demo-basic` or `demo-rich`
- `display_name`: Korean display name

Rules:
- `auth-service` issues JWTs.
- Protected backend services verify JWT signatures locally with a shared secret.
- Services trust JWT `sub` as `user_id`.
- No refresh token, role model, or admin authorization in the one-day scope.
- Public endpoints are limited to Performance browsing and seat map reads.
- Protected endpoints include Saved Performances, Booking Requests, Bookings, Payments, and `GET /auth/me`.

## Point Payment Rules

- Dev-login creates or uses users with predictable starting balances.
- `demo-basic` starts with `100000` points.
- `demo-rich` starts with `300000` points.
- Mock Seat Grade prices:
  - `VIP`: `150000`
  - `R`: `120000`
  - `S`: `90000`
  - `A`: `60000`
- `payment-service` deducts points only when given a `booking_request_id`.
- `payment-service` prevents duplicate successful deductions for the same `booking_request_id`.
- Payment History is created only when point deduction succeeds.
- Insufficient balance maps to Booking Failure Reason `INSUFFICIENT_POINTS`.
- `POST /payments/deduct` is internal only and requires a simple `X-Service-Token`.
- The frontend never calls `POST /payments/deduct`; it creates Booking Requests instead.

## Mock Seat Map Rules

- Each Performance gets a demo-owned Mock Seat Map generated from fixed rules.
- Seat rows: `A` through `H`.
- Seats per row: `1` through `10`.
- Total seats per Performance: `80`.
- Seat IDs use `{row}-{number}`, for example `A-1`.
- Grade mapping:
  - Rows `A-B`: `VIP`, `150000`
  - Rows `C-D`: `R`, `120000`
  - Rows `E-F`: `S`, `90000`
  - Rows `G-H`: `A`, `60000`
- Booking DB enforces `UNIQUE(performance_id, performance_date, seat_id)` for confirmed Bookings (날짜별 예매 도입으로 3컬럼 복합 유니크).
- `event-service` is authoritative for Seat Grade and price.
- Frontend sends `performance_id`, `seat_id`, and `show_date` when creating a Booking Request, not price. 여러 좌석 선택 시 좌석당 Booking Request를 1건씩 생성한다.
- `booking-worker` reads Performance and Seat data from `event-service` before deducting points and saving the Booking Snapshot.
- Seat definitions are generated by fixed rules, not stored as one row per seat.
- Seat occupancy is remembered by confirmed Bookings in `booking-service`.
- Seat Availability for the UI is returned by `booking-service` by combining generated seat definitions with confirmed Bookings.
- Frontend calls `GET /api/performances/{performance_id}/seat-availability`; gateway routing sends it to `booking-service`.
- Day-one Seat Availability statuses are `AVAILABLE` and `OCCUPIED`.
- No temporary seat hold state is implemented. If two users submit the same available Seat, the database uniqueness rule allows only one Booking to confirm.

## Async Booking Queue

- Redis Stream: `booking.requests`
- Producer: `booking-api`
- Consumer: `booking-worker`
- Consumer group: `booking-workers`
- Message fields include `booking_request_id`, `performance_id`, `seat_id`, `show_date`, and `user_id`.
- Redis Streams is used because the demo needs queue-style asynchronous processing, not a long-lived event streaming platform.
- Strimzi/Kafka is deferred to a later infrastructure-learning track.

Worker behavior:
- Processing takes a `pg_advisory_xact_lock` on (performance, date, seat) and inserts with `ON CONFLICT DO NOTHING` — a double guard consistent with the no-hold design.
- On successful processing, mark the Booking Request `CONFIRMED` and acknowledge the stream message.
- On expected business failure, mark the Booking Request `FAILED` with a Booking Failure Reason and acknowledge the stream message.
- On unexpected exception, mark the Booking Request `FAILED` with `WORKER_ERROR` and acknowledge the stream message.
- Do not implement pending-message recovery in the one-day scope.

## Booking Request State Machine

Statuses:
- `PENDING`: booking-api created the Booking Request and appended it to Redis Streams.
- `PROCESSING`: booking-worker consumed the request.
- `CONFIRMED`: seat uniqueness check and Point Payment succeeded, and a Booking was created.
- `FAILED`: the request could not become a Booking.

Failure reasons:
- `SEAT_ALREADY_BOOKED`
- `INSUFFICIENT_POINTS`
- `PAYMENT_FAILED`
- `WORKER_ERROR`

Frontend behavior:
- After `결제하기`, route to `/booking?ids=<request_id,...>` — 멀티 좌석 예매라 요청 id들을 쿼리스트링으로 복수 전달한다.
- Poll `GET /booking-requests/{request_id}` every 1 second per request until terminal status.
- Show processing, success, or failure Korean copy from the status and failure reason.
- Do not implement cancellation, expiration, refund, or seat hold states in the one-day scope.

## Frontend Page Structure

Korean UI copy and empty/error states live in `docs/reference/UI_COPY.md`.

- `/`: Performance dashboard — 상단 회전 배너, `오픈 예정` 행, 장르/지역 필터 사이드바, `전체 공연` 그리드. (계획했던 `장르별 공연`/`지역별 공연` 섹션 구성은 필터 방식으로 대체됨)
- `/performances/:id`: Performance detail with `상세정보`, `좌석/가격`, and `관람안내` tabs.
- `/performances/:id/seats`: mock seat selection using demo-owned seat maps.
- `/booking?ids=...`: booking request processing and result page (멀티 좌석 결과 통합 표시).
- `/mypage`: Point Balance, Bookings, Payment History, and Saved Performances.

The dashboard does not include `오늘의 추천공연` because recommendation logic is outside the one-day scope.
The UI does not include `랭킹` because ranking logic is outside the one-day scope.

## My Page Scope

Sections:
- `내 정보`: display name and provider label.
- `보유 포인트`: current Point Balance.
- `예매내역`: Booking Snapshot, Seat, Seat Grade, paid amount, and booked time.
- `최근 결제내역`: Point Payment amount, Performance title, status, and paid time.
- `관심공연`: Saved Performance cards resolved from Redis IDs and event-service metadata.

No point charging UI is included in the one-day scope. Demo users start with predictable point balances instead.

## Kubernetes Shape

- `booking-api` and `booking-worker` are separate deployments from the same booking-service codebase.
- Services communicate through Kubernetes service DNS.
- Gateway API(Istio 구현체, ambient mesh)가 `/api/...`를 각 백엔드로 라우팅한다. seat-availability의 regex 경로 재작성은 EnvoyFilter로 처리.
- Add readiness/liveness probes for every backend service.
- Use raw Kubernetes manifests for the first working deployment. (매니페스트는 본 repo가 아니라 GitLab `team6/manifest` repo에 있고, ArgoCD가 동기화한다 — ADR-0004 참조)
- Do not run Strimzi/Kafka in the day-one app path.

## Local Development Path

- Use Docker Compose as the first local integration path before Kubernetes.
- Compose includes frontend, backend services, PostgreSQL, and Redis.
- Keep service configuration based on environment variables so the same services can move from Compose to Kubernetes with minimal code changes.
- Move to Kubernetes only after the local user flow works end to end.

## Prototype Feedback Loop

Docker Compose prototype acceptance checks live in `docs/planning/ACCEPTANCE_CHECKLIST.md`.
Docker Compose run instructions live in `docs/ops/PROTOTYPE_RUNBOOK.md`.

- Build the Docker Compose prototype first.
- Review the clickable Korean UI before starting Kubernetes deployment work.
- Use the prototype review to adjust UI/UX, Korean labels, page density, empty states, and error copy.
- Keep backend contracts stable unless the prototype reveals a missing workflow.
- Start infrastructure work only after the core booking flow works locally:
  - dashboard
  - detail page
  - dev login
  - Saved Performances
  - seat availability
  - Booking Request processing
  - Point Payment
  - My Page history

## Helm Migration Plan (예정 — 미착수)

After the raw manifests are working:
- Convert repeated Deployment, Service, ConfigMap, and Secret patterns into a shared chart structure.
- Keep per-service values in separate `values-*.yaml` files or chart value blocks.
- Preserve separate workloads for `booking-api` and `booking-worker`.
- Move environment-specific settings such as image tags, hostnames, resource requests, and replica counts into values.
- Add Helm only after the raw manifests prove the service wiring, database connections, Redis Streams flow, and Istio routes.
