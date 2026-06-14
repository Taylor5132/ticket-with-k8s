# API 명세서

> 작성일: 2026-06-14 · 기준: app-repo 최신 코드 · 작성: 자동생성(검토 필요)

본 문서는 app-repo 내 마이크로서비스(auth-service, event-service, booking-service, payment-service, saved-service)의 HTTP API를 정리한 명세서입니다. 모든 내용은 주어진 서비스 데이터에 근거하며, 데이터에 없는 항목은 기재하지 않습니다.

---

## ① 공통 사항

### 1. 베이스 경로

- 클라이언트 노출 API는 기본적으로 `/api` 경로 하위로 라우팅됩니다.
- booking-service의 좌석 가용성 엔드포인트는 `/api/performances/...` 경로와 함께 `/performances/...` alias(별칭)도 제공합니다.
- event-service의 `/internal/...`, booking-service의 워커/디스패처 처리 경로 등 일부는 내부 처리용 또는 내부 전용입니다(아래 각 서비스 명세 참조).

### 2. 인증 방식

| 인증 방식 | 헤더 | 설명 | 적용 대상 |
|---|---|---|---|
| JWT Bearer (current_user) | `Authorization: Bearer <jwt>` | 사용자 인증. JWT를 `JWT_SECRET`/HS256으로 디코드하여 `sub`(사용자 id), `display_name`, `provider`를 추출하는 `current_user` 의존성. 누락/디코드 실패 시 `401 UNAUTHORIZED`. | 사용자용 보호 엔드포인트 |
| 서비스 간 토큰 (X-Service-Token) | `X-Service-Token: <token>` | 서비스 간 내부 호출 인증. `SERVICE_TOKEN`과 비교하여 일치 시에만 허용. 불일치 시 `403 FORBIDDEN`. | 내부 전용 엔드포인트 |
| 없음 (none) | - | 인증 불필요(헬스체크, 공개 카탈로그 조회, OAuth 진입점 등) | 공개 엔드포인트 |

#### JWT 토큰 발급 (auth-service)

- `issue_token`: 알고리즘 HS256, `JWT_SECRET` 서명.
- payload: `sub`, `provider`, `display_name`, `iat`, `exp`.
- 만료: 12시간.

### 3. 공통 에러 코드 포맷

에러 응답은 다음 형식의 JSON 본문을 가집니다.

```json
{
  "code": "<ERROR_CODE>",
  "message": "<사용자용 메시지>"
}
```

#### 공통/반복 에러 코드

| HTTP | code | message | 발생 조건 |
|---|---|---|---|
| 401 | UNAUTHORIZED | 로그인이 필요한 기능입니다. | `current_user` 의존성: Bearer 헤더 없음 / 토큰 디코드 실패 |
| 403 | FORBIDDEN | 요청 권한이 없습니다. | `X-Service-Token` 불일치 |
| 404 | NOT_FOUND | 요청한 정보를 찾을 수 없습니다. | 대상 리소스 없음 |

> 참고: OAuth 콜백(auth-service `/auth/google/callback`)은 위 JSON 에러 포맷 대신, 오류를 프론트엔드로의 `oauth_error` 쿼리 리다이렉트로 처리합니다(해당 엔드포인트 명세 참조).

### 4. 서비스 개요

| 서비스 | 목적 | 포트 | 데이터베이스 | Redis |
|---|---|---|---|---|
| auth-service | 사용자 인증/계정 관리(로컬·Google OAuth·dev 로그인, JWT 발급) | 컨테이너 내부 8000, 호스트 8001:8000 | auth_db (postgresql+psycopg) · 테이블: users | 미사용 |
| event-service | KOPIS 공연/공연장 카탈로그 조회 및 회차·좌석등급 계산(읽기 전용) | 8000 | event_db | 미사용 |
| booking-service | 좌석 예매 비동기 처리 + Redis 대기열로 트래픽 제어 | 8000 | booking_db (postgresql+psycopg) | 사용(스트림/대기열/입장토큰) |
| payment-service | 포인트 잔액 관리 및 예매 시 포인트 차감/결제 기록 | 컨테이너 내부 8000, 호스트 8005:8000 | payment_db (PostgreSQL) | 미사용 |
| saved-service | 사용자별 공연 찜 목록 관리(Redis Set) | 컨테이너 내부 8000, 호스트 8003:8000 | 없음(영속 저장소는 Redis만 사용) | 사용(찜 목록 Set) |

