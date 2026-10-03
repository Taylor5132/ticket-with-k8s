# Booking Ticket Platform (ticket-with-k8s)

> 한국어 공연 예매 데모 플랫폼. 플래시 세일(티켓팅) 트래픽을 견디는 것을 목표로 설계된 MSA 구조다.

A Korean-language performance ticketing demo built as a set of FastAPI microservices and a React frontend. The core design problem is **flash-sale traffic**: booking is not processed synchronously. The booking API only accepts a request, pushes it onto a Redis Stream, and a background worker settles it, so that exactly one user wins a given (performance, date, seat). A Redis-backed waiting room (queue + admission tokens) sits in front of booking. Locally the stack runs with Docker Compose. In production it ran on an on-premises Kubernetes cluster (Istio ambient + Gateway API + Cilium), deployed through GitLab CI and ArgoCD GitOps.

## Features

- **Accounts and login**: ID/password signup and login, a `dev-login` with demo accounts (`demo-basic` 100,000P, `demo-rich` 300,000P), and optional Google OAuth (`GOOGLE_OAUTH_ENABLED`). JWTs are issued by `auth-service`.
- **Performance catalog**: list, facets, upcoming, and detail endpoints served by `event-service` from PostgreSQL. Data is seeded from `infra/docker-compose/postgres/init/010_ticketing.sql` (100 performances, 87 venues) and kept fresh by a daily KOPIS sync batch (`cron/`).
- **Saved performances (관심공연)**: per-user saved list stored in Redis (`saved-service`).
- **Waiting room**: `POST /queue/join` hands out a FIFO ticket (Redis `INCR` + `ZSET`). A dispatcher admits `QUEUE_ADMISSION_RATE` users per second per queue, and an admission worker issues short-lived admission tokens. The token gate is enforced on booking when `ENFORCE_ADMISSION_TOKEN=true`.
- **Async booking**: `POST /booking-requests` records a `PENDING` request and `XADD`s it to a Redis Stream. `booking-worker` consumes it through a consumer group, checks the seat, deducts points through `payment-service`, and marks the request `CONFIRMED` or failed. Clients poll `GET /booking-requests/{id}`.
- **Seat availability** per performance and show date (`show_date` is required everywhere).
- **Point payments**: balance, history, and an internal deduct endpoint (`payment-service`, service-token protected).
- **My page**: point balance, booking history, payment history, and saved performances.
- **Load testing**: k6 scenarios for the full booking flow and KEDA autoscaling, plus a local queue-verification script.

## Tech stack

| Area | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite 5, React Router 6, Vitest + Testing Library. The production image is a static build served by nginx |
| Backend | Python 3.12, FastAPI, Uvicorn, SQLAlchemy 2 + psycopg 3, redis-py, httpx, PyJWT, bcrypt, managed with `uv` |
| Data | PostgreSQL (one instance, one database per service), Redis (cache, Streams booking queue, waiting-room ZSETs, saved items) |
| Observability | OpenTelemetry (OTLP exporter, set via `OTEL_EXPORTER_OTLP_ENDPOINT`), `prometheus-fastapi-instrumentator` |
| Batch | KOPIS OpenAPI daily sync (`cron/`) |
| Local edge | Docker Compose, Caddy reverse proxy, and Cloudflare Tunnel (`tunnel` profile) |
| CI/CD | GitLab CI (SonarQube → build → Trivy → manifest update) → ArgoCD |
| Platform | On-prem Kubernetes: Istio ambient mesh + Gateway API, Cilium, KEDA autoscaling (see ADRs and `docs/ops/`). Redis Streams replaced the original Strimzi/Kafka plan (ADR-0006) |
| Load test | k6 |

## Architecture

```
Users → Cloudflare Tunnel → cloudflared → Istio Gateway (booking-gw) → services
Code push → GitLab CI (build → Trivy → manifest update) → ArgoCD → K8s
```

Request routing (identical in `infra/docker-compose/caddy/Caddyfile` and the Vite dev proxy; the `/api` prefix is stripped):

| Path | Service |
|---|---|
| `/api/performances/{id}/seat-availability` | booking-api (must match before the broader `/api/performances/*` rule) |
| `/api/auth/*` | auth-service |
| `/api/saved/*` | saved-service |
| `/api/payments/*` | payment-service |
| `/api/queue/*`, `/api/booking-requests/*`, `/api/bookings/*` | booking-api |
| `/api/performances/*` | event-service |
| everything else | frontend |

The booking pipeline in `services/booking-service` is one codebase with four entry points:

| Process | Command | Role |
|---|---|---|
| `booking-api` | `uvicorn app.main:app` | Seat availability, booking requests, queue join/status, my bookings |
| `booking-worker` | `python -m app.worker` | Consumes the booking Redis Stream and settles requests |
| `queue-dispatcher` | `python -m app.dispatcher` | Pops users from waiting-room queues at the admission rate |
| `admission-worker` | `python -m app.admission_worker` | Issues admission tokens with a TTL |

