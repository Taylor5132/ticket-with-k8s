# DB 명세서

> 작성일: 2026-06-14 · 기준: app-repo 최신 코드 · 작성: 자동생성(검토 필요)

## 1. 개요

본 시스템은 **단일 PostgreSQL 인스턴스**를 사용하되, 서비스별로 데이터베이스(DB)를 분리하여 운영한다. 각 DB는 소유 서비스(owner service)가 책임지고 관리하며, DB 간 직접적인 외래키(FK)는 두지 않고 서비스 경계를 넘는 참조는 논리 참조로만 둔다.

분리된 DB는 다음 4개이다.

- `auth_db`
- `event_db`
- `booking_db`
- `payment_db`

### 1.1 서비스 - DB 매핑

| DB | 소유 서비스 | 비고 |
| --- | --- | --- |
| `auth_db` | auth-service | OAuth/login 사용자 계정 |
| `event_db` | event-service | 공연/공연장 마스터 데이터 (KOPIS), 기본 연결 DB |
| `booking_db` | booking-service (booking-api / booking-worker) | 예매 요청/확정 예매 |
| `payment_db` | payment-service | 포인트 잔액/결제 내역 |

## 2. DB별 테이블 명세

### 2.1 `auth_db` (auth-service)

#### 2.1.1 `users`

- **용도**: OAuth/login 사용자 계정 정보 저장 (provider + login_id 단위로 유일)
- **PK**: `id`
- **FK**: 없음
- **UNIQUE**: `UNIQUE (provider, login_id)`
- **인덱스**: `UNIQUE (provider, login_id)` 제약에 의한 암묵적 유니크 인덱스

| 컬럼명 | 타입 | 제약 | 설명 |
| --- | --- | --- | --- |
| `id` | TEXT | PRIMARY KEY | 사용자 ID(텍스트 PK, 애플리케이션이 생성) |
| `provider` | TEXT | NOT NULL; UNIQUE(provider, login_id)의 일부 | 인증 제공자 (예: google, local 등) |
| `login_id` | TEXT | NOT NULL; UNIQUE(provider, login_id)의 일부 | 제공자 내 로그인 식별자 |
| `display_name` | TEXT | NOT NULL | 표시 이름 |
| `created_at` | TIMESTAMPTZ | NOT NULL DEFAULT now() | 생성 시각 |
| `updated_at` | TIMESTAMPTZ | NOT NULL DEFAULT now() | 수정 시각 |

### 2.2 `event_db` (event-service)

공연(KOPIS) 마스터 데이터는 `010_ticketing.sql`(pg_dump)에서 정의되며, 해당 스크립트에 `\connect`가 없으므로 `POSTGRES_DB=event_db` 기본 연결로 실행되어 `event_db`에 적재된다.

#### 2.2.1 `performances`

- **용도**: 공연(KOPIS) 마스터 데이터. `010_ticketing.sql`(pg_dump)에서 정의되며 기본 DB(`event_db`)에 적재됨. `\connect` 없음 → `POSTGRES_DB=event_db` 기본 연결로 실행
- **PK**: `id`
- **FK**: `performances_venue_id_fkey: FOREIGN KEY (venue_id) REFERENCES public.venues(id)`
- **UNIQUE**: `performances_kopis_id_key: UNIQUE (kopis_id)`
- **인덱스**:
  - `idx_performances_genre ON public.performances(genre)` (020_fix_event_sequences.sql, IF NOT EXISTS)
  - `idx_performances_status ON public.performances(status)` (020)
  - `idx_performances_start_date ON public.performances(start_date)` (020)
  - `performances_kopis_id_key` (UNIQUE 제약 암묵 인덱스)
  - `performances_pkey` (PK 암묵 인덱스)