### 5. 관측성(공통)

모든 서비스 공통: `OTEL_EXPORTER_OTLP_ENDPOINT` 설정 시 OpenTelemetry 트레이싱 활성화, `prometheus-fastapi-instrumentator`로 `/metrics` 노출, CORS 전체 허용.

---

## ② 서비스별 엔드포인트 명세

---

## auth-service

사용자 인증/계정 관리 서비스. 로컬(아이디·비밀번호) 회원가입·로그인, Google OAuth 로그인, 개발용 로그인을 처리하고 JWT 액세스 토큰을 발급한다.

- 데이터베이스: auth_db (postgresql+psycopg, 기본 `postgresql+psycopg://postgres:postgres@postgres:5432/auth_db`) · 테이블: `users`
- 스키마 자동 마이그레이션: startup 이벤트에서 `ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash TEXT` 실행

### 엔드포인트 요약

| 메서드 | 경로 | 인증 | 설명 |
|---|---|---|---|
| GET | /health | none | 헬스체크 |
| POST | /auth/dev-login | none | 개발용 로그인(upsert 후 JWT 발급) |
| POST | /auth/signup | none | 로컬 회원가입 |
| POST | /auth/login | none | 로컬 로그인 |
| GET | /auth/me | JWT(current_user) | 내 정보 조회 |
| GET | /auth/google | none | Google OAuth 시작 |
| GET | /auth/google/callback | none (oauth_state 쿠키 CSRF 검증) | Google OAuth 콜백 |

---

### GET /health

| 항목 | 내용 |
|---|---|
| 인증 | none |
| 설명 | 헬스체크 |
| 요청 (path/query/body) | 없음 |
| 응답 | `{"status": "ok"}` |
| 에러코드 | 없음 |
| 접근 테이블 | 없음 |
| 외부호출 | 없음 |

---

### POST /auth/dev-login

| 항목 | 내용 |
|---|---|
| 인증 | none |
| 설명 | 개발용 로그인: 임의 provider/login_id/display_name으로 사용자 upsert(ON CONFLICT(provider,login_id) DO UPDATE) 후 JWT 발급. 비밀번호 검증 없음(개발/테스트용). |
| 요청 - path | 없음 |
| 요청 - query | 없음 |
| 요청 - body | `DevLoginRequest { provider: str, login_id: str, display_name: str }` |
| 응답 | `{ access_token, token_type: "bearer", user: { id, provider, login_id, display_name } }` |
| 에러코드 | 없음 |
| 접근 테이블 | users |
| 외부호출 | 없음 |

---

### POST /auth/signup

| 항목 | 내용 |
|---|---|
| 인증 | none |
| 설명 | 로컬 회원가입: login_id(4~20자 영문·숫자·밑줄 정규식), password(8자 이상), display_name(공백 아님) 검증 후 bcrypt 해시, provider='local'로 INSERT, JWT 발급. |
| 요청 - path | 없음 |
| 요청 - query | 없음 |
| 요청 - body | `SignupRequest { login_id: str, password: str, display_name: str }` |
| 응답 | `{ access_token, token_type: "bearer", user: { id, provider, login_id, display_name } }` |
| 접근 테이블 | users |
| 외부호출 | 없음 |

#### 에러코드

| HTTP | code | message |
|---|---|---|
| 400 | INVALID_ID | 아이디는 4~20자 영문·숫자·밑줄만 사용할 수 있습니다. |
| 400 | WEAK_PASSWORD | 비밀번호는 8자 이상이어야 합니다. |
| 400 | INVALID_NAME | 닉네임을 입력해 주세요. |
| 409 | ID_TAKEN | 이미 사용 중인 아이디입니다. |

---

### POST /auth/login

| 항목 | 내용 |
|---|---|
| 인증 | none |
| 설명 | 로컬 로그인: provider='local' 사용자의 password_hash를 `bcrypt.checkpw`로 검증 후 JWT 발급. |
| 요청 - path | 없음 |
| 요청 - query | 없음 |
| 요청 - body | `LocalLoginRequest { login_id: str, password: str }` |
| 응답 | `{ access_token, token_type: "bearer", user: { id, provider, login_id, display_name } }` |
| 접근 테이블 | users |
| 외부호출 | 없음 |

