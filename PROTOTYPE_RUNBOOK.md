# Docker Compose Prototype Runbook

Run this on the Ubuntu VM from the repository root.

## Start

```bash
docker compose up --build
```

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
curl http://localhost:8004/performances/1/seat-availability
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
2. Log in with `카카오로 시작하기` for the basic user or `Google로 시작하기` for the rich user.
3. Open a Performance detail page.
4. Save it as `관심공연`.
5. Click `예매하기`.
6. Select an available seat.
7. Click `결제하기`.
8. Wait for Redis Streams booking processing.
9. Open `마이페이지` and check Point Balance, Booking history, Payment History, and Saved Performances.

## Known Prototype Notes

- Event metadata comes from `infra/docker-compose/postgres/init/010_ticketing.sql`.
- The dump has 100 Performances and 87 Venues.
- The event-service maps the dump columns into the frontend API shape.
- Seat definitions are generated from fixed mock rules.
- Seat occupancy is remembered by confirmed Bookings.
- Redis Streams replaces Kafka/Strimzi for the one-day prototype.
- Docker is not available in the current Windows Codex workspace, so Compose should be validated on the Ubuntu VM.
