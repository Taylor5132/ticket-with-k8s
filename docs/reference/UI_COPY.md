# Korean UI Copy

> **2026-06-12 현행화**: 코드와 대조해 갱신. 회원가입 탭·날짜 선택·대기열 화면의 카피를 추가했고, 변경된 버튼 문구를 반영했다. ⚠ 코드 측 이슈: App.tsx 상단바 브랜드가 `티켓랩123`으로 돼 있음(테스트 흔적으로 추정 — 코드 수정 필요, 문서 기준은 `티켓랩`).

## Navigation

- Brand placeholder: `티켓랩`
- Main nav: `공연`
- My Page nav: `마이페이지`
- Login: `로그인`
- Logout: `로그아웃`

## Login

- Page title: `로그인` (dedicated `/login` page)
- ID field label: `아이디` / placeholder: `아이디를 입력해 주세요`
- Password field label: `비밀번호` / placeholder: `비밀번호를 입력해 주세요`
- Submit button: `로그인`
- Divider: `또는`
- Google-style button: `Google로 시작하기`
- Demo helper title: `데모 계정으로 체험해 보세요`
- Demo helper note: `데모 환경에서는 비밀번호 검증 없이 아이디 기준으로 로그인됩니다.`
- Basic user 칩: `demo-basic` + `100,000P` (구 문구 `기본 데모 사용자`는 display_name으로만 사용)
- Rich user 칩: `demo-rich` + `300,000P` (구 문구 `포인트 많은 데모 사용자`는 display_name으로만 사용)
- Missing ID error: `아이디를 입력해 주세요.`
- Missing password error: `비밀번호를 입력해 주세요.`

## Signup (회원가입 탭 — 2026-06 추가)

- Tab: `회원가입` / `로그인` 전환 탭
- ID placeholder: `4~20자 영문·숫자·밑줄`
- Password placeholder: `8자 이상`
- Nickname field: `닉네임`
- Welcome line: `가입 즉시 10만 포인트를 드립니다 🎉`
- Validation errors: 형식 불일치 시 각 필드 규칙 문구 표시

## Dashboard

- Page title: `공연`
- Section: `오픈 예정`
- 필터 사이드바: `필터` / 그룹 `장르`·`지역` / `전체` / `초기화` (구성 개편 — 구 `공연 목록`/`장르별 보기`/`지역별 보기` 섹션은 필터 방식으로 대체됨)
- 그리드 제목: `전체 공연` 또는 `{필터} 공연`
- 배너 버튼: `자세히 보기`
- Empty state: `표시할 공연이 없습니다.`

## Performance Detail

- Tab: `상세정보`
- Tab: `좌석/가격`
- Tab: `관람안내`
- Save button: `관심공연`
- Saved button: `관심공연 저장됨` (구: `관심공연 해제`)
- 날짜 선택: `날짜 선택` 칩 피커 (2026-06 추가)
- Booking button: `예매하기` / 날짜 미선택 시: `날짜를 선택해 주세요`
- Price label: `공식 가격 안내:` + 등급/가격 표 (구: `가격 안내`)
- Runtime label: `공연 시간`
- Age rating label: `관람 연령`
- Venue label: `공연장`
- Period label: `공연 기간`
- Guidance empty state: `등록된 관람 안내가 없습니다.`

## Queue Waiting (대기열 화면 — 2026-06 추가)

- 대기 순번: `나의 대기순서`
- 안내: `현재 접속 인원이 많아 대기중입니다...`
- 경고: 새로고침 시 순번 유지 관련 안내 문구

## Seat Selection

- Page title: `좌석 선택`
- 좌석 등급 범례: 등급별 가격 표시 (구 `선택 가능` 라벨은 범례로 대체됨)
- Occupied label: `예매 완료`
- Selected label: `선택한 좌석`
- No selected seat: `좌석을 선택해 주세요.`
- Payment button: `결제하기`
- Back button: `공연 상세로 돌아가기`

## Booking Processing

- Processing title: `예매 요청 처리 중입니다`
- Processing body: `좌석과 포인트를 확인하고 있습니다. 잠시만 기다려 주세요.`
- Success title: `예매가 완료되었습니다`
- Success body: `마이페이지에서 예매내역과 결제내역을 확인할 수 있습니다.`
- Failure title: `예매에 실패했습니다`
- 멀티 좌석 variant: `N석 모두 예매가 완료되었습니다.` / `일부 예매에 실패했습니다` (2026-06 추가)
- 버튼: `마이페이지에서 확인` / `공연 목록으로` (구 `좌석 다시 선택하기`/`마이페이지로 이동`은 코드에서 제거됨)

## Booking Failure Messages

- `SEAT_ALREADY_BOOKED`: `이미 예매된 좌석입니다. 다른 좌석을 선택해 주세요.`
- `INSUFFICIENT_POINTS`: `보유 포인트가 부족합니다. 다른 좌석을 선택하거나 포인트가 많은 데모 사용자로 로그인해 주세요.`
- `PAYMENT_FAILED`: `결제 처리 중 문제가 발생했습니다. 잠시 후 다시 시도해 주세요.`
- `WORKER_ERROR`: `예매 처리 중 문제가 발생했습니다. 잠시 후 다시 시도해 주세요.`
- Unknown: `알 수 없는 문제로 예매에 실패했습니다.`

## My Page

- Page title: `마이페이지`
- 프로필 스트립: 표시명 + provider 라벨 (구 `내 정보` 제목 없이 무제 영역으로 변경)
- 라벨: `보유 포인트` (프로필 스트립 내부)
- Section: `예매내역`
- Section: `최근 결제내역`
- Section: `관심공연`
- Empty bookings: `아직 예매내역이 없습니다.`
- Empty payments: `아직 결제내역이 없습니다.`
- Empty saved performances: `아직 관심공연이 없습니다.`
- Provider dev: `데모`
- Provider kakao: `카카오`
- Provider google: `Google`

## Generic Errors

- Login required: `로그인이 필요한 기능입니다.`
- Network error: `서버와 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.` — ⚠ 미구현 (api.ts에 fetch 실패 catch가 없어 현재는 raw TypeError 노출; 이 카피로 구현 예정)
- Not found: `요청한 정보를 찾을 수 없습니다.`
- Unexpected error: `문제가 발생했습니다. 잠시 후 다시 시도해 주세요.`
