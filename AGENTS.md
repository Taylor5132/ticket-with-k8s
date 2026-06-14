# AGENTS.md — AI/신규 인원 유지보수 가이드

> 이 문서는 **이 repo의 맥락이 전혀 없는 AI 에이전트(또는 신규 팀원)** 가 안전하게 유지보수할 수 있도록 작성됐다.
> 작업 전 이 문서 전체를 읽을 것. 마지막 검증일: 2026-06-12 (문서 전수를 실코드와 대조 완료한 시점).

## 1. 이 프로젝트가 무엇인가

한국어 공연 예매(티켓팅) 데모. 핵심 설계 문제는 **플래시 세일 폭주 트래픽**이다 — 예매는 동기 처리하지 않고, booking-api가 접수만 받아 Redis Stream에 넣고 booking-worker가 백그라운드에서 처리한다 (한 좌석·한 날짜에 한 명만 성공해야 함).

- 코드는 이 repo(모노레포), **K8s 매니페스트는 별도 repo `team6/manifest`** (GitLab `192.168.0.237:8443`, ArgoCD가 동기화). 이 분리는 ADR-0004 보정 참조.
- 실서비스는 온프레미스 K8s 클러스터에서 돈다 (네임스페이스: `frontend`/`backend`/`db`/`monitoring`/`argocd`). 이 repo만 보고 클러스터 상태를 단정하지 말 것.
- 이미지 레지스트리는 사설 Harbor(`192.168.0.237`, self-signed TLS).

## 2. 디렉토리 지도

| 경로 | 내용 | 수정 빈도 |
|---|---|---|
| `services/<name>/app/` | FastAPI 서비스 5종. booking-service는 `main.py`(API)와 `worker.py`(스트림 소비자)가 한 코드베이스 | 높음 |
| `apps/frontend/src/` | React UI. `api.ts`가 자체 fetch 헬퍼 (TanStack Query는 설치만 됨) | 높음 |
| `cron/` | KOPIS 일일 동기화 배치 (가이드: `cron/README.md`) | 낮음 |
| `infra/docker-compose/postgres/init/` | DB 초기화 SQL 4파일 — **스키마의 단일 진실 공급원** | 낮음 |
| `docs/reference/` | 살아있는 스펙 — 코드와 동기화 의무 (아래 §4) | 코드 따라감 |
| `docs/ops/` | K8s/CI/런북 | 인프라 변경 시 |
| `docs/planning/` | 역사적 계획 — "당시 계획 + 현행화 주석" 형식 유지 | 거의 없음 |
| `docs/adr/` | 결정 기록 — **본문 재작성 금지** (아래 §5) | 결정 변경 시만 |
| `load-test/` | k6 부하테스트 시나리오 | 테스트 시 |
| `.gitlab-ci.yml` | build → scan(Trivy) → update-manifest 3스테이지 | 신중히 |

## 3. 절대 규칙

1. **삭제는 인간의 승인 없이 하지 말 것.** 폐기된 계획처럼 보여도 미래 계획일 수 있다. 폐기 표시가 필요하면 삭제 대신 ~~취소선~~ + 사유 주석.
2. **미구현 계획을 "구현됨"처럼 쓰지 말 것.** 반대도 마찬가지. 확신이 없으면 코드를 grep해서 확인한 뒤 쓴다.
3. 문서에 **실제 비밀값(API 키, 토큰, 비밀번호)을 절대 커밋하지 말 것.** 예시는 `<발급받은 키>` 형식으로.
4. 클러스터 상태에 대한 주장은 이 repo만으로 검증 불가 — "repo 기준" / "클러스터 기준(날짜)"을 구분해 적는다.

## 4. 코드 ↔ 문서 동기화 맵 (코드를 바꾸면 여기를 고쳐라)

| 코드 변경 | 갱신할 문서 |
|---|---|
| 엔드포인트/요청·응답 형태 (`services/*/app/main.py`) | `docs/reference/API_CONTRACTS.md` |
| DB 테이블/컬럼/제약 (`infra/.../init/*.sql`, 런타임 ALTER) | `docs/reference/DB_SCHEMA.md` |
| Redis 키/스트림/필드 | `docs/reference/DB_SCHEMA.md` (Redis 절) |
| 화면 문구/버튼/신규 화면 (`apps/frontend/src`) | `docs/reference/UI_COPY.md` |
| 도메인 개념 추가/변경 | `docs/reference/CONTEXT.md` (용어 사전) |
| K8s/메시/스토리지/관측 구성 | `docs/ops/K8S_STACK.md` |
| 네임스페이스 ResourceQuota/LimitRange (manifest repo `booking/17~18`, `monitoring/11`) | `docs/ops/QUOTA_LIMITS_REPORT.md` |
| `.gitlab-ci.yml` 스테이지/잡 | `docs/ops/CICD_PLAN.md` |
| 로컬 실행 절차/포트 | `docs/ops/PROTOTYPE_RUNBOOK.md` |
| `cron/` 스크립트 동작 | `cron/README.md` |

문서 수정 컨벤션: 사실이 바뀌면 본문을 직접 고치고, 큰 방향 전환이면 `> **YYYY-MM-DD 현행화/보정**:` 블록인용을 붙인다. 미착수 계획은 `(예정)` 표기.