| 컬럼명 | 타입 | 제약 | 설명 |
| --- | --- | --- | --- |
| `id` | integer | NOT NULL; PRIMARY KEY(performances_pkey); DEFAULT nextval('public.performances_id_seq'::regclass) (시퀀스 OWNED BY id) | 공연 PK(자동 증가) |
| `kopis_id` | character varying(20) | UNIQUE(performances_kopis_id_key) | KOPIS 공연 ID |
| `venue_id` | integer | FK → public.venues(id) | 공연장 ID(외래키) |
| `title` | character varying(500) | | 공연 제목 |
| `start_date` | date | | 공연 시작일 |
| `end_date` | date | | 공연 종료일 |
| `poster_url` | text | | 포스터 이미지 URL |
| `genre` | character varying(100) | | 장르 |
| `status` | character varying(20) | | 공연 상태(예: 공연예정) |
| `is_open_run` | character(1) | | 오픈런 여부 (Y/N) |
| `cast_text` | text | | 출연진 텍스트 |
| `runtime` | character varying(50) | | 공연 시간(러닝타임) |
| `age_rating` | character varying(50) | | 관람 연령 등급 |
| `description` | text | | 공연 설명 |
| `intro_image_urls` | text | | 소개 이미지 URL 목록(파이프 \| 구분 문자열) |
| `schedule` | text | | 공연 일정 텍스트(예: 일요일(14:00)) |

#### 2.2.2 `venues`

- **용도**: 공연장(venue) 마스터 데이터. `010_ticketing.sql`(pg_dump)에서 정의, 기본 DB(`event_db`)에 적재
- **PK**: `id`
- **FK**: 없음
- **UNIQUE**: `venues_kopis_id_key: UNIQUE (kopis_id)`
- **인덱스**:
  - `idx_venues_province ON public.venues(province)` (020_fix_event_sequences.sql, IF NOT EXISTS)
  - `venues_kopis_id_key` (UNIQUE 제약 암묵 인덱스)
  - `venues_pkey` (PK 암묵 인덱스)

| 컬럼명 | 타입 | 제약 | 설명 |
| --- | --- | --- | --- |
| `id` | integer | NOT NULL; PRIMARY KEY(venues_pkey); DEFAULT nextval('public.venues_id_seq'::regclass) (시퀀스 OWNED BY id) | 공연장 PK(자동 증가) |
| `kopis_id` | character varying(20) | UNIQUE(venues_kopis_id_key) | KOPIS 공연장 ID |
| `name` | character varying(255) | | 공연장 이름 |
| `address` | text | | 주소 |
| `province` | character varying(50) | | 광역시/도 |
| `district` | character varying(50) | | 시/군/구 |
| `seat_capacity` | integer | | 좌석 수용 인원 |
| `phone` | character varying(20) | | 전화번호 |
| `latitude` | numeric(18,14) | | 위도 |
| `longitude` | numeric(18,14) | | 경도 |
| `halls_text` | text | | 공연장 내 홀 정보 텍스트 |

### 2.3 `booking_db` (booking-service: booking-api / booking-worker)

#### 2.3.1 `booking_requests`

- **용도**: 예매 요청(비동기 처리) 상태 추적. 성공 시 `booking_id`로 확정 예매와 연결
- **PK**: `id`
- **FK**: 없음
- **UNIQUE**: 없음
- **인덱스**:
  - `idx_booking_requests_user_id ON booking_requests(user_id)`
  - `idx_booking_requests_status ON booking_requests(status)`

| 컬럼명 | 타입 | 제약 | 설명 |
| --- | --- | --- | --- |
| `id` | TEXT | PRIMARY KEY | 예매 요청 ID(텍스트 PK) |
| `user_id` | TEXT | NOT NULL | 요청 사용자 ID(auth_db.users.id 논리 참조, DB FK 없음) |
| `performance_id` | TEXT | NOT NULL | 공연 ID(event_db.performances 논리 참조, DB FK 없음) |
| `seat_id` | TEXT | NOT NULL | 좌석 ID |
| `show_date` | DATE | NOT NULL | 공연 회차 날짜 |
| `status` | TEXT | NOT NULL | 요청 처리 상태 |
| `failure_reason` | TEXT | NULL 허용 | 실패 사유(실패 시) |
| `booking_id` | TEXT | NULL 허용 | 확정된 예매 ID(성공 시 bookings.id와 매칭) |
| `created_at` | TIMESTAMPTZ | NOT NULL DEFAULT now() | 생성 시각 |
| `updated_at` | TIMESTAMPTZ | NOT NULL DEFAULT now() | 수정 시각 |

