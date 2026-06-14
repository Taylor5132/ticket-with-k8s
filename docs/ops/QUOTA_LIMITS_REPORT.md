# ResourceQuota & LimitRange — Setup Report

> **작성일 / Date**: 2026-06-13 (updated 2026-06-14 — ephemeral-storage 추가)
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

### 2.1 ResourceQuota (compute + ephemeral-storage)

| Namespace | requests.cpu | requests.memory | requests.ephemeral-storage | limits.cpu | limits.memory |
|---|---|---|---|---|---|
| `backend` | `4` | `6Gi` | `8Gi` | `20` | `12Gi` |
| `db` | `1` | `2Gi` | — | `3` | `3Gi` |
| `frontend` | `1` | `1Gi` | — | `4` | `3Gi` |

> `monitoring`에는 하드 컴퓨트 쿼터를 두지 않았다 — 관측 스택을 너무 조이면 장애를 못 보게 되므로.
> `requests.ephemeral-storage`는 폭주가 KEDA로 증폭되는 `backend`에만 두었다. `db`/`frontend`는 파드 수가
> 고정이고 작아 쿼터 가치가 낮다 — LimitRange의 ephemeral 기본값으로 노드 보호는 동일하게 적용된다.

### 2.2 LimitRange (컨테이너 기본값 주입)

| Namespace | defaultRequest (cpu/mem/ephem) | default limit (cpu/mem/ephem) | 역할 |
|---|---|---|---|
| `backend` | 50m / 64Mi / 128Mi | 500m / 256Mi / 1Gi | 위생 백스톱 (서비스들은 cpu/mem 자체 값 보유, **ephemeral 은 전부 미선언 → 36파드 주입**) |
| `db` | 250m / 512Mi / 256Mi | 1000m / 1Gi / 2Gi | **postgres·redis가 resources 미선언 → 기본값 주입** (temp_file 대비 ephem 넉넉) |
| `frontend` | 50m / 64Mi / 128Mi | 300m / 256Mi / 512Mi | **frontend·cloudflared 미선언 → 기본값 주입** |
| `monitoring` | 50m / 64Mi | *(없음)* + `max` 4 / 8Gi | 위생용 — `default` limit 미설정으로 중량 파드 OOMKill 회피 (ephem 미적용, §7 참고) |

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
- [x] **storage/object-count 쿼터 결정 (2026-06-14)** — §8 참고. ephemeral-storage 추가, PVC/object 쿼터는 근거 있게 제외.

---

## 8. Storage / object-count 결정 (2026-06-14)

§7의 마지막 open item("storage/object-count 쿼터")을 검토하고 결론냈다.

### 8.1 ephemeral-storage limits — **추가함 ✅**
실제 스토리지 리스크는 PVC가 아니라 **노드 로컬 ephemeral 디스크**(컨테이너 쓰기 레이어 +
stdout 로그 + emptyDir)다. 기존 LimitRange/Quota는 cpu·memory만 제한해 이 축이 무방비였다.

- 플래시세일 중 KEDA가 backend를 8/8/6으로 확장 + Loki로 로그가 쏟아질 때, 로그/임시파일을
  마구 쓰는 파드 하나가 워커를 **DiskPressure → 파드 축출(피크 시점!)** 로 몰 수 있다.
  이를 막는 레버는 ephemeral-storage request/limit 뿐.
- 적용: `17-limit-ranges.yaml`의 세 LimitRange에 `ephemeral-storage` defaultRequest/default 추가
  (backend 128Mi/1Gi, db 256Mi/2Gi, frontend 128Mi/512Mi).
- `18-resource-quotas.yaml`의 backend 쿼터에 `requests.ephemeral-storage: 8Gi` 추가
  (36파드 ceiling × 128Mi ≈ 4.5Gi + 서지/CronJob 헤드룸). **cpu/memory와 동일하게 쿼터는
  오토스케일 상한 이상** — 낮으면 세일 중 KEDA가 ephemeral 쿼터에서 조용히 막힌다.

### 8.2 PVC storage 쿼터(`requests.storage`/`persistentvolumeclaims`) — **제외 (의도적)**
클러스터의 모든 StorageClass가 `kubernetes.io/no-provisioner`(`booking/00-storage.yaml`)다.
PVC가 스스로 볼륨을 만들 수 없고, 관리자가 미리 만든(GitOps 추적) PV에만 바인딩된다.
→ 스토리지 쿼터가 막으려는 "동적 무한 프로비저닝" 시나리오가 **구조적으로 발생 불가**.
PVC-count 캡이 주는 건 잘못 만든 PVC의 admission 거부(메시지 약간 명확)뿐 — 가치 낮아 생략.

### 8.3 object-count 쿼터(`count/pods`, `count/secrets` 등) — **제외 (저우선)**
- 동기였던 "KEDA 오설정 파드 폭증"은 **이미 compute 쿼터가 차단**한다(`requests.cpu/memory`
  소진 시 추가 파드 스케줄 불가). 게다가 LimitRange가 모든 컨테이너에 `defaultRequest`를
  주입하므로 compute 회계를 빠져나가는 zero-request 파드가 없다 → `count/pods`는 사실상 중복.
- Job/Pod 누적은 이미 제어됨: kopis CronJob들이 `successfulJobsHistoryLimit:1` /
  `failedJobsHistoryLimit:1` + `concurrencyPolicy: Forbid`(`booking/13-kopis-cronjob.yaml`).
- Secret/ConfigMap 누적(SealedSecrets+ArgoCD+Helm)은 이론상 가능하나 이 랩 규모에선 etcd
  압박 무의미. → 필요해지면 그때 `count/pods` 트립와이어 정도만 추가.

### 8.4 monitoring ephemeral — **추가함 ✅ (max-as-default 주의)**
`monitoring/11-limit-range.yaml`에 `defaultRequest: { ephemeral-storage: 256Mi }` +
`max.ephemeral-storage: 10Gi` 추가.

⚠️ **중요한 K8s 동작**: LimitRange에서 어떤 리소스에 `max`만 있고 `default`(limit)가 없으면
**`max` 값이 그대로 default limit으로 주입**된다. 모니터링 파드는 cpu/mem limit은 자체 선언하지만
ephemeral limit은 선언하지 않으므로, `max.ephemeral-storage: 10Gi`는 사실상 **모든 모니터링
컨테이너의 ephemeral limit = 10Gi**로 작동한다(= "limit 없는 가드레일"은 ephemeral에선 성립 안 함).

그래서 10Gi를 **일부러 높게** 잡았다:
- Loki/VM/Tempo의 영구 데이터는 PVC(각 5/10/10Gi)로 가고, 노드 ephemeral은 주로 로그·쓰기
  레이어·emptyDir(alloy) → 정상 동작은 10Gi에 절대 안 닿는다.
- 폭주(워커 ~50GB 루트 디스크를 채워 DiskPressure → 노드 전체 파드 축출) 직전에는 **문제
  파드 하나만** ephemeral limit 초과로 격리 축출된다 → 관측 스택 전체 붕괴 방지.
- `defaultRequest: 256Mi`는 스케줄러의 ephemeral 예약 + kubelet의 DiskPressure 축출 순위
  (request 초과 파드 우선 축출) 근거로 쓰인다.

> monitoring에는 여전히 **하드 ResourceQuota는 없다** — LimitRange(위생/가드레일)만 둔다는
> 원래 설계 그대로. ephemeral도 쿼터가 아니라 per-pod LimitRange로만 다뤘다.