## 5. ADR 규칙

ADR(`docs/adr/`)은 "그때 왜 그렇게 결정했나"의 기록이다. **기존 ADR 본문을 고쳐 쓰지 말 것.** 결정이 바뀌면 ① 새 ADR을 추가하고 구 ADR에 `status: superseded by ADR-XXXX`를 달거나(예: 0005→0006), ② 부분 변경이면 말미에 `> **보정**:` 블록인용만 추가한다 (예: 0003, 0004, 0007).

## 6. 함정 목록 (실제로 겪은 것들 — 시간 절약용)

1. **seat-availability 라우팅**: `/api/performances/{id}/seat-availability`는 event-service가 아니라 **booking-api**로 가야 한다. Gateway API는 regex 캡처 재작성이 불가해 **Istio EnvoyFilter**로 해결돼 있다 (manifest repo). 이 라우트가 404면 십중팔구 EnvoyFilter 누락.
2. **ambient 메시 + NetworkPolicy**: 파드 간 트래픽은 원래 포트가 아니라 **HBONE 15008/TCP**로 도착한다. 포트를 제한하는 NetworkPolicy에는 반드시 15008을 추가할 것. 증상: 영문 모를 connection timeout, ztunnel 로그에 "NetworkPolicy is blocking HBONE port 15008".
3. **cron 이미지 실행 명령**: 의존성이 uv venv(`/app/.venv`)에 있어서 컨테이너에서 맨 `python`은 ModuleNotFoundError. 반드시 `uv run python ...`.
4. **show_date는 어디에나 있다**: 예매 요청·스트림 메시지·bookings UNIQUE 제약·seat-availability 쿼리 전부 날짜 차원 포함. 이걸 빼먹으면 422/404.
5. **에러 응답 형태**: FastAPI라 `{"detail": {"code", "message"}}` 이중 구조다. 평면 `{"code","message"}`로 파싱하면 깨진다.
6. **frontend는 nginx 정적 서빙**(prod 빌드)이다 — 과거 Vite dev 서버에서 전환됨(멀티스테이지 Dockerfile, 메모리 ~512Mi→~30Mi, OOM 해소). 주의점: ① React Router(BrowserRouter) 딥링크·새로고침 404 방지를 위해 `apps/frontend/nginx.conf`의 `try_files ... /index.html` SPA fallback이 **필수**. ② `VITE_*`는 **빌드 타임**에 번들에 박힌다 — 런타임 env로 못 바꾼다(예: `VITE_GOOGLE_OAUTH_ENABLED`는 Docker `--build-arg`, 기본 true). ③ 게이트웨이의 Host→localhost 재작성은 Vite용이었어 이제 불필요(`booking/06-gateway.yaml`의 `/` 라우트에서 제거 가능). 클러스터에서 `/api/*`는 게이트웨이가 처리하므로 nginx는 정적 파일만 서빙한다(Vite 프록시 미사용).
7. **Harbor self-signed**: 모든 Dockerfile 베이스 이미지가 Harbor를 가리킨다. 로컬 빌드는 Harbor 접근 + 인증서 신뢰(또는 containerd skip_verify)가 전제.
8. **부하테스트 계정 포인트**: dev-login 신규 계정은 100,000P라 VIP석(150,000P) 예매는 INSUFFICIENT_POINTS로 실패한다. 의도된 검증이 아니라면 demo-rich(300,000P)를 쓸 것.
9. **티켓팅 불변식**: 한 (공연, 날짜, 좌석)에 CONFIRMED는 1건만. 부하테스트 후 `SELECT ... GROUP BY ... HAVING COUNT(*)>1`이 0행인지 확인 (쿼리는 `docs/ops/K8S_STACK.md`의 k6 절).

## 7. 알려진 미해결 이슈 (2026-06-12 기준)

- [ ] `apps/frontend/src/App.tsx` 상단바 브랜드가 `티켓랩123` (테스트 흔적, `티켓랩`이 맞음)
- [ ] `cron/daily_update_data.py` 모듈 docstring이 자기 코드와 불일치 (수집 범위 -30d 표기, 키 기본값 언급)
- [ ] `apps/frontend/src/api.ts`에 네트워크 실패 catch 없음 — UI_COPY의 "서버와 연결할 수 없습니다..." 카피 미구현
- [ ] KOPIS API 키가 git 히스토리에 노출된 적 있음 → 키 재발급 권장 (작업 트리는 마스킹 완료)
- [ ] 구 `booking` 네임스페이스 폐기 후 `.gitlab-ci.yml`의 sed 경로(`booking/*.yaml`)와 ArgoCD App Path 갱신 필요

## 8. 검증 치트시트

```bash
# 엔드포인트 목록 ↔ API_CONTRACTS.md 대조
grep -rn "@app\." services/*/app/main.py

# 스키마의 진실 ↔ DB_SCHEMA.md 대조
cat infra/docker-compose/postgres/init/005_service_schemas.sql

# UI 문구 ↔ UI_COPY.md 대조
grep -rn "버튼문구" apps/frontend/src --include="*.tsx"

# 로컬 스모크 (show_date 필수!)
curl "http://localhost:8004/performances/1/seat-availability?show_date=2026-07-01"
```