#### 2.3.2 `bookings`

- **용도**: 확정된 예매 정보(스냅샷 포함). 같은 공연/날짜/좌석 중복 예매를 UNIQUE로 방지
- **PK**: `id`
- **FK**: `booking_request_id → booking_requests(id)` (REFERENCES, 동시에 UNIQUE)
- **UNIQUE**:
  - `booking_request_id` UNIQUE (1:1 예매요청-예매)
  - `UNIQUE (performance_id, performance_date, seat_id)` (좌석 중복 예매 방지)
- **인덱스**:
  - `idx_bookings_user_id ON bookings(user_id)`
  - `idx_bookings_performance_id ON bookings(performance_id)`
  - `booking_request_id` UNIQUE 제약에 의한 암묵 인덱스
  - `UNIQUE (performance_id, performance_date, seat_id)` 암묵 인덱스

| 컬럼명 | 타입 | 제약 | 설명 |
| --- | --- | --- | --- |
| `id` | TEXT | PRIMARY KEY | 예매 ID(텍스트 PK) |
| `booking_request_id` | TEXT | NOT NULL; UNIQUE; FK REFERENCES booking_requests(id) | 연결된 예매 요청 ID(1:1) |
| `user_id` | TEXT | NOT NULL | 예매 사용자 ID |
| `performance_id` | TEXT | NOT NULL; UNIQUE(performance_id, performance_date, seat_id)의 일부 | 공연 ID |
| `performance_title` | TEXT | NOT NULL | 공연 제목 스냅샷 |
| `venue_name` | TEXT | NOT NULL | 공연장 이름 스냅샷 |
| `performance_date` | DATE | NOT NULL; UNIQUE(performance_id, performance_date, seat_id)의 일부 | 공연 날짜 |
| `seat_id` | TEXT | NOT NULL; UNIQUE(performance_id, performance_date, seat_id)의 일부 | 좌석 ID |
| `seat_grade` | TEXT | NOT NULL | 좌석 등급 |
| `paid_amount` | INTEGER | NOT NULL | 결제 금액(포인트/원) |
| `booked_at` | TIMESTAMPTZ | NOT NULL DEFAULT now() | 예매 확정 시각 |

### 2.4 `payment_db` (payment-service)

#### 2.4.1 `point_balances`

- **용도**: 사용자별 포인트(잔액) 보유 현황
- **PK**: `user_id`
- **FK**: 없음
- **UNIQUE**: 없음
- **인덱스**: `point_balances_pkey` (user_id PK 암묵 인덱스)

| 컬럼명 | 타입 | 제약 | 설명 |
| --- | --- | --- | --- |
| `user_id` | TEXT | PRIMARY KEY | 사용자 ID(텍스트 PK, 사용자당 1행) |
| `balance` | INTEGER | NOT NULL | 포인트 잔액 |
| `updated_at` | TIMESTAMPTZ | NOT NULL DEFAULT now() | 잔액 갱신 시각 |

#### 2.4.2 `payment_history`

- **용도**: 결제 내역. `booking_request_id` 단위로 1회 결제 보장(UNIQUE)
- **PK**: `id`
- **FK**: 없음
- **UNIQUE**: `booking_request_id` UNIQUE (멱등 결제 보장)
- **인덱스**:
  - `idx_payment_history_user_id ON payment_history(user_id)`
  - `idx_payment_history_paid_at ON payment_history(paid_at)`
  - `booking_request_id` UNIQUE 제약에 의한 암묵 인덱스

