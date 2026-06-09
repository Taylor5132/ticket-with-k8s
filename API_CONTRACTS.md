# API Contracts

All frontend-facing routes are shown with the `/api` prefix. Gateway routing may send them to different backend services.

## Conventions

- Protected endpoints require `Authorization: Bearer <token>`.
- Timestamps are ISO 8601 strings.
- IDs are strings.
- Error responses use:

```json
{
  "code": "ERROR_CODE",
  "message": "Korean user-facing or developer-readable message"
}
```

## Auth

### `POST /api/auth/dev-login`

Request:

```json
{
  "provider": "kakao",
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
    "provider": "kakao",
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
  "provider": "kakao",
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

## Seat Availability

### `GET /api/performances/{performance_id}/seat-availability`

Response:

```json
{
  "performance_id": "perf-001",
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

## Booking

### `POST /api/booking-requests`

Request:

```json
{
  "performance_id": "perf-001",
  "seat_id": "E-3"
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