#### 에러코드

| HTTP | code | message |
|---|---|---|
| 401 | INVALID_CREDENTIALS | 아이디 또는 비밀번호가 올바르지 않습니다. (사용자 없음 / password_hash 없음 / 비밀번호 불일치) |

---

### GET /auth/me

| 항목 | 내용 |
|---|---|
| 인증 | JWT(current_user) |
| 설명 | JWT의 `sub`(id)로 users에서 현재 사용자 정보 조회. |
| 요청 - path | 없음 |
| 요청 - query | 없음 (`Authorization: Bearer` 헤더 사용) |
| 요청 - body | 없음 |
| 응답 | `{ id, provider, login_id, display_name }` |
| 접근 테이블 | users |
| 외부호출 | 없음 |

#### 에러코드

| HTTP | code | message |
|---|---|---|
| 401 | UNAUTHORIZED | 로그인이 필요한 기능입니다. (current_user 의존성: Bearer 없음 / 토큰 디코드 실패) |
| 404 | NOT_FOUND | 요청한 정보를 찾을 수 없습니다. |

---

### GET /auth/google

| 항목 | 내용 |
|---|---|
| 인증 | none |
| 설명 | Google OAuth 시작: CSRF용 state 토큰(`secrets.token_urlsafe`) 생성, httponly `oauth_state` 쿠키(max_age 300, samesite=lax) 설정 후 Google 인증 URL로 302 리다이렉트. |
| 요청 - path | 없음 |
| 요청 - query | 없음 |
| 요청 - body | 없음 |
| 응답 | `302 RedirectResponse` → Google authorize URL, `Set-Cookie: oauth_state`(httponly, max_age 300, samesite lax) |
| 접근 테이블 | 없음 |
| 외부호출 | Google `accounts.google.com/o/oauth2/v2/auth` (리다이렉트 대상) |

#### 에러코드

| HTTP | code | message |
|---|---|---|
| 503 | OAUTH_NOT_CONFIGURED | Google 로그인이 설정되지 않았습니다. (GOOGLE_CLIENT_ID 미설정) |

---

### GET /auth/google/callback

| 항목 | 내용 |
|---|---|
| 인증 | none (`oauth_state` 쿠키로 CSRF 검증) |
| 설명 | Google OAuth 콜백: `oauth_state` 쿠키와 state 파라미터 일치 검증, Google token/userinfo API 호출, provider='google'로 사용자 upsert, JWT 발급 후 `FRONTEND_URL`로 token·user를 쿼리스트링에 담아 리다이렉트. |
| 요청 - path | 없음 |
| 요청 - query | `code`, `state`, `error` (모두 default `""`) |
| 요청 - body | 없음 |
| 응답 | `302 RedirectResponse` → 성공: `FRONTEND_URL/?token=<jwt>&user=<json>` / 실패: `FRONTEND_URL/?oauth_error=...`, `oauth_state` 쿠키 삭제 |
| 접근 테이블 | users |
| 외부호출 | Google `oauth2.googleapis.com/token` (POST httpx), Google `www.googleapis.com/oauth2/v3/userinfo` (GET httpx) |

#### 에러 처리(특이사항)

에러는 HTTPException(JSON `{code,message}`) 대신 `oauth_error` 쿼리 리다이렉트로 처리합니다.

| oauth_error 값 | 발생 조건 |
|---|---|
| (error 파라미터 값) | `error` 파라미터가 존재할 때 |
| invalid_state | state 불일치 |
| google_api_error | 토큰/유저정보 호출 중 예외 |

---

## event-service

KOPIS 공연/공연장 카탈로그를 조회하고, 공연 회차(스케줄) 계산 및 좌석 등급/가격 정의를 제공하는 읽기 전용 카탈로그 서비스.

- 데이터베이스: event_db · 테이블: `performances`, `venues`
- 고정 가격표: `VIP석 150,000원, R석 120,000원, S석 90,000원, A석 60,000원`
- 좌석 등급 규칙(GRADE_RULES, 행 문자 A~H): A/B→VIP 150000, C/D→R 120000, E/F→S 90000, G/H→A 60000