Kubernetes manifests are **not** in this repo. They live in a separate GitLab repo (`team6/manifest`) that ArgoCD syncs. CI rewrites image tags there.

## Repository structure

```
apps/frontend/            React + Vite SPA (Dockerfile: node build → nginx on :5173)
services/
  auth-service/           signup/login/dev-login/Google OAuth, JWT issuing
  event-service/          performances, facets, venues (event_db)
  saved-service/          saved performances (Redis)
  booking-service/        booking API + worker + queue dispatcher + admission worker
  payment-service/        point balance, history, deduct
cron/                     KOPIS daily update / expired-performance delete scripts
infra/docker-compose/
  postgres/init/          DB init SQL, the single source of truth for the schema
  caddy/Caddyfile         reverse proxy used by the `tunnel` profile
load-test/                k6 scenarios + verify-queue-local.sh
docs/
  reference/              living specs: API contracts, DB/Redis schema, glossary, UI copy
  ops/                    K8s stack, CI/CD, local runbook, load shedding, quotas, sealed secrets
  planning/               historical plans (annotated with current status)
  adr/                    architecture decision records 0001–0007
  spec/                   Korean functional/API/DB specifications
.gitlab-ci.yml            code-quality → build → scan → update-manifest
AGENTS.md                 maintenance guide for new contributors and AI agents (read this first)
```

## Prerequisites

- Docker with Docker Compose v2.
- **Access to the private Harbor registry at `192.168.0.237`** (self-signed TLS). Every Dockerfile's base image is pulled from it (for example `192.168.0.237/booking_ticket/uv:python3.12-bookworm-slim`), so builds only work where Harbor is reachable and its certificate is trusted or configured as an insecure registry. Outside that network, you'd have to point the `FROM` lines at public images. `cron/Dockerfile` already uses `ghcr.io/astral-sh/uv:python3.12-bookworm-slim`.
- Optional: a KOPIS OpenAPI key for `cron/`, Google OAuth credentials, a Cloudflare Tunnel token, and k6 for load tests.

## Getting started (local, Docker Compose)

```bash
cp .env.example .env          # optional: only needed for OAuth / tunnel settings
docker compose up --build
```

Ports exposed on the host:

| Service | Port |
|---|---|
| frontend | 5173 |
| auth-service | 8001 |
| event-service | 8002 |
| saved-service | 8003 |
| booking-api | 8004 |
| payment-service | 8005 |
| postgres | 5432 (`postgres` / `postgres`) |
| redis | 6379 |

