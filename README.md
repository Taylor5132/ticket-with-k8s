# Booking Ticket Platform

한국어 공연 예매 데모 플랫폼. 플래시 세일(티켓팅) 트래픽을 견디는 것을 목표로 설계된 MSA 구조다.

- **프론트엔드**: React + Vite (`apps/frontend`)
- **백엔드**: FastAPI 마이크로서비스 5종 + 비동기 워커 (`services/`)
  - auth(인증/JWT) · event(공연 메타데이터) · saved(관심공연) · booking(좌석/대기열/예매 + worker) · payment(포인트 결제)
- **데이터**: PostgreSQL(단일 인스턴스, 서비스별 DB 4개) + Redis(캐시 + Streams 예매 큐 + 대기열 ZSET)
- **배치**: KOPIS 공연 데이터 일일 동기화 (`cron/`)
- **운영**: 온프레미스 K8s 클러스터 (Istio ambient + Gateway API + Cilium), ArgoCD GitOps

## 빠른 시작 (로컬)

```bash
docker compose up --build       # Harbor(192.168.0.237) 접근 가능 환경 필요
# frontend: http://localhost:5173
```

상세 절차·체크는 [docs/ops/PROTOTYPE_RUNBOOK.md](docs/ops/PROTOTYPE_RUNBOOK.md).

## 배포 구조 (요약)

```
사용자 → Cloudflare Tunnel → cloudflared → Istio Gateway(booking-gw) → 서비스들
코드 push → GitLab CI(빌드→Trivy→manifest 갱신) → ArgoCD → K8s
```

K8s 매니페스트는 이 repo가 아니라 **GitLab `team6/manifest` repo**에 있다.

## 문서 인덱스

| 위치 | 성격 | 내용 |
|---|---|---|
| [docs/reference/](docs/reference/) | **살아있는 스펙** — 코드 변경 시 함께 갱신 | API 계약, DB/Redis 스키마, 도메인 용어, UI 카피 |
| [docs/ops/](docs/ops/) | 인프라·운영 | K8s 스택 설계/현황, CI/CD, 로컬 런북 |
| [docs/planning/](docs/planning/) | 역사적 계획 (현행화 주석 포함) | 최초 빌드 계획, 인프라 계획, 수용 체크리스트 |
| [docs/adr/](docs/adr/) | 아키텍처 결정 기록 | ADR-0001~0007 |
| [cron/README.md](cron/README.md) | 배치 가이드 | KOPIS 동기화 실행/배포 |
| [load-test/](load-test/) | 부하테스트 | k6 시나리오 |
| [AGENTS.md](AGENTS.md) | **AI/신규 인원 유지보수 가이드** | 문서 동기화 규칙, 함정 목록 |

## 유지보수

이 repo를 처음 보는 사람(또는 AI)은 **[AGENTS.md](AGENTS.md)부터 읽을 것.** 문서 수정 규칙과 알려진 함정이 정리돼 있다.