### 엔드포인트 요약

| 메서드 | 경로 | 인증 | 설명 | 내부전용 |
|---|---|---|---|---|
| GET | /health | none | 헬스체크 | - |
| GET | /performances | none | 공연 목록 조회/필터링 | - |
| GET | /performances/{performance_id} | none | 공연 상세 조회 | - |
| GET | /internal/performances/{performance_id}/seats/{seat_id} | none | 좌석 등급/가격 정의 조회 | 내부 전용 |

---

### GET /health

| 항목 | 내용 |
|---|---|
| 인증 | none |
| 설명 | 헬스체크 |
| 요청 (path/query/body) | 없음 |
| 응답 | `{"status": "ok"}` |
| 에러코드 | 없음 |
| 접근 테이블 | 없음 |
| 외부호출 | 없음 |

---

### GET /performances

| 항목 | 내용 |
|---|---|
| 인증 | none |
| 설명 | 공연 목록 조회. genre/area/status 필터링, `start_date` ASC, `id` ASC 정렬. performances를 venues와 조인. |
| 요청 - path | 없음 |
| 요청 - query | `genre?`, `area?`, `status?` (모두 선택) |
| 요청 - body | 없음 |
| 응답 | `{ "items": [performance_card] }` — 각 카드: `{ id, kopis_id, title, poster_url, venue_name, area(=province), genre, start_date, end_date, status }` |
| 에러코드 | 없음 |
| 접근 테이블 | performances, venues |
| 외부호출 | 없음 |

---

### GET /performances/{performance_id}

| 항목 | 내용 |
|---|---|
| 인증 | none |
| 설명 | 공연 상세 조회. 공연장 정보 및 계산된 회차(schedules)·고정 가격표(price_text) 포함. `is_open_run`은 'Y' 여부로 bool 변환, 위도/경도 float 변환. |
| 요청 - path | `performance_id` (str) |
| 요청 - query | 없음 |
| 요청 - body | 없음 |
| 응답 | `{ id, kopis_id, title, poster_url, genre, status, start_date, end_date, is_open_run(bool), cast_text, runtime, age_rating, price_text, guidance_text, intro_image_urls[], schedules[], venue: { id, kopis_id, name, address, province, district, seat_capacity, phone, latitude, longitude, halls_text } }` |
| 접근 테이블 | performances, venues |
| 외부호출 | 없음 |

#### 에러코드

| HTTP | code | message |
|---|---|---|
| 404 | NOT_FOUND | 요청한 정보를 찾을 수 없습니다. |

---

### GET /internal/performances/{performance_id}/seats/{seat_id} 〔내부 전용〕

> 내부 전용 엔드포인트. DB에 접근하지 않고 `seat_id` 접두(행 문자)로 등급/가격을 순수 계산합니다.

| 항목 | 내용 |
|---|---|
| 인증 | none |
| 설명 | 좌석 등급/가격 정의 조회. `seat_id`를 `-`로 split한 첫 토큰(행 문자 A~H)으로 GRADE_RULES에 매핑해 grade/price 계산. |
| 요청 - path | `performance_id` (str), `seat_id` (str) |
| 요청 - query | 없음 |
| 요청 - body | 없음 |
| 응답 | `{ performance_id, seat_id, grade, price }` (예: grade=VIP/R/S/A, price=150000/120000/90000/60000) |
| 접근 테이블 | 없음 (DB 미접근) |
| 외부호출 | 없음 |

#### 에러코드

| HTTP | code | message |
|---|---|---|
| 404 | NOT_FOUND | 요청한 정보를 찾을 수 없습니다. (seat_id 행 문자가 GRADE_RULES(A~H)에 없을 때) |

---

## booking-service

공연 좌석 예매를 비동기 스트림으로 처리하고, Redis 기반 대기열(Waiting Queue)로 트래픽 유입량을 제어하는 예매 서비스.

- 데이터베이스: booking_db (postgresql+psycopg) · 테이블: `bookings`, `booking_requests`
- Redis 용도 요약:

