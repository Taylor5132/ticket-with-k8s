# API Contracts

> **2026-06-12 현행화**: 실제 서비스 코드와 대조해 수정함. 에러 응답 구조 정정, 인증 API 추가(signup/login/Google), 날짜별 예매(show_date) 반영, 대기열 API 추가.

All frontend-facing routes are shown with the `/api` prefix. Gateway routing may send them to different backend services.

## Conventions

- Protected endpoints require `Authorization: Bearer <token>`.
- Timestamps are ISO 8601 strings.
- IDs are strings.
- Error responses use FastAPI's `detail` envelope (평면 구조가 아님 — 실코드 기준):

```json
{
  "detail": {
    "code": "ERROR_CODE",
    "message": "Korean user-facing or developer-readable message"
  }
}
```

## Auth

### `POST /api/auth/signup`

Request:

```json
{
  "login_id": "myid",
  "password": "********",
  "display_name": "닉네임"
}
```

Response (`provider`는 `local`, 가입 즉시 100,000P 지급):

```json
{
  "access_token": "jwt",
  "token_type": "bearer",
  "user": { "id": "user-...", "provider": "local", "login_id": "myid", "display_name": "닉네임" }
}
```

### `POST /api/auth/login`

Request: `{ "login_id": "myid", "password": "********" }` — Response는 signup과 동일 형태.

### `GET /api/auth/google` / `GET /api/auth/google/callback`

Google OAuth 리다이렉트 플로우 (state 쿠키 + 토큰 교환). `GOOGLE_OAUTH_ENABLED=false`면 프론트가 dev-login 폴백 사용.

### `POST /api/auth/dev-login` (폴백용으로 유지)

Request:

```json
{
  "provider": "dev",
  "login_id": "demo-basic",
  "display_name": "데모 사용자"
}
```

Response:

```json
{
  "access_token": "jwt",
  "token_type": "bearer",
  "user": {
    "id": "user-demo-basic",
    "provider": "dev",
    "login_id": "demo-basic",
    "display_name": "데모 사용자"
  }
}
```

### `GET /api/auth/me`

Response:

```json
{
  "id": "user-demo-basic",
  "provider": "dev",
  "login_id": "demo-basic",
  "display_name": "데모 사용자"
}
```

## Performances

### `GET /api/performances`

Query parameters:

- `genre`: optional
- `area`: optional
- `status`: optional

Response:

```json
{
  "items": [
    {
      "id": "perf-001",
      "kopis_id": "PF000001",
      "title": "오페라의 유령",
      "poster_url": "https://example.com/poster.jpg",
      "venue_name": "블루스퀘어",
      "area": "서울",
      "genre": "뮤지컬",
      "start_date": "2026-07-01",
      "end_date": "2026-08-31",
      "status": "공연예정"
    }
  ]
}
```

### `GET /api/performances/{performance_id}`

Response:

```json
{
  "id": "perf-001",
  "kopis_id": "PF000001",
  "title": "오페라의 유령",
  "poster_url": "https://example.com/poster.jpg",
  "genre": "뮤지컬",
  "status": "공연예정",
  "start_date": "2026-07-01",
  "end_date": "2026-08-31",
  "is_open_run": false,
  "cast_text": "홍길동, 김영희",
  "runtime": "150분",
  "age_rating": "8세 이상",
  "price_text": "VIP석 150,000원, R석 120,000원",
  "guidance_text": "공연 시작 후 입장이 제한될 수 있습니다.",
  "intro_image_urls": [
    "https://example.com/detail-1.jpg"
  ],
  "schedules": [
    { "date": "2026-07-01", "times": ["19:30"] }
  ],
  "venue": {
    "id": "venue-001",
    "kopis_id": "FC000001",
    "name": "블루스퀘어",
    "address": "서울특별시 용산구 ...",
    "province": "서울",
    "district": "용산구",
    "seat_capacity": 1000,
    "phone": "02-0000-0000",
    "latitude": 37.0,
    "longitude": 127.0,
    "halls_text": "신한카드홀:1000석"
  }
}
```

비고: `price_text`는 DB 컬럼이 아니라 event-service 코드에서 하드코딩된 등급 가격표이고, `guidance_text`는 `schedule`/`description` 컬럼에서 유도된다. `schedules`는 날짜별 회차 배열 (`compute_schedules`가 공연 기간 + 시간 안내 텍스트를 파싱해 생성 — 날짜 선택 UI의 데이터원).

