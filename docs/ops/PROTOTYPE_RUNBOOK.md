# Docker Compose Prototype Runbook

> **2026-06-12 현행화**: 이 문서는 **로컬 개발 경로** 전용이다. 실제 배포는 K8s 클러스터(ArgoCD GitOps)에서 운영 중 — `docs/ops/K8S_STACK.md` 참조.

Run this on the Ubuntu VM from the repository root.

## Start

```bash
docker compose up --build
```

⚠ 모든 Dockerfile의 베이스 이미지가 사설 Harbor(`192.168.0.237`, self-signed)를 가리키므로, Harbor에 접근 가능하고 인증서를 신뢰(또는 insecure-registry 설정)하는 환경에서만 빌드된다.

Frontend:

```text
http://<vm-ip>:5173
```

Useful service ports:

```text
auth-service     8001
event-service    8002
saved-service    8003
booking-api      8004
payment-service  8005
postgres         5432
redis            6379
```

## First Checks

```bash
curl http://localhost:8002/health
curl http://localhost:8002/performances
curl "http://localhost:8004/performances/1/seat-availability?show_date=2026-07-01"  # show_date 필수 (없으면 422)
```

## Reset Data

This deletes local prototype state, including imported Postgres data and Redis data:

```bash
docker compose down -v
```

Then start again:

```bash
docker compose up --build
```

## Expected Prototype Flow

1. Open the frontend.
2. Log in — 아이디/비밀번호 로그인·회원가입, 또는 데모 칩 `demo-basic`(100,000P) / `demo-rich`(300,000P). (`카카오로 시작하기` 버튼은 로그인 개편 때 제거됨; `Google로 시작하기`는 OAuth 비활성 시 demo-rich 폴백)
3. Open a Performance detail page.
4. Save it as `관심공연`.
5. 날짜 선택 후 click `예매하기` (날짜 미선택 시 버튼 비활성).
6. (대기열이 있으면 입장 대기 화면을 거친 뒤) Select one or more available seats.
7. Click `결제하기`.
8. Wait for Redis Streams booking processing.
9. Open `마이페이지` and check Point Balance, Booking history, Payment History, and Saved Performances.

## Known Prototype Notes

- Event metadata comes from `infra/docker-compose/postgres/init/010_ticketing.sql`.
- The dump has 100 Performances and 87 Venues.
- The event-service maps the dump columns into the frontend API shape.
- Seat definitions are generated from fixed mock rules.
- Seat occupancy is remembered by confirmed Bookings.
- Redis Streams replaces Kafka/Strimzi — 프로토타입 한정이 아니라 클러스터 운영에서도 동일 메커니즘이다.
- Compose에는 `tunnel` 프로파일(caddy + cloudflared)도 있다: `docker compose --profile tunnel up`.
- (역사적 메모) Docker is not available in the current Windows Codex workspace, so Compose should be validated on the Ubuntu VM. — 당시 작성 환경 기준이며 현재는 무관.