| 구분 | 키/스트림 | 용도 |
|---|---|---|
| 예매 요청 큐 | STREAM_NAME=`booking.requests` (Consumer Group `booking-workers`) | XADD/XREADGROUP 비동기 처리 |
| 대기열 FIFO | ZSET `queue:{perf}:{date}`, INCR `seq:{perf}:{date}`, Set `active-queues` | 번호표(score) ZADD/ZRANK/ZCARD, 원자적 번호표 발급, Dispatcher 순회 레지스트리 |
| 입장 처리 스트림 | WORK_STREAM=`work-stream` (Consumer Group `admission-workers`) | Lua로 ZPOPMIN+XADD 원자 핸드오프 |
| 입장 토큰 | `token:{perf}:{date}:{user_id}` (SET ex=`ADMISSION_TOKEN_TTL` 기본 600초) | 입장 토큰 |
| 만료 | `QUEUE_TTL` 기본 3600초 | 유휴 큐/seq 만료 |

- 비동기 처리 구성요소(내부 프로세스, HTTP 엔드포인트 아님): Worker(`worker.py`), Dispatcher(`dispatcher.py`), Admission Worker(`admission_worker.py`).

### 엔드포인트 요약

| 메서드 | 경로 | aliases | 인증 | 설명 |
|---|---|---|---|---|
| GET | /health | - | none | 헬스체크 |
| GET | /api/performances/{performance_id}/seat-availability | /performances/{performance_id}/seat-availability | none | 좌석 가용성 조회 |
| POST | /booking-requests | - | JWT(current_user) | 예매 요청 생성(비동기) |
| GET | /booking-requests/{request_id} | - | JWT(current_user) | 예매 요청 상태 조회 |
| POST | /queue/join | - | JWT(current_user) | 대기열 진입 |
| GET | /queue/status | - | JWT(current_user) | 대기열 상태 조회 |
| GET | /bookings/me | - | JWT(current_user) | 내 예매 목록 조회 |
| GET | /metrics | - | none | Prometheus 메트릭 |

---

### GET /health

| 항목 | 내용 |
|---|---|
| 인증 | none |
| 설명 | 헬스체크 |
| 요청 (path/query/body) | 없음 |
| 응답 | `{"status": "ok"}` |
| 에러코드 | 없음 |
| 접근 테이블 | 없음 |
| 외부호출 | 없음 |

---

### GET /api/performances/{performance_id}/seat-availability

> aliases(별칭): `/performances/{performance_id}/seat-availability`

| 항목 | 내용 |
|---|---|
| 인증 | none |
| 설명 | 공연/일자별 80석(A~H행 1~10번)의 가용성 조회. 이미 예매된 좌석은 OCCUPIED. 좌석 등급/가격은 행 기준 고정 규칙(A/B=VIP 150000, C/D=R 120000, E/F=S 90000, G/H=A 60000). |
| 요청 - path | `performance_id` |
| 요청 - query | `show_date` (필수, `Query(...)`) |
| 요청 - body | 없음 |
| 응답 | `{ performance_id, show_date, seats: [{ seat_id, row, number, grade, price, status }] }` |
| 에러코드 | 없음 (명세상 기재 없음) |
| 접근 테이블 | bookings |
| 외부호출 | 없음 |

---

### POST /booking-requests

| 항목 | 내용 |
|---|---|
| 인증 | JWT(current_user) |
| 설명 | 예매 요청 생성: booking_requests에 PENDING 기록 후 `booking.requests` 스트림에 XADD하고 request_id 반환. 실제 처리는 워커가 비동기 수행. `ENFORCE_ADMISSION_TOKEN=true`면 입장 토큰 없이는 403 차단. |
| 요청 - path | 없음 |
| 요청 - query | 없음 |
| 요청 - body | `BookingRequestCreate { performance_id: str, seat_id: str, show_date: str (YYYY-MM-DD) }` |
| 응답 | `{ request_id, status: "PENDING" }` |
| 접근 테이블 | booking_requests |
| 외부호출 | 없음 (HTTP 응답 시점 기준) |

#### 에러코드

| HTTP | code | message |
|---|---|---|
| 403 | NO_ADMISSION_TOKEN | 대기열을 통과한 뒤 예매할 수 있습니다 (ENFORCE_ADMISSION_TOKEN=true이고 입장 토큰 없을 때) |
| 400 | INVALID_SEAT | 좌석을 선택해 주세요 (유효하지 않은 seat_id) |

---

### GET /booking-requests/{request_id}

