# 배포 전략 (Deployment Strategy)

## 개요

배포 전략과 스케일링 전략은 별개의 개념입니다.

| 구분 | 목적 | 관련 설정 |
|------|------|----------|
| **배포 전략** | 새 버전 코드를 어떻게 교체하는가 | `Deployment.spec.strategy` |
| **스케일링 전략** | 트래픽에 따라 replica를 어떻게 조절하는가 | KEDA, HPA, 수동 scale |

티켓팅 오픈 전 replica 증가, KEDA 자동 확장은 스케일링 전략이며 배포 전략과 무관합니다.

---

## 서비스별 배포 전략

| 서비스 | 전략 | 이유 |
|--------|------|------|
| **booking-api** | Blue/Green | 결제 흐름 중 즉시 롤백 필요, 신버전 검증 후 트래픽 전환 |
| **payment-service** | Blue/Green | 결제 버그 발생 시 환불 이슈로 직결 |
| **event-service** | RollingUpdate | Read-heavy (조회 전용), 버전 혼재 무방 |
| **auth-service** | RollingUpdate | Stateless JWT 방식, 어느 파드가 처리해도 동일 |
| **saved-service** | RollingUpdate | 찜하기 기능, 금전적 피해 없음, 버전 혼재 무방 |
| **queue-dispatcher** | RollingUpdate | Redis SortedSet 원자적 연산으로 중복 처리 불가 |
| **booking-worker** | Recreate | Redis Streams Queue consumer, 중복 처리 방지 |
| **admission-worker** | Recreate | Redis Streams Queue consumer, 중복 처리 방지 |
| **frontend** | RollingUpdate | Stateless, 버전 혼재 무방 (시연 시 Blue/Green으로 임시 전환) |

---

## RollingUpdate 설정

기본값(25%)은 replica 수에 따라 실제 숫자가 달라져 예측이 어렵습니다.
명시적으로 고정값을 설정합니다.

```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 1        # 배포 중 replica보다 1개 더 허용
    maxUnavailable: 0  # 신버전이 Ready 되기 전까지 구버전 유지
```

**동작 흐름 (replica=1 기준):**
```
[v1] 실행 중
  → [v1][v2-시작] (maxSurge:1 허용)
  → [v1][v2-Ready]
  → [v2] (v1 종료)
```
`maxUnavailable: 0`은 신버전이 Ready 되기 전까지 구버전을 절대 종료하지 않습니다.
신버전이 먼저 올라오고, 이후 구버전이 내려가는 방식입니다.

**적용 대상:** event-service, auth-service, saved-service, queue-dispatcher, frontend

---

## Blue/Green 설정

### 동작 흐름

```
1. v1 Deployment 실행 중 → 실 트래픽 100%
2. v2 Deployment 배포   → 트래픽 0% (Service에 연결 안 됨)
3. v2 내부 검증         → port-forward로 직접 테스트
4. Service selector 변경 → 트래픽 v2로 100% 즉시 전환
5. 이상 없으면 v1 종료  → 배포 완료
   이상 있으면 v1 복귀  → selector 변경으로 즉시 롤백
```

### 핵심 장점

- 신버전을 실 트래픽 없이 먼저 검증 가능
- v1 파드가 살아있어 롤백이 수초 내 가능 (파드 재시작 불필요)
- RollingUpdate와 달리 v1/v2 혼재 구간 없음

### 시연 명령어 (frontend 기준 — 시연용 Blue/Green)

```bash
# [1단계] v1, v2 파드 동시 실행 확인
kubectl get pods -n frontend --show-labels | grep frontend

# [2단계] Service가 v1 바라보는지 확인
kubectl get svc frontend -n frontend -o jsonpath='{.spec.selector}'

# [3단계] v2 파드 사전 검증 (실 트래픽 영향 없음)
kubectl port-forward deployment/frontend-v2 8080:5173 -n frontend
# → 브라우저 localhost:8080 에서 v2 UI 확인 후 Ctrl+C

# [4단계] Endpoint 실시간 감시 (별도 터미널)
kubectl get endpoints frontend -n frontend -w

# [5단계] v2로 트래픽 전환 + 소요시간 측정
START=$(date +%s) && \
kubectl patch service frontend -n frontend \
  -p '{"spec":{"selector":{"app":"frontend","version":"v2"}}}' && \
END=$(date +%s) && echo "전환 소요시간: $((END-START))초"

# [6단계] v1 롤백 + 소요시간 측정
START=$(date +%s) && \
kubectl patch service frontend -n frontend \
  -p '{"spec":{"selector":{"app":"frontend","version":"v1"}}}' && \
END=$(date +%s) && echo "롤백 소요시간: $((END-START))초"
```