`booking-worker`, `queue-dispatcher`, and `admission-worker` run without published ports. On first start, Postgres runs the init scripts in `infra/docker-compose/postgres/init/`, which create `auth_db`, `booking_db`, and `payment_db` (`event_db` is the container's default database) and load the performance data.

Smoke checks:

```bash
curl http://localhost:8002/health
curl http://localhost:8002/performances
curl "http://localhost:8004/performances/1/seat-availability?show_date=2026-07-01"   # show_date is required (422 without it)
```

Verify the waiting-room pipeline end to end (join → dispatch → admission token → booking accepted; without a token → 403):

```bash
bash load-test/verify-queue-local.sh
```

Expose the stack publicly through Caddy + Cloudflare Tunnel (needs `CLOUDFLARE_TUNNEL_TOKEN` in `.env`):

```bash
docker compose --profile tunnel up --build
```

Reset all local data (Postgres and Redis volumes):

```bash
docker compose down -v
```

Expected UI flow: log in (ID/password or a demo chip) → open a performance → save it → pick a date → `예매하기` → pass the waiting room if one is active → select seats → `결제하기` → wait for the Redis Streams worker → check `마이페이지`. See [docs/ops/PROTOTYPE_RUNBOOK.md](docs/ops/PROTOTYPE_RUNBOOK.md) for details.

> Note: the frontend image is now a static nginx build, and `apps/frontend/nginx.conf` does not proxy `/api`. In the cluster, `/api/*` is routed by the gateway. Locally, API routing comes from Caddy (`tunnel` profile) or the Vite dev server proxy (`npm run dev`), whose targets are Compose service hostnames.

## Configuration

Root `.env` (see `.env.example`), read by `docker-compose.yml`:

| Variable | Purpose |
|---|---|
| `DOMAIN` | Passed to the Caddy container (`tunnel` profile). The current Caddyfile listens on `:80` |
| `CLOUDFLARE_TUNNEL_TOKEN` | Token for the `cloudflared` container (`tunnel` profile) |
| `GOOGLE_OAUTH_ENABLED` | `true` turns on real Google OAuth. With `false`, the Google button falls back to dev-login (demo-rich) |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Google OAuth credentials |
| `GOOGLE_REDIRECT_URI` | Must match the redirect URI registered in Google Cloud (`…/api/auth/google/callback`) |
| `FRONTEND_URL` | Where auth-service redirects after OAuth |

Service environment variables (defaults are in code and in `docker-compose.yml`):

| Variable | Used by | Default / notes |
|---|---|---|
| `DATABASE_URL` | auth, event, booking, payment | `postgresql+psycopg://postgres:postgres@postgres:5432/<service>_db` |
| `REDIS_URL` | saved, booking | `redis://redis:6379/0` |
| `JWT_SECRET` | auth, saved, booking, payment | `dev-secret` (local only; must match across services) |
| `SERVICE_TOKEN` | booking, payment | `dev-service-token`, for service-to-service calls such as point deduction |
| `EVENT_SERVICE_URL` / `PAYMENT_SERVICE_URL` | saved, booking | `http://event-service:8000` / `http://payment-service:8000` |
| `ENFORCE_ADMISSION_TOKEN` | booking-api | `false` in code (cluster default); Compose sets `true` |
| `QUEUE_ADMISSION_RATE` | booking-api, dispatcher | `3` users per second per queue |
| `QUEUE_TTL` | booking-api | `3600` s idle queue expiry |
| `DISPATCHER_TICK_SECONDS` | dispatcher | `1.0` |
| `ADMISSION_TOKEN_TTL` | admission-worker | `600` s |
| `ADMISSION_BATCH`, `ADMISSION_BLOCK_MS`, `ADMISSION_CLAIM_MIN_IDLE_MS`, `ADMISSION_CLAIM_EVERY` | admission-worker | Stream read and pending-claim tuning |
| `CONSUMER_NAME` | worker, admission-worker | Redis Stream consumer name |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | all services | Turns on tracing export when set |
| `VITE_GOOGLE_OAUTH_ENABLED` | frontend | **Build-time** arg (Dockerfile default `true`). It cannot be changed at runtime |
| `DATABASE_URL`, `KOPIS_API_KEY` | `cron/` | See [cron/README.md](cron/README.md) |

## Tests

```bash
# Backend (per service; pyproject defines a `test` extra)
cd services/booking-service
uv sync --extra test
uv run pytest

# Frontend
cd apps/frontend
npm install
npm test                # or: npm run test:coverage
```

CI runs each service's tests with coverage before SonarQube analysis (`.gitlab-ci.yml`).

## Deployment

- **CI** (`.gitlab-ci.yml`): `code-quality` (pytest/vitest + SonarQube quality gate) → `build` (images pushed to Harbor) → `scan` (Trivy, exceptions in `.trivyignore`) → `update-manifest` (rewrites the image tag to `$CI_COMMIT_SHORT_SHA` in the `team6/manifest` repo). Each job runs only when its service's path changed.
- **CD**: ArgoCD syncs the manifest repo to the cluster.
- Cluster design and status: [docs/ops/K8S_STACK.md](docs/ops/K8S_STACK.md), [docs/ops/DEPLOY_STRATEGY.md](docs/ops/DEPLOY_STRATEGY.md), [docs/ops/CICD_PLAN.md](docs/ops/CICD_PLAN.md), [docs/ops/SEALED_SECRETS.md](docs/ops/SEALED_SECRETS.md), [docs/ops/ETCD_ENCRYPTION.md](docs/ops/ETCD_ENCRYPTION.md).
- Load testing: `load-test/k6-test.js` (full flow) and `load-test/k6-keda-test.js`. Results: [docs/ops/SCALING_TEST_2026-06-14.md](docs/ops/SCALING_TEST_2026-06-14.md).

## Documentation index

| Location | Kind | Contents |
|---|---|---|
| [docs/reference/](docs/reference/) | **Living spec**, updated with code | API contracts, DB/Redis schema, domain glossary, UI copy |
| [docs/ops/](docs/ops/) | Infra and operations | K8s stack design/status, CI/CD, local runbook, load shedding, quotas/limits |
| [docs/planning/](docs/planning/) | Historical plans (with status notes) | Initial build plan, infra plan, acceptance checklist |
| [docs/adr/](docs/adr/) | Architecture decision records | ADR-0001 to 0007 |
| [docs/spec/](docs/spec/) | Specifications (Korean) | Functional, API, and DB specs |
| [cron/README.md](cron/README.md) | Batch guide | Running and deploying the KOPIS sync |
| [load-test/](load-test/) | Load tests | k6 scenarios |
| [AGENTS.md](AGENTS.md) | **Maintenance guide for AI and new contributors** | Doc-sync rules and known pitfalls |

## Notes

- Read **[AGENTS.md](AGENTS.md)** before changing anything. It maps which docs must be updated with which code and lists real pitfalls (seat-availability routing, HBONE port 15008 with ambient mesh, `uv run python` in containers, `show_date` everywhere, the `{"detail": {"code", "message"}}` error shape).
- Ticketing invariant: at most one `CONFIRMED` booking per (performance, date, seat).
- `dev-login` accounts start with 100,000P, so VIP seats (150,000P) fail with `INSUFFICIENT_POINTS`. Use `demo-rich` (300,000P) for those.
- Local Compose credentials (`postgres/postgres`, `dev-secret`, `dev-service-token`) are for development only.
- Several internal addresses (Harbor `192.168.0.237`, the GitLab manifest repo, k6 Prometheus endpoints) refer to the original on-prem lab and will not resolve elsewhere.