| 항목 | 내용 |
|---|---|
| 인증 | JWT(current_user) |
| 설명 | 본인 예매 요청의 처리 상태(PENDING/PROCESSING/CONFIRMED/FAILED) 폴링 조회. |
| 요청 - path | `request_id` |
| 요청 - query | 없음 |
| 요청 - body | 없음 |
| 응답 | `{ request_id, status, failure_reason, booking_id, show_date(ISO or null) }` |
| 접근 테이블 | booking_requests |
| 외부호출 | 없음 |

#### 에러코드

| HTTP | code | message |
|---|---|---|
| 404 | NOT_FOUND | 요청한 정보를 찾을 수 없습니다 (해당 user의 요청 없음) |

---

### POST /queue/join

| 항목 | 내용 |
|---|---|
| 인증 | JWT(current_user) |
| 설명 | 대기줄 진입. 처음 진입자만 INCR 번호표를 score로 ZADD(nx)하고 active-queues에 등록(FIFO). 입장 토큰이 이미 있으면 즉시 admitted. |
| 요청 - path | 없음 |
| 요청 - query | `performance_id`, `show_date` |
| 요청 - body | 없음 (쿼리 파라미터로 받음) |
| 응답 | `{ admitted, position, total }` |
| 에러코드 | 없음 (명세상 기재 없음) |
| 접근 테이블 | 없음 (Redis 사용) |
| 외부호출 | 없음 |

---

### GET /queue/status

| 항목 | 내용 |
|---|---|
| 인증 | JWT(current_user) |
| 설명 | 입장 여부(토큰 존재)와 대기 위치/전체 인원 조회. 토큰 있으면 admitted, 줄에 있으면 position/total, 줄에서 빠졌으나 토큰 미발급(스트림 처리 중)이면 대기 응답. |
| 요청 - path | 없음 |
| 요청 - query | `performance_id`, `show_date` |
| 요청 - body | 없음 |
| 응답 | `{ admitted, position, total }` |
| 에러코드 | 없음 (명세상 기재 없음) |
| 접근 테이블 | 없음 (Redis 사용) |
| 외부호출 | 없음 |

---

### GET /bookings/me

| 항목 | 내용 |
|---|---|
| 인증 | JWT(current_user) |
| 설명 | 본인의 확정 예매 내역을 `booked_at` 내림차순으로 조회. |
| 요청 - path | 없음 |
| 요청 - query | 없음 |
| 요청 - body | 없음 |
| 응답 | `{ items: [{ id, performance_id, performance_title, venue_name, performance_date(ISO), seat_id, seat_grade, paid_amount, booked_at(ISO) }] }` |
| 에러코드 | 없음 (명세상 기재 없음) |
| 접근 테이블 | bookings |
| 외부호출 | 없음 |

---

### GET /metrics

| 항목 | 내용 |
|---|---|
| 인증 | none |
| 설명 | Prometheus 메트릭 노출 (`prometheus_fastapi_instrumentator`가 자동 등록). |
| 요청 (path/query/body) | 없음 |
| 응답 | Prometheus text exposition format |
| 에러코드 | 없음 |
| 접근 테이블 | 없음 |
| 외부호출 | 없음 |

---

### 비동기 처리 구성요소(참고)

> 아래는 HTTP 엔드포인트가 아닌 내부 백그라운드 프로세스이며, 다른 서비스로의 내부 호출이 발생합니다.

| 구성요소 | 파일 | 동작 요약 | 외부호출 |
|---|---|---|---|
| Worker | worker.py | `booking.requests` 스트림 소비. pg_advisory_xact_lock(좌석 락) → 좌석 중복 확인 → 공연/좌석 조회 → 포인트 차감 → bookings INSERT(ON CONFLICT DO NOTHING) → 상태 CONFIRMED/FAILED 갱신 후 XACK. | event-service(공연/좌석 조회), payment-service(`X-Service-Token`으로 포인트 차감) |
| Dispatcher | dispatcher.py | `TICK_SECONDS`(기본 1초)마다 active-queues 각 큐에서 (`ADMISSION_RATE`×TICK, 기본 3/s)명을 Lua(DISPATCH_LUA: ZPOPMIN+XADD)로 work-stream에 핸드오프. 빈 큐는 SREM. | 없음(Redis) |
| Admission Worker | admission_worker.py | `work-stream`을 `admission-workers` 그룹으로 소비, 입장 토큰(`token:...`, TTL=ADMISSION_TOKEN_TTL) 발급 후 XACK. XAUTOCLAIM으로 idle 일감 회수(무유실). | 없음(Redis) |