## Seat Availability

### `GET /api/performances/{performance_id}/seat-availability?show_date=YYYY-MM-DD`

Query parameters:

- `show_date`: **필수**. 좌석 점유는 날짜별로 계산된다.

Response:

```json
{
  "performance_id": "perf-001",
  "show_date": "2026-07-01",
  "seats": [
    {
      "seat_id": "A-1",
      "row": "A",
      "number": 1,
      "grade": "VIP",
      "price": 150000,
      "status": "AVAILABLE"
    },
    {
      "seat_id": "A-2",
      "row": "A",
      "number": 2,
      "grade": "VIP",
      "price": 150000,
      "status": "OCCUPIED"
    }
  ]
}
```

## Saved Performances

### `GET /api/saved/me`

Response:

```json
{
  "items": [
    {
      "id": "perf-001",
      "title": "오페라의 유령",
      "poster_url": "https://example.com/poster.jpg",
      "venue_name": "블루스퀘어",
      "area": "서울",
      "genre": "뮤지컬",
      "start_date": "2026-07-01",
      "end_date": "2026-08-31"
    }
  ]
}
```

### `POST /api/saved/performances/{performance_id}`

Response:

```json
{
  "performance_id": "perf-001",
  "saved": true
}
```

### `DELETE /api/saved/performances/{performance_id}`

Response:

```json
{
  "performance_id": "perf-001",
  "saved": false
}
```

## Queue (가상 대기열)

### `POST /api/queue/join?performance_id=&show_date=`

Response:

```json
{ "position": 5, "total": 12 }
```

### `GET /api/queue/status?performance_id=&show_date=`

Response (입장 허가 전 / 후):

```json
{ "admitted": false, "position": 3, "total": 12 }
```

```json
{ "admitted": true, "position": 0, "total": 0 }
```

비고: Redis ZSET 기반. `QUEUE_ADMISSION_RATE`(기본 3명/초)에 따라 선두부터 입장 처리된다. 프론트는 2초 간격 폴링.

## Booking

### `POST /api/booking-requests`

Request (`show_date` 필수 — 날짜별 예매; 멀티 좌석 선택 시 좌석당 1건씩 호출):

```json
{
  "performance_id": "perf-001",
  "seat_id": "E-3",
  "show_date": "2026-07-01"
}
```

Response:

```json
{
  "request_id": "br-001",
  "status": "PENDING"
}
```

### `GET /api/booking-requests/{request_id}`

Response:

```json
{
  "request_id": "br-001",
  "status": "CONFIRMED",
  "failure_reason": null,
  "booking_id": "booking-001"
}
```

Failed response example:

```json
{
  "request_id": "br-001",
  "status": "FAILED",
  "failure_reason": "SEAT_ALREADY_BOOKED",
  "booking_id": null
}
```

### `GET /api/bookings/me`

Response:

```json
{
  "items": [
    {
      "id": "booking-001",
      "performance_id": "perf-001",
      "performance_title": "오페라의 유령",
      "venue_name": "블루스퀘어",
      "performance_date": "2026-07-01",
      "seat_id": "E-3",
      "seat_grade": "S",
      "paid_amount": 90000,
      "booked_at": "2026-06-09T12:00:00Z"
    }
  ]
}
```

## Payments

### `GET /api/payments/me/balance`

Response:

```json
{
  "balance": 100000
}
```

### `GET /api/payments/me/history`

Response:

```json
{
  "items": [
    {
      "id": "pay-001",
      "booking_request_id": "br-001",
      "booking_id": "booking-001",
      "performance_title": "오페라의 유령",
      "amount": 90000,
      "status": "PAID",
      "paid_at": "2026-06-09T12:00:00Z"
    }
  ]
}
```

### Internal `POST /payments/deduct`

Headers:

- `X-Service-Token: <service-token>`

Request:

```json
{
  "user_id": "user-demo-basic",
  "booking_request_id": "br-001",
  "booking_id": "booking-001",
  "amount": 90000,
  "performance_title": "오페라의 유령"
}
```

Response:

```json
{
  "payment_id": "pay-001",
  "balance_after": 10000
}
```
