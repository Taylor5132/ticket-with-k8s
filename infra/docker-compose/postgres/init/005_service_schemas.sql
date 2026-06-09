\connect auth_db

CREATE TABLE users (
  id TEXT PRIMARY KEY,
  provider TEXT NOT NULL,
  login_id TEXT NOT NULL,
  display_name TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (provider, login_id)
);

\connect booking_db

CREATE TABLE booking_requests (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  performance_id TEXT NOT NULL,
  seat_id TEXT NOT NULL,
  show_date DATE NOT NULL,
  status TEXT NOT NULL,
  failure_reason TEXT,
  booking_id TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

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
  UNIQUE (performance_id, performance_date, seat_id)
);

CREATE INDEX idx_booking_requests_user_id ON booking_requests(user_id);
CREATE INDEX idx_booking_requests_status ON booking_requests(status);
CREATE INDEX idx_bookings_user_id ON bookings(user_id);
CREATE INDEX idx_bookings_performance_id ON bookings(performance_id);

\connect payment_db

CREATE TABLE point_balances (
  user_id TEXT PRIMARY KEY,
  balance INTEGER NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

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

CREATE INDEX idx_payment_history_user_id ON payment_history(user_id);
CREATE INDEX idx_payment_history_paid_at ON payment_history(paid_at);