> Worker가 FAILED로 갱신할 수 있는 사유: `SEAT_ALREADY_BOOKED`, `INSUFFICIENT_POINTS`, `PAYMENT_FAILED`, `WORKER_ERROR`.

---

## payment-service

사용자 포인트 잔액을 관리하고 예매 시 서비스 토큰 기반으로 포인트를 차감하며 결제 내역을 기록하는 결제(포인트) 서비스.

- 데이터베이스: payment_db (PostgreSQL, `postgresql+psycopg://postgres:postgres@postgres:5432/payment_db`) · 테이블: `point_balances`, `payment_history`
- 기본 잔액 자동 생성(ensure_balance): user_id에 'demo-rich' 포함 시 300000, 그 외 100000.

### 엔드포인트 요약

| 메서드 | 경로 | 인증 | 설명 | 내부전용 |
|---|---|---|---|---|
| GET | /health | none | 헬스체크 | - |
| GET | /payments/me/balance | JWT(current_user) | 포인트 잔액 조회 | - |
| GET | /payments/me/history | JWT(current_user) | 결제 내역 조회 | - |
| POST | /payments/deduct | X-Service-Token | 포인트 차감(결제 처리) | 내부 전용 |

---

### GET /health

| 항목 | 내용 |
|---|---|
| 인증 | none |
| 설명 | 헬스체크 |
| 요청 (path/query/body) | 없음 |
| 응답 | `{"status": "ok"}` |
| 에러코드 | 없음 |
| 접근 테이블 | 없음 |
| 외부호출 | 없음 |

---

### GET /payments/me/balance

| 항목 | 내용 |
|---|---|
| 인증 | JWT(current_user) |
| 설명 | 현재 사용자의 포인트 잔액 조회(레코드 없으면 기본 잔액으로 자동 생성). |
| 요청 - path | 없음 |
| 요청 - query | 없음 |
| 요청 - body | 없음 |
| 응답 | `{ "balance": int }` |
| 접근 테이블 | point_balances |
| 외부호출 | 없음 |

#### 에러코드

| HTTP | code | message |
|---|---|---|
| 401 | UNAUTHORIZED | 로그인이 필요한 기능입니다. |

---

### GET /payments/me/history

| 항목 | 내용 |
|---|---|
| 인증 | JWT(current_user) |
| 설명 | 현재 사용자의 결제(포인트 사용) 내역을 `paid_at` 내림차순으로 조회. |
| 요청 - path | 없음 |
| 요청 - query | 없음 |
| 요청 - body | 없음 |
| 응답 | `{ "items": [{ id, booking_request_id, booking_id, performance_title, amount, status, paid_at(ISO 문자열) }] }` |
| 접근 테이블 | payment_history |
| 외부호출 | 없음 |

#### 에러코드

| HTTP | code | message |
|---|---|---|
| 401 | UNAUTHORIZED | 로그인이 필요한 기능입니다. |

---

### POST /payments/deduct 〔내부 전용〕

> 내부 전용 엔드포인트. `X-Service-Token`으로 인증된 내부 서비스 호출만 허용합니다.

| 항목 | 내용 |
|---|---|
| 인증 | X-Service-Token |
| 설명 | 내부 서비스 호출로 포인트 차감 및 결제 기록. `booking_request_id` 단위 멱등 처리(이미 존재 시 기존 결제 재반환), `point_balances` 행 잠금(FOR UPDATE) 후 잔액 검증·차감, payment_history에 'PAID' 기록. |
| 요청 - path | 없음 |
| 요청 - query | 없음 |
| 요청 - header | `x-service-token` |
| 요청 - body | `DeductRequest { user_id: str, booking_request_id: str, booking_id: str, amount: int, performance_title: str }` |
| 응답 | `{ "payment_id": str, "balance_after": int }` (멱등 재호출 시 기존 payment_id와 현재 잔액) |
| 접근 테이블 | payment_history, point_balances |
| 외부호출 | 없음 |

