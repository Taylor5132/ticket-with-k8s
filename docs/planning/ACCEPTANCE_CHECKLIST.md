# Docker Compose Prototype Acceptance Checklist

> **2026-06-12 현행화**: 이 게이트는 통과 완료된 역사적 문서다 — 현재 시스템은 K8s 클러스터(frontend/backend/db NS, ArgoCD GitOps)에서 운영 중이다. "Not Required" 항목 중 일부(Google OAuth, KOPIS 실연동, K8s 매니페스트)는 이후 구현되었다.

The first prototype runs with Docker Compose on an Ubuntu VM. Kubernetes work starts only after this checklist passes.

## Runtime

- `docker compose up --build` starts all application services.
- Frontend is reachable from the VM/browser.
- PostgreSQL container starts and creates service-owned databases.
- Redis container starts and supports both Sets and Streams.
- Backend services expose health endpoints.
- `booking-worker` starts and joins the Redis Streams consumer group.

## Seed Data

- Event DB contains at least 12 KOPIS-shaped Performances.
- Every Performance is linked to a Venue.
- Dashboard shows poster, title, venue, area, genre, and date range.
- At least one Performance has guidance text or intro images for the detail page.

## Auth

- User can log in as `demo-basic`.
- User can log in as `demo-rich`.
- Frontend stores and sends JWT for protected endpoints.
- Protected endpoints reject missing or invalid JWTs.

## Saved Performances

- User can save a Performance as `관심공연`.
- User can remove a Saved Performance.
- My Page shows Saved Performances from Redis.
- Empty Saved Performances state appears for a new user.

## Seat Selection

- Seat map renders 80 seats.
- Seat grades and prices match the fixed rules.
- Occupied seats are disabled or visibly unavailable.
- User cannot click `결제하기` without selecting a seat.

## Booking And Payment

- `demo-basic` can successfully book an `S` or `A` seat.
- `demo-basic` fails with `INSUFFICIENT_POINTS` for a `VIP` or `R` seat.
- `demo-rich` can successfully book a `VIP` seat.
- Two booking attempts for the same Performance and Seat result in one success and one `SEAT_ALREADY_BOOKED`.
- Successful booking deducts points exactly once.
- Duplicate payment deduction for the same Booking Request does not deduct points twice.
- Booking Request reaches a terminal state: `CONFIRMED` or `FAILED`.

## My Page

- My Page shows user display name and provider label.
- My Page shows current Point Balance.
- My Page shows Booking history after success.
- My Page shows Payment History after success.
- Empty booking/payment states appear before first booking.

## UI Review Gate

- Korean labels render correctly in the browser.
- Main flow is understandable without developer explanation.
- Booking processing page clearly shows loading, success, and failure states.
- UI/UX issues found in prototype review are triaged before Kubernetes work starts.

## Not Required For Prototype

- Admin page.
- Cancellation or refund.
- Real Kakao/Google OAuth. → **Google OAuth는 이후 구현됨** (auth-service `/auth/google`; Kakao는 여전히 미구현)
- Point charging UI.
- Real payment gateway.
- KOPIS live API ingestion. → **이후 구현됨** (`cron/` 일일 동기화)
- Kubernetes manifests. → **이후 구현됨** (별도 repo `team6/manifest`, ArgoCD 동기화)
