# ResourceQuota & LimitRange — Setup Report

> **작성일 / Date**: 2026-06-13
> **대상 네임스페이스 / Namespaces**: `backend`, `db`, `frontend` (compute quota) + `monitoring` (hygiene LimitRange only)
> **관련 매니페스트 / Files**: `booking/17-limit-ranges.yaml`, `booking/18-resource-quotas.yaml`, `monitoring/11-limit-range.yaml`

---

## 1. Why (배경)

이 클러스터는 플래시세일 티켓팅 앱을 4개 네임스페이스(`frontend`/`backend`/`db`/`monitoring`)에서 운영한다.
이번 작업 이전에는 **어떤 네임스페이스에도 `ResourceQuota`나 `LimitRange`가 없었다.**

그 상태의 위험:
- 한 네임스페이스의 폭주(예: `booking-worker` 메모리 누수, KEDA 오설정으로 인한 파드 폭증, 잘못된 PVC)가
  다른 네임스페이스를 자원 고갈로 몰아넣을 수 있다.
- 특히 장애를 **관측**해야 할 `monitoring`이나 데이터를 쥔 `db`가 굶으면 사고가 커진다.

**목표**: 각 네임스페이스에 공정한 몫을 보장하고 폭주의 폭발 반경을 제한하되,
**정상적인 오토스케일(플래시세일 중 KEDA/HPA 확장)은 절대 막지 않는다.**

---

## 2. What was deployed (적용 내용)

| 파일 | 종류 | 대상 |
|---|---|---|
| `booking/17-limit-ranges.yaml` | `LimitRange` ×3 | backend, db, frontend |
| `booking/18-resource-quotas.yaml` | `ResourceQuota` ×3 | backend, db, frontend |
| `monitoring/11-limit-range.yaml` | `LimitRange` ×1 | monitoring (위생용, 하드 캡 없음) |

### 2.1 ResourceQuota (compute only — cpu/memory)

| Namespace | requests.cpu | requests.memory | limits.cpu | limits.memory |
|---|---|---|---|---|
| `backend` | `4` | `6Gi` | `20` | `12Gi` |
| `db` | `1` | `2Gi` | `3` | `3Gi` |
| `frontend` | `1` | `1Gi` | `4` | `3Gi` |

> `monitoring`에는 하드 컴퓨트 쿼터를 두지 않았다 — 관측 스택을 너무 조이면 장애를 못 보게 되므로.

### 2.2 LimitRange (컨테이너 기본값 주입)

| Namespace | defaultRequest (cpu/mem) | default limit (cpu/mem) | 역할 |
|---|---|---|---|
| `backend` | 50m / 64Mi | 500m / 256Mi | 위생 백스톱 (서비스들은 이미 자체 값 보유) |
| `db` | 250m / 512Mi | 1000m / 1Gi | **postgres·redis가 resources 미선언 → 기본값 주입** |
| `frontend` | 50m / 64Mi | 300m / 256Mi | **frontend·cloudflared 미선언 → 기본값 주입** |
| `monitoring` | 50m / 64Mi | *(없음)* + `max` 4 / 8Gi | 위생용 — `default` limit 미설정으로 중량 파드 OOMKill 회피 |

---

## 3. How the numbers were chosen (산정 근거)

설계를 지배한 두 가지 제약:

### 제약 1 — 쿼터는 오토스케일 상한 "이상"이어야 한다
`requests.cpu/memory` 쿼터를 초과하면 다음 파드 생성이 admission 단계에서 **거부**된다.
쿼터가 KEDA max보다 낮으면 **플래시세일 도중 KEDA 스케일이 조용히 막히는** 최악의 상황이 발생한다.

그래서 `backend` 쿼터는 **풀 스케일아웃 + 롤링 서지 헤드룸**으로 산정:

```
backend 풀 스케일아웃 (04-app-services + 11-keda + 12-hpa 기준):
  requests 합계 = 3.2 vCPU / 4.22 Gi   (KEDA 8/8/6 + HPA 3/3 최대치)
  limits   합계 = ~16 vCPU / 8.44 Gi
→ 쿼터 = 4 vCPU / 6Gi (req), 20 vCPU / 12Gi (lim)   (~25% 헤드룸)
```

`limits.cpu`(20)는 물리 코어를 의도적으로 초과한다 — limits는 스케줄 예약이 아니라 상한일 뿐이며,
스케줄링에 실제로 잡히는 건 `requests`다.

### 제약 2 — 컴퓨트 쿼터는 모든 파드의 resources 선언을 강제한다
`db`(postgres·redis)와 `frontend`(frontend·cloudflared) 파드는 **resources를 전혀 선언하지 않았다.**
`LimitRange`로 기본값을 주입하지 않으면, 쿼터 적용 후 이들의 재기동/롤아웃이 거부된다
(`must specify requests.cpu`). 즉 **LimitRange는 선택이 아니라 필수 enabler**다.