#### 에러코드

| HTTP | code | message |
|---|---|---|
| 403 | FORBIDDEN | 요청 권한이 없습니다. |
| 409 | INSUFFICIENT_POINTS | 보유 포인트가 부족합니다. |

---

## saved-service

사용자별 공연 찜(저장) 목록을 Redis Set으로 관리하고, 저장된 공연 상세를 event-service에서 조회해 카드 형태로 반환하는 서비스.

- 데이터베이스: 없음(SQL DB 미사용, 영속 저장소는 Redis만 사용)
- Redis: 사용자별 찜 목록을 Redis Set에 저장. 키 형식 `saved:user:{user_id}` (sadd 추가, srem 삭제, smembers 조회). `REDIS_URL` 기본 `redis://redis:6379/0`, decode_responses=True.
- 카드 변환: `card()` 헬퍼가 event-service 상세 응답을 카드 스키마로 변환(`venue.name`→venue_name, `venue.province`→area).

### 엔드포인트 요약

| 메서드 | 경로 | 인증 | 설명 |
|---|---|---|---|
| GET | /health | none | 헬스 체크 |
| GET | /saved/me | JWT(current_user) | 찜한 공연 목록 조회 |
| POST | /saved/performances/{performance_id} | JWT(current_user) | 공연 찜 추가 |
| DELETE | /saved/performances/{performance_id} | JWT(current_user) | 공연 찜 삭제 |

---

### GET /health

| 항목 | 내용 |
|---|---|
| 인증 | none |
| 설명 | 헬스 체크 |
| 요청 (path/query/body) | 없음 |
| 응답 | `{"status": "ok"}` |
| 에러코드 | 없음 |
| 접근 테이블 | 없음 |
| 외부호출 | 없음 |

---

### GET /saved/me

| 항목 | 내용 |
|---|---|
| 인증 | JWT(current_user) |
| 설명 | 로그인 사용자가 찜한 공연 목록을 카드 형태로 반환. Redis Set의 ID를 (숫자면 정수 기준) 정렬 후 각 ID마다 event-service에서 상세 조회. 응답이 200이 아닌 ID는 결과에서 제외. |
| 요청 - path | 없음 |
| 요청 - query | 없음 |
| 요청 - body | 없음 |
| 응답 | `{ "items": [{ id, title, poster_url, venue_name, area, genre, start_date, end_date }, ...] }` |
| 접근 테이블 | 없음 (Redis 사용) |
| 외부호출 | event-service: `GET {EVENT_SERVICE_URL}/performances/{performance_id}` (찜한 각 ID별, httpx.Client timeout=5.0, 기본 `http://event-service:8000`) |

#### 에러코드

| HTTP | code | message |
|---|---|---|
| 401 | UNAUTHORIZED | 로그인이 필요한 기능입니다. (current_user 의존성) |

---

### POST /saved/performances/{performance_id}

| 항목 | 내용 |
|---|---|
| 인증 | JWT(current_user) |
| 설명 | 공연을 사용자 찜 목록(Redis Set `saved:user:{user_id}`)에 sadd로 추가. |
| 요청 - path | `performance_id` (str) |
| 요청 - query | 없음 |
| 요청 - body | 없음 |
| 응답 | `{ "performance_id": "<id>", "saved": true }` |
| 접근 테이블 | 없음 (Redis 사용) |
| 외부호출 | 없음 |

#### 에러코드

| HTTP | code | message |
|---|---|---|
| 401 | UNAUTHORIZED | 로그인이 필요한 기능입니다. (current_user 의존성) |

---

### DELETE /saved/performances/{performance_id}

| 항목 | 내용 |
|---|---|
| 인증 | JWT(current_user) |
| 설명 | 공연을 사용자 찜 목록(Redis Set)에서 srem으로 제거. |
| 요청 - path | `performance_id` (str) |
| 요청 - query | 없음 |
| 요청 - body | 없음 |
| 응답 | `{ "performance_id": "<id>", "saved": false }` |
| 접근 테이블 | 없음 (Redis 사용) |
| 외부호출 | 없음 |

#### 에러코드

| HTTP | code | message |
|---|---|---|
| 401 | UNAUTHORIZED | 로그인이 필요한 기능입니다. (current_user 의존성) |