### 시연 manifest 구성 (frontend)

| 파일 | 내용 |
|------|------|
| `booking/05-frontend.yaml` | v1 Deployment (image: 7ebd7bdb) + Service (selector: version=v1) |
| `booking/05-frontend-v2.yaml` | v2 Deployment (image: 193164c5, 헤더 텍스트 변경) |

**적용 대상:** booking-api, payment-service (운영), frontend (시연 한정)

---

## Recreate 설정

```yaml
strategy:
  type: Recreate
```

### 동작 흐름

```
구버전 파드 전부 종료 (SIGTERM → 완전 종료 대기)
          ↓
신버전 파드 시작
```

### Recreate를 사용하는 이유

booking-worker, admission-worker는 Redis Streams XREADGROUP 방식으로 동작합니다.

```
RollingUpdate 중 위험 시나리오:
  v1-worker가 메시지 A 처리 중 (XACK 미전송)
  v2-worker도 동일 메시지 A 재처리 시도 (pending 상태이므로)
  → 이중 결제 / 이중 좌석 배정 위험
```

Recreate는 구버전과 신버전이 동시에 실행되는 구간이 없어 중복 처리를 방지합니다.

### Graceful Shutdown 설정 (필수)

Recreate 자체는 "현재 작업 완료 후 종료"를 보장하지 않습니다.
앱 코드의 SIGTERM 처리와 아래 설정이 함께 필요합니다.

```yaml
spec:
  template:
    spec:
      terminationGracePeriodSeconds: 60  # SIGTERM 후 60초 여유
```

**적용 대상:** booking-worker, admission-worker

---

## 멱등성 (Idempotency)

Recreate 전략을 사용해도, 파드 종료 시점(DB 업데이트 후 XACK 전)에 따라
재처리가 발생할 수 있습니다.

```
메시지 처리 중 파드 종료 케이스:
  결제 차감 완료 → 파드 종료 → XACK 미전송
  새 worker가 동일 메시지 재처리 시도
  → request_id로 기존 처리 여부 확인 후 XACK만 전송
```

각 워커는 `request_id` 기반으로 이미 처리된 메시지를 건너뛰도록 구현합니다.

---

## readinessProbe (향후 과제)

파드가 Ready 상태가 된 후 실제로 요청을 처리할 수 있는지 확인하는 설정입니다.

```yaml
readinessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
```

**현재 미적용 이유:** 각 서비스에 `/health` 엔드포인트가 구현되어 있지 않아 보류.
적용 시 probe 실패로 파드가 영원히 NotReady 상태가 됩니다.

**적용 우선순위 (구현 후):**

| 서비스 | 필요도 | 이유 |
|--------|--------|------|
| auth-service | 높음 | DB 연결 실패 시 로그인 전체 불가 |
| booking-api | 높음 | DB + Redis 동시 의존, 예매 진입점 |
| payment-service | 높음 | 결제 DB 연결 확인 중요 |
| event-service | 높음 | 공연 조회 DB 연결 |
| saved-service | 낮음 | 찜 기능, 저위험 |
| queue-dispatcher | 낮음 | HTTP 요청 직접 안 받음 |
| frontend | 낮음 | 단순 파일 서빙 |
| booking-worker | 불필요 | HTTP 서버 아님, Recreate 전략 사용 |
| admission-worker | 불필요 | HTTP 서버 아님, Recreate 전략 사용 |

---

## 배포 타이밍

도구로 강제하기보다 팀 운영 규칙으로 관리합니다.

- 티켓팅 오픈 전후 각 2시간은 배포 금지
- 배포 전 다음 티켓팅 일정 확인 필수
- booking-worker, admission-worker는 대기열이 비어있는 시점에 배포

---

## 전략 비교 요약

| | Recreate | RollingUpdate | Blue/Green |
|---|---|---|---|
| 다운타임 | 있음 | 없음 | 없음 |
| 롤백 속도 | 느림 | 보통 (30초~1분) | 빠름 (수초) |
| 구버전/신버전 혼재 | 없음 | 있음 (일시적) | 없음 |
| 신버전 사전 검증 | 불가 | 불가 | 가능 |
| 리소스 | 절약 | 보통 | 2배 (일시적) |