| 컬럼명 | 타입 | 제약 | 설명 |
| --- | --- | --- | --- |
| `id` | TEXT | PRIMARY KEY | 결제 내역 ID(텍스트 PK) |
| `user_id` | TEXT | NOT NULL | 결제 사용자 ID |
| `booking_request_id` | TEXT | NOT NULL; UNIQUE | 예매 요청 ID(booking_db.booking_requests.id 논리 참조, DB FK 없음; 멱등성 키) |
| `booking_id` | TEXT | NULL 허용 | 확정 예매 ID(booking_db.bookings.id 논리 참조) |
| `performance_title` | TEXT | NOT NULL | 공연 제목 스냅샷 |
| `amount` | INTEGER | NOT NULL | 결제 금액 |
| `status` | TEXT | NOT NULL DEFAULT 'PAID' | 결제 상태(기본값 PAID) |
| `paid_at` | TIMESTAMPTZ | NOT NULL DEFAULT now() | 결제 시각 |

## 3. 테이블 간 관계 요약

DB 내부 관계는 물리적 FK로, DB 경계를 넘는 관계는 논리 참조(DB FK 없음)로 구분한다.

### 3.1 물리적 외래키(같은 DB 내)

| 출발 테이블 | 컬럼 | 도착 테이블 | 관계 | 비고 |
| --- | --- | --- | --- | --- |
| `event_db.performances` | `venue_id` | `event_db.venues` (id) | N:1 | `performances_venue_id_fkey` |
| `booking_db.bookings` | `booking_request_id` | `booking_db.booking_requests` (id) | 1:1 | FK + UNIQUE |

### 3.2 논리 참조(DB 경계를 넘는 참조, DB FK 없음)

| 출발 테이블 | 컬럼 | 도착(논리) | 비고 |
| --- | --- | --- | --- |
| `booking_db.booking_requests` | `user_id` | `auth_db.users.id` | DB FK 없음 |
| `booking_db.booking_requests` | `performance_id` | `event_db.performances` | DB FK 없음 |
| `booking_db.booking_requests` | `booking_id` | `booking_db.bookings.id` | 성공 시 매칭 |
| `payment_db.payment_history` | `booking_request_id` | `booking_db.booking_requests.id` | DB FK 없음; 멱등성 키 |
| `payment_db.payment_history` | `booking_id` | `booking_db.bookings.id` | DB FK 없음 |

### 3.3 핵심 무결성 규칙

| 규칙 | 적용 위치 | 효과 |
| --- | --- | --- |
| 사용자 유일성 | `auth_db.users` UNIQUE(provider, login_id) | provider+login_id 단위 1계정 |
| 공연/공연장 KOPIS 유일성 | `performances.kopis_id`, `venues.kopis_id` UNIQUE | KOPIS ID 중복 적재 방지 |
| 예매요청-예매 1:1 | `bookings.booking_request_id` UNIQUE | 한 요청당 한 예매 |
| 좌석 중복 예매 방지 | `bookings` UNIQUE(performance_id, performance_date, seat_id) | 동일 공연/날짜/좌석 1예매 |
| 멱등 결제 | `payment_history.booking_request_id` UNIQUE | 예매요청당 1회 결제 |

## 부록: Redis 키 구조

Redis는 영속 DB가 아니므로 본 명세서의 정식 테이블 명세 대상에서 제외하며, 운영상 사용되는 키 구조만 간단히 정리한다.

| 용도 | 키 / 스트림 | 비고 |
| --- | --- | --- |
| 대기열 | `queue:` | 대기열 큐 |
| 대기열 시퀀스 | `seq:` | 순번 발급 |
| 대기열 토큰 | `token:` | 입장/대기 토큰 |
| 대기열 작업 스트림 | `work-stream` | 대기열 워크 스트림 |
| 예매 스트림 | `booking.requests` | 예매 요청 스트림 |