> **Ambient 메시 이점**: 사이드카가 없으므로(ztunnel은 `istio-system`의 DaemonSet)
> 파드당 프록시가 쿼터에 잡히지 않는다. 네임스페이스 내 유일한 Istio 파드는
> `frontend`의 게이트웨이 Envoy 하나뿐(자체 resources 보유).

### 하드웨어 정합성 (capacity 검증)
산정값은 워커 VM의 실제 가용량에 대조해 검증했다:

| 계층 | 용량 |
|---|---|
| Proxmox 호스트 (물리) | `k8s` 31.25 GiB + `k8s2` 31.25 GiB = ~62.5 GiB |
| 워커 VM raw capacity (5×3 vCPU / 7GB) | 15 vCPU / ~35 GiB |
| **워커 VM allocatable (kubelet/OS 예약 후)** | **~12 vCPU / ~29.6 GiB** ← 실제 스케줄 가능 budget |

세 쿼터의 requests 합계 = backend 4 + db 1 + frontend 1 = **6 vCPU**.
→ 워커 12 vCPU 안에 여유 있게 들어가고, **워커 1대 손실 시(~9.6 vCPU)에도** 모니터링 포함 적재 가능. ✅

> ⚠️ 학습 메모: 진짜 한계로 튜닝하려면 capacity(15 vCPU)가 아니라 **allocatable(12 vCPU)** 기준으로 볼 것.

---

## 4. Rollout (배포 절차)

GitOps — ArgoCD가 `team6/manifest` repo의 `main`을 동기화한다.

1. **LimitRange 먼저** (`17-*`). LimitRange는 *신규 생성* 파드에만 적용 → 기존 러닝 파드는 무중단.
2. **ResourceQuota** (`18-*`).
3. 파일 번호 17 < 18 이므로 단일 ArgoCD sync에서 안전한 순서로 적용된다.

> resources 미선언 파드(db/frontend)는 기존 파드가 살아있는 동안은 0으로 카운트되며,
> **다음 재기동 시점**에 LimitRange 기본값을 받아 쿼터에 잡히기 시작한다.

---

## 5. Current status (현재 상태 — 2026-06-13 스냅샷)

ArgoCD sync 완료, 모든 객체 가동 중. 라이브 사용량:

| Namespace | requests (used / hard) | limits (used / hard) | 비고 |
|---|---|---|---|
| `backend` | cpu 950m/4, mem 1280Mi/6Gi | cpu 4700m/20, mem 2560Mi/12Gi | 평시(min replica) ~24% 사용. 세일 시 확장 여유 충분 |
| `db` | cpu 250m/1, mem 512Mi/2Gi | cpu 1/3, mem 1Gi/3Gi | 재기동된 1개 파드가 기본값 받아 카운트 시작됨 |
| `frontend` | cpu 100m/1, mem 128Mi/1Gi | cpu 2/4, mem 1Gi/3Gi | 게이트웨이 Envoy만 카운트 (나머지는 재기동 전) |
| `monitoring` | — (쿼터 없음) | — | `monitoring-hygiene` LimitRange만 존재 |

모든 모니터링 파드는 이미 자체 requests/limits를 선언 → 위생 LimitRange는 현재 아무것도 바꾸지 않음(안전).

---

## 6. Verification (검증 방법)

```bash
# 쿼터 사용량 vs 한도
kubectl -n backend  get resourcequota backend-compute
kubectl -n db       get resourcequota db-compute
kubectl -n frontend get resourcequota frontend-compute

# 미선언 파드가 기본값을 받는지 (재기동 후 확인)
kubectl -n db get pod -l app=redis -o jsonpath='{.items[0].spec.containers[0].resources}'; echo

# ★ 핵심: 피크 부하에서 쿼터가 KEDA를 막지 않는지
#   부하 후 quota 거부 이벤트가 비어 있어야 함
kubectl -n backend get events --field-selector reason=FailedCreate | grep -i quota   # expect: empty
kubectl -n backend get deploy event-service booking-api booking-worker
```

합격 기준: 피크에서도 세 쿼터 모두 한도 미만, KEDA가 상한(8/8/6)까지 도달하면서 quota 거부 없음,
db/frontend 파드가 주입된 기본 resources를 표시.

---

## 7. Open items (남은 확인 사항)

- [ ] **미선언 파드 카운트**: db/frontend의 기존 파드는 재기동 시 사용량이 약간 상승한다(여전히 한도 내). db는 이미 1개 반영됨.
- [ ] **ArgoCD App path**: `booking/`·`monitoring/` 디렉터리를 watch하는지 확인 (적용된 걸로 보아 정상 작동 중).
- [ ] **튜닝 후속**: 첫 실세일 후 실제 사용량 baseline이 나오면 헤드룸을 재조정.
- [ ] (선택) storage/object-count 쿼터는 이번 범위에서 제외 — 필요 시 추가.
