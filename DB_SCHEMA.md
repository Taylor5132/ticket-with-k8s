# Database Schema

PostgreSQL runs as one instance with separate service-owned databases. Services must not query another service's database directly.

## `auth_db`

### `users`

```sql
CREATE TABLE users (
  id TEXT PRIMARY KEY,
  provider TEXT NOT NULL,
  login_id TEXT NOT NULL,
  display_name TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (provider, login_id)
);
```

## `event_db`

The prototype imports `infra/docker-compose/postgres/init/010_ticketing.sql`, copied from the provided `ticketing.sql` dump. The event-service adapts this dump shape into the frontend API response shape.

### `venues`

```sql
CREATE TABLE venues (
  id INTEGER PRIMARY KEY,
  kopis_id VARCHAR(20) UNIQUE,
  name VARCHAR(255),
  address TEXT,
  province VARCHAR(50),
  district VARCHAR(50),
  seat_capacity INTEGER,
  phone VARCHAR(20),
  latitude NUMERIC(18,14),
  longitude NUMERIC(18,14),
  halls_text TEXT
);
```

### `performances`

```sql
CREATE TABLE performances (
  id INTEGER PRIMARY KEY,
  kopis_id VARCHAR(20) UNIQUE,
  venue_id INTEGER REFERENCES venues(id),
  title VARCHAR(500),
  start_date DATE,
  end_date DATE,
  poster_url TEXT,
  genre VARCHAR(100),
  status VARCHAR(20),
  is_open_run CHAR(1),
  cast_text TEXT,
  runtime VARCHAR(50),
  age_rating VARCHAR(50),
  description TEXT,
  intro_image_urls TEXT,
  schedule TEXT
);
```

Suggested indexes:

```sql
CREATE INDEX idx_performances_genre ON performances(genre);
CREATE INDEX idx_performances_status ON performances(status);
CREATE INDEX idx_performances_start_date ON performances(start_date);
CREATE INDEX idx_venues_province ON venues(province);
```

The dump currently does not include `price_text` or `guidance_text` columns. The API derives `price_text` from the mock seat price rules and maps `schedule` or `description` into `guidance_text`.

## `booking_db`

### `booking_requests`

```sql
CREATE TABLE booking_requests (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  performance_id TEXT NOT NULL,
  seat_id TEXT NOT NULL,
  status TEXT NOT NULL,
  failure_reason TEXT,
  booking_id TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Allowed `status` values:

- `PENDING`
- `PROCESSING`
- `CONFIRMED`
- `FAILED`

Allowed `failure_reason` values:

- `SEAT_ALREADY_BOOKED`
- `INSUFFICIENT_POINTS`
- `PAYMENT_FAILED`
- `WORKER_ERROR`

### `bookings`

```sql
CREATE TABLE bookings (
  id TEXT PRIMARY KEY,
  booking_request_id TEXT NOT NULL UNIQUE REFERENCES booking_requests(id),
  user_id TEXT NOT NULL,
  performance_id TEXT NOT NULL,
  performance_title TEXT NOT NULL,
  venue_name TEXT NOT NULL,
  performance_date DATE NOT NULL,
  seat_id TEXT NOT NULL,
  seat_grade TEXT NOT NULL,
  paid_amount INTEGER NOT NULL,
  booked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (performance_id, seat_id)
);
```

Suggested indexes:

```sql
CREATE INDEX idx_booking_requests_user_id ON booking_requests(user_id);
CREATE INDEX idx_booking_requests_status ON booking_requests(status);
CREATE INDEX idx_bookings_user_id ON bookings(user_id);
CREATE INDEX idx_bookings_performance_id ON bookings(performance_id);
```

## `payment_db`

### `point_balances`

```sql
CREATE TABLE point_balances (
  user_id TEXT PRIMARY KEY,
  balance INTEGER NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### `payment_history`

```sql
CREATE TABLE payment_history (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  booking_request_id TEXT NOT NULL UNIQUE,
  booking_id TEXT,
  performance_title TEXT NOT NULL,
  amount INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'PAID',
  paid_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Suggested indexes:

```sql
CREATE INDEX idx_payment_history_user_id ON payment_history(user_id);
CREATE INDEX idx_payment_history_paid_at ON payment_history(paid_at);
```

## Redis

Redis is owned by the application infrastructure but used by service-specific key spaces.

### Saved Performances

Key:

```text
saved:user:{user_id}
```

Type:

```text
Set
```

Members:

```text
performance_id
```

No TTL for the one-day demo.

### Booking Requests Stream

Stream:

```text
booking.requests
```

Consumer group:

```text
booking-workers
```

Message fields:

```text
booking_request_id
performance_id
seat_id
user_id
```
