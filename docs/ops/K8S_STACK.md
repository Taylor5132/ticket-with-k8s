# Kubernetes Infrastructure Stack

> Decision document for migrating the ticketing platform to the on-premises Kubernetes cluster.  
> Audience: team members joining the K8s migration phase.  
> Last updated after cross-validating every claim against actual application code.  
> **2026-06-12 현행화**: 결정 중 일부는 이미 시행됐고(ambient 메시, 트레이싱), 일부는 다른 방식으로 채택됐다(수동 로컬 PV, KPR 미적용, frontend/backend/db 네임스페이스). 본문에 현재 상태를 병기하며, 미착수 계획은 "(예정)"으로 표기한다.

---

## Cluster Topology

| VM | Role | Proxmox Host | IP | vCPU | RAM | OS Disk | Data Disk |
|---|---|---|---|---|---|---|---|
| lb-01 | Load Balancer | k8s | 192.168.0.16 | 1 | 1 GB | 32 GB | — |
| etcd-01 | etcd | k8s | 192.168.0.43 | 2 | 2 GB | 32 GB | 20 GB |
| etcd-02 | etcd | k8s | 192.168.0.18 | 2 | 2 GB | 32 GB | 20 GB |
| etcd-03 | etcd | **k8s2** | 192.168.0.19 | 2 | 2 GB | 32 GB | 20 GB |
| cp-01 | Control Plane | k8s | 192.168.0.46 | 2 | 4 GB | 40 GB | 20 GB |
| cp-02 | Control Plane | k8s | 192.168.0.21 | 2 | 4 GB | 40 GB | 20 GB |
| cp-03 | Control Plane | k8s2 | 192.168.0.22 | 2 | 4 GB | 40 GB | 20 GB |
| worker-01 | Worker | k8s | 192.168.0.23 | 3 | 7 GB | 50 GB | 100 GB |
| worker-02 | Worker | k8s2 | 192.168.0.24 | 3 | 7 GB | 50 GB | 100 GB |
| worker-03 | Worker | k8s2 | 192.168.0.25 | 3 | 7 GB | 50 GB | 100 GB |
| worker-04 | Worker | k8s | 192.168.0.50 | 3 | 7 GB | 50 GB | 100 GB |
| worker-05 | Worker | k8s2 | 192.168.0.51 | 3 | 7 GB | 50 GB | 100 GB |

**Usable worker capacity**: 15 vCPU / 35 GB RAM across 5 nodes.  
Reserve ~10 GB for system + observability. **~25 GB available for application pods.**

### etcd Quorum Risk

etcd-01 and etcd-02 are both on Proxmox host `k8s`. If that host goes down, two of three etcd members are lost — **quorum is broken, the cluster becomes read-only**. etcd-03 on `k8s2` is the only cross-host voter.

Mitigation: treat Proxmox host `k8s` as the highest-priority single point of failure. Monitor its health. If budget allows, migrate etcd-02 to a third distinct host.

### Why External etcd

etcd is on dedicated VMs, not co-located with control planes. Under flash sale load, API server, scheduler, and controller-manager all write heavily to etcd. Dedicated etcd VMs prevent application-driven control-plane activity from causing etcd write latency.

---

## The Core Problem: Flash Sale Traffic

This application is a **bursty flash sale system**:

- ~5% utilization for 23 hours
- Sudden spike at T+0 of a ticket release
- Thousands of users hitting the booking queue simultaneously
- A single bottleneck at any layer cascades into a full outage

Every infrastructure choice below is evaluated against: **what happens at T+0 of a flash sale?**

---

## CNI: Cilium

**Decision**: Cilium with eBPF-based kube-proxy replacement. **(목표 — 현재 미적용: 배포 클러스터는 `kube-proxy-replacement=false`로 kube-proxy(IPVS 모드)와 병행 중이고, Maglev도 미설정(기본 random), `routing-mode=tunnel`(VXLAN)이다. KPR 전환 시 kube-proxy/IPVS가 제거된다.)**

Calico and Flannel route traffic through iptables — a serialized O(n) rule chain that degrades under connection surges. Cilium replaces iptables with eBPF programs at O(1) lookup speed.

| Feature | Impact |
|---|---|
| eBPF kube-proxy replacement | Eliminates iptables bottleneck during booking surges |
| Maglev consistent hashing | Stable connection distribution across booking-api replicas |
| L7 network policy | "booking-api may only call POST /payments on payment-service" — enforced in kernel |
| Hubble | Real-time network flow visibility without instrumentation changes |
| LB-IPAM | Assigns LoadBalancer IPs natively — no MetalLB needed |

### Configuration

```bash
helm install cilium cilium/cilium \
  --set kubeProxyReplacement=true \
  --set k8sServiceHost=192.168.0.16 \   # lb-01 VIP — the HA entry point, NOT a single cp IP
  --set k8sServicePort=6443 \
  --set loadBalancer.algorithm=maglev \
  --set ipam.mode=kubernetes
```

> **Note**: `k8sServiceHost` must point to the load-balanced API server VIP (lb-01), not to cp-01's IP (192.168.0.46). Using a single control-plane IP here creates an SPOF that defeats the 3-cp HA setup.

---

## Service Mesh: Istio Ambient — 도입 완료 (원계획: Deferred)

**Decision (개정)**: 원래 결정은 "초기 출시엔 메시 없음"이었으나, 운영 중 **Istio 1.30 ambient 모드를 도입했다** — ztunnel 8/8 전 노드(L4 mTLS), waypoint 없음(팀 방침). 아래의 "메시 25ms 논쟁이 이 앱에 무관한 이유" 분석은 waypoint(L7 프록시)를 켜지 않는 근거로 여전히 유효하다.

### Why the "Mesh Adds 25ms" Argument Doesn't Apply Here

A common argument for sidecarless mesh is eliminating per-hop sidecar latency for multi-service call chains. **This app's synchronous user-facing request path has only one hop: Gateway → service.**

Evidence from the code:
- JWT is verified locally in every service (`common.py:33–40`) — no call to auth-service per request
- booking-api receives a booking request, enqueues it to `booking.requests` Redis stream, and returns immediately
- The downstream chain (worker → event-service → payment-service) is **asynchronous** — it happens in the background worker, not in the user's response path

The remaining value of a service mesh for this app is **mTLS between services**. Cilium's mutual auth has been in beta for years and is not production-grade for this use case. If mTLS is required, use **Istio ambient mode** (stable as of Istio 1.22+), which adds a node-level ztunnel without sidecars.

**For now**: Cilium NetworkPolicy with default-deny covers lateral movement. Add Istio ambient when the team has operational capacity. → **이후 ambient 도입 완료 (상단 개정 참조). NetworkPolicy와 병행 운영 중.**

---

## Ingress: Istio Gateway + Kubernetes Gateway API + Cilium LB-IPAM

**Decision**: Istio as the Gateway API implementation. Cilium LB-IPAM for LoadBalancer IPs (no MetalLB needed — Cilium is already installed).

### Why Not Cilium Gateway for This App

Cilium Gateway API does not support **regex path rewrite**. This application has a hard routing requirement: `/api/performances/{id}/seat-availability` must route to `booking-api`, while all other `/api/performances/*` routes go to `event-service`. This split requires a regex match that Cilium Gateway cannot express — it is a runtime blocker.

Istio Gateway handles this correctly.

→ **실전 검증됨**: 다만 Gateway API 표준만으로는 regex "재작성"까지는 불가해서, 최종적으로 **EnvoyFilter**(regex capture rewrite → booking-api)로 해결했다. Cilium Gateway 기각 사유였던 이 요구사항이 실제 장애(좌석창 404)로 재확인된 셈이다.

### Why Not the Old Ingress API

`networking.k8s.io/v1 Ingress` cannot express per-route timeouts, retries, or traffic weights. Gateway API solves this natively.

### Critical HTTPRoute: seat-availability Split

```yaml
# This split MUST be present — without it, the highest-traffic read path during
# a flash sale (seat availability checks) returns 404 from event-service.
HTTPRoute:
  # seat-availability → booking-api (must match before the broader performances rule)
  match: path regex ^/api/performances/[^/]+/seat-availability
  backend: booking-api:8000

  # All other performance routes → event-service
  match: path prefix /api/performances
  backend: event-service:8000

  # Queue, booking, payment routes → respective services
  match: path prefix /api/queue           → booking-api:8000   timeout: 30s
  match: path prefix /api/booking-requests → booking-api:8000  timeout: 10s
  match: path prefix /api/bookings        → booking-api:8000   timeout: 10s
  match: path prefix /api/payments        → payment-service:8000
  match: path prefix /api/auth            → auth-service:8000
  match: path prefix /api/saved           → saved-service:8000
  match: /                                → frontend:5173
```

### External Entry Point: Cloudflare Tunnel

This cluster sits behind a home router (192.168.0.1 gateway) with no port forwarding. Internet → lb-01 direct is not possible. The Cloudflare Tunnel (`cloudflared`) that was set up in Docker Compose is the correct external entry point — it opens an outbound tunnel to Cloudflare's edge, so no router config is needed.

In Kubernetes: run `cloudflared` as a Deployment in the **`frontend`** namespace (실배치 ×2 HA). 게이트웨이 Svc는 LB-IPAM으로 192.168.0.100을 할당받지만 L2 announce가 없어 LAN 직접 접근은 불가 — 외부 유입은 터널 경유가 유일한 경로다.

---

## Observability: VictoriaMetrics + Loki + Grafana (Tracing Deferred)

**Decision (개정)**: Phase 1(메트릭+로그+대시보드)과 **Phase 2(Tempo 트레이싱 + OTel Collector)가 모두 배포되었다.** 각 서비스 코드에도 `telemetry.py` 계측이 추가됨. 로그 수집기는 Promtail 대신 **Grafana Alloy**(DaemonSet)를 채택.

### Why Defer Tracing

Full LGTM (VictoriaMetrics + Loki + Tempo + Pyroscope + OTel Collector) costs ~1.5–2 GB RAM and adds per-request CPU overhead from span collection — precisely when the cluster needs every cycle for booking throughput. ArgoCD (see below) also requires ~1–1.5 GB. Tracing can be enabled after the first sale gives baseline data.

### Phase 1 Stack (launch)

| Signal | Tool |
|---|---|
| Metrics | VictoriaMetrics |
| Logs | Loki + Alloy (DaemonSet — Promtail 대신 채택) |
| Visualization | Grafana |
| Alerting | Alertmanager → Slack (warning) / PagerDuty (critical) |

### Phase 2 Stack (post-launch)

Add Tempo (traces) + OpenTelemetry Collector once baseline RAM headroom is confirmed. → **배포 완료 (2026-06-12 기준 monitoring NS에서 가동 중)**

### Dashboard 1: Booking Funnel (Product View)

The most important dashboard — shows where users drop off during a sale:

```
Queue joins/min → Seat page loads/min → Booking requests/min → Confirmed/min → Failed/min
```

Conversion rates between each stage reveal where the bottleneck is during a flash sale.

### Dashboard 2: Queue System

- `booking.requests` stream pending message count (KEDA input signal)
- booking-worker consumer group lag over time
- Waiting room position distribution (P50/P95 of queue position at join time)

### Dashboard 3: Infrastructure Headroom

- CPU/RAM per worker node (how close to saturation)
- PostgreSQL connection pool per service DB
- Redis memory usage and connected clients

### SLO Alerts

| Alert | Threshold | Severity |
|---|---|---|
| Booking API P99 latency | > 500 ms | Warning |
| Booking confirmed rate | < 99% | Critical |
| Redis stream lag (`booking.requests`) | > 500 messages | Warning |
| PostgreSQL connection pool | > 80% | Warning |
| Worker node memory | > 85% | Critical |

---

## Auto-scaling: KEDA

**Decision**: KEDA for all event-driven scaling. HPA for CPU-bound services.

### booking-worker: Scale on Redis Stream Lag

```yaml
triggers:
- type: redis-streams
  metadata:
    address: redis.ticket-data.svc:6379
    stream: booking.requests          # exact name from common.py — not "booking-stream"
    consumerGroup: booking-workers    # from common.py:17
    pendingEntriesCount: "10"
    minReplicaCount: "2"
    maxReplicaCount: "6"              # see capacity math below
```

**Why maxReplicaCount: 6, not 20**

Each booking-worker replica processes `xreadgroup(count=1)` + `sleep(0.1)` per iteration. This is a hard code ceiling of **~6–7 messages/second per replica** regardless of hardware.

At `QUEUE_ADMISSION_RATE=3/s` (default), the queue fills at 3 msg/s. One worker drains at 6–7 msg/s — already faster than it fills. Scaling to 20 replicas means 17 workers consuming memory while processing nothing. Set max at 6: enough to handle bursts and replica failures, none wasted.

To increase real throughput, the worker code must be changed (increase `count=`, remove `sleep(0.1)`, or run async). That is a code-level decision, not an infra one.

### booking-api: Scale on RPS (Leading Indicator)

CPU is a lagging indicator — it rises *after* the service is already under load. RPS is the leading signal.

```yaml
triggers:
- type: prometheus
  metadata:
    serverAddress: http://victoriametrics.monitoring:8428
    query: sum(rate(http_requests_total{service="booking-api"}[1m]))
    threshold: "80"    # 80 RPS per replica
    minReplicaCount: "2"
    maxReplicaCount: "8"
```

**Combine with cron pre-scale**: for announced sales, scale up 10 minutes before the sale opens rather than waiting for KEDA to react.

```yaml
triggers:
- type: cron
  metadata:
    timezone: Asia/Seoul
    start: "50 19 * * 5"   # 19:50 KST Friday (10 min before a Friday sale)
    end:   "30 21 * * 5"   # 21:30 KST Friday
    desiredReplicas: "6"
```

---

## Load Testing: k6 (External, Not In-Cluster)

**Decision**: Run k6 from a dedicated machine on the LAN, not inside the cluster.

> **수행됨 (1차)**: `load-test/k6-test.js`로 클러스터 외부 머신에서 부하테스트 완료 — 30 VU ramp(1m 상승 → 5m 유지 → 30s 하강), 전체 예매 플로우(좌석조회 → 대기열 join/폴링 → 예매 요청 → 상태 폴링), 결과는 Prometheus remote-write로 VictoriaMetrics(:30428)에 적재.  
> 계획과의 차이: ① 토큰을 env 주입 대신 `setup()`에서 dev-login으로 일괄 발급 (반복 로그인 회피 취지는 충족) ② `k6-vu-*` 계정은 기본 100,000P라 VIP석(150,000P)은 `INSUFFICIENT_POINTS`로 실패 가능 — 아래 demo-rich 권고는 미적용 ③ 대상 주소가 구 게이트웨이(192.168.0.99)였으므로 booking NS 폐기 후에는 192.168.0.100으로 변경 필요.  
> 아래 Test Protocol 표(soak/spike/breakpoint)는 미수행. (예정)

### Why Not k6 Operator In-Cluster

Running k6 inside the cluster means the load generators and the application under test share the same 15 vCPU / 35 GB. During a spike test the generators consume resources that directly reduce the headroom available to booking-api and booking-worker. You are measuring a degraded system, not the real capacity.

Use any spare machine on the LAN (`192.168.0.x`) as the load generator. It has direct network access to the cluster's LoadBalancer IPs.

### k6 Scenario: Correct Setup

Two common mistakes to avoid:

1. **Do not call `/api/auth/login` per virtual user in the scenario.** bcrypt verification takes 100–300 ms of CPU per call. Thousands of VUs hammering auth-service makes it the bottleneck — but auth-service is not what you're testing. Instead, **pre-generate JWT tokens** for test accounts and inject them as environment variables.

2. **Use demo-rich accounts for booking VUs.** Regular accounts have 100,000 points. VIP seats cost 150,000 points — every booking attempt fails with `INSUFFICIENT_POINTS`. Use the `demo-rich` seed account (300,000 points) or pre-seed test accounts with sufficient balance.

```javascript
// Correct: tokens pre-generated, not created per VU
const TOKEN = __ENV.DEMO_RICH_TOKEN;
const PERF_ID = __ENV.PERF_ID;
const SHOW_DATE = __ENV.SHOW_DATE;

export default function () {
  // 1. Join queue (using pre-existing token)
  const queueRes = http.post(
    `/api/queue/join?performance_id=${PERF_ID}&show_date=${SHOW_DATE}`,
    null,
    { headers: { Authorization: `Bearer ${TOKEN}` } }
  );

  // 2. Poll queue until admitted
  let admitted = false;
  while (!admitted) {
    sleep(2);
    const status = http.get(
      `/api/queue/status?performance_id=${PERF_ID}&show_date=${SHOW_DATE}`,
      { headers: { Authorization: `Bearer ${TOKEN}` } }
    );
    admitted = status.json('admitted');
  }

  // 3. Select a seat and submit booking request
  const bookRes = http.post('/api/booking-requests',
    JSON.stringify({ performance_id: PERF_ID, seat_id: 'A-1', show_date: SHOW_DATE }),
    { headers: { Authorization: `Bearer ${TOKEN}`, 'Content-Type': 'application/json' } }
  );

  // 4. Poll booking status until terminal state
  const requestId = bookRes.json('request_id');
  let confirmed = false;
  for (let i = 0; i < 30; i++) {
    sleep(1);
    const statusRes = http.get(`/api/booking-requests/${requestId}`,
      { headers: { Authorization: `Bearer ${TOKEN}` } }
    );
    const status = statusRes.json('status');
    if (status === 'CONFIRMED' || status === 'FAILED') { confirmed = true; break; }
  }
}
```

### The Real Acceptance Criterion

P99 latency thresholds are necessary but not sufficient for a ticketing system. The most important invariant is:

> **Each seat may have at most one CONFIRMED booking per performance date.**

Run a post-test SQL assertion:

```sql
-- Must return 0 rows after every load test
SELECT performance_id, performance_date, seat_id, COUNT(*)
FROM bookings
GROUP BY performance_id, performance_date, seat_id
HAVING COUNT(*) > 1;
```

A test that passes P99 thresholds but violates this invariant is a failed test.

### Test Protocol

| Test | Shape | Goal |
|---|---|---|
| Soak | 200 concurrent users × 2 hours | Find memory leaks in booking-worker |
| Spike | 0 → 2,000 users in 30 seconds | Validate KEDA reacts before queue saturates |
| Breakpoint | Ramp 100 users/min until failure | Find actual capacity ceiling |

---

## Chaos Engineering: Chaos Mesh

Run these scenarios against staging before every major sale.

| Scenario | Type | What it validates |
|---|---|---|
| Kill worker-01 during spike test | PodChaos | Booking-worker pods reschedule without losing queued messages |
| Partition booking-api from Redis | NetworkChaos | Booking requests fail fast; circuit breaker trips; no silent data loss |
| Inject 200ms latency on payment-service | NetworkChaos | Worker retry logic handles slow payments; queue doesn't back up indefinitely |
| Kill booking-worker pod mid-processing | PodChaos | Redis stream `xack` ensures at-least-once delivery; no duplicate confirmed bookings |
| Stress CPU on worker-03 node | StressChaos | KEDA reschedules booking-worker pods to less-loaded nodes |

> **Do not run a "PostgreSQL primary failover" scenario.** This app uses a single PostgreSQL instance per service DB (ADR-0003). There is no replica to fail over to — the test would validate nothing and leave the DB in a broken state.

---

## Storage: local-path-provisioner (Primary) + Longhorn (Upgrade Path)

**Decision (개정)**: local-path-provisioner 대신 **수동 로컬 PV**를 채택했다 — StorageClass `local-storage`(no-provisioner, WaitForFirstConsumer, Retain), 노드별 `/mnt/data` 경로. fsync가 로컬 디스크로 떨어진다는 원래 논거는 동일하게 충족된다. Longhorn은 여전히 업그레이드 경로다. (예정)

### Why Not Longhorn at Launch

Longhorn replicates every write over the LAN before acknowledging it to PostgreSQL. PostgreSQL flushes WAL on every commit (fsync). This means every transaction crosses the LAN twice — on the hot path that users wait for during seat confirmation. At ~1ms LAN latency + 2 replicas, that adds ~2ms per write, which compounds across a flash sale.

Longhorn also costs ~1–2 vCPU and 4–5 GB RAM across the cluster for its managers and CSI components.

**local-path-provisioner** uses a node-local directory — fsync writes go to the local disk, sub-millisecond. Node loss means data loss for that node's PVC.

**Upgrade trigger**: when the team requires RPO ≈ 0 on node failure, migrate to Longhorn with `dataLocality: best-effort` (primary replica stays local, secondary crosses LAN only for durability).

---

## ArgoCD Integration

ArgoCD manages all Kubernetes manifests as GitOps — **가동 중(파드 7/7), GitLab `team6/manifest` repo 동기화**. Resource cost: ~0.3–0.5 vCPU / 1–1.5 GB RAM — fits within the 25 GB headroom alongside a deferred tracing stack.

### Rule 1: Remove `spec.replicas` from KEDA-managed Deployments

If `spec.replicas` is set in a manifest and ArgoCD is set to auto-sync, ArgoCD will reset the replica count every sync cycle — overriding KEDA's scale decisions. During a flash sale this causes booking-worker to be scaled back down mid-sale.

```yaml
# In every Deployment managed by KEDA or HPA:
spec:
  # replicas: intentionally omitted — managed by KEDA/HPA
  selector: ...
```

Or use `ignoreDifferences` in the ArgoCD Application:

```yaml
ignoreDifferences:
- group: apps
  kind: Deployment
  jsonPointers:
  - /spec/replicas
```

### Rule 2: Sync Window — Freeze Deployments During Sales

Block ArgoCD auto-sync in the window around each sale. A deployment mid-sale can cause a rolling restart of booking-api while users are in the queue.

```yaml
syncWindows:
- kind: deny
  schedule: "50 19 * * 5"   # 19:50 KST Friday
  duration: 2h
  applications: ["*"]
  namespaces: ["ticket-backend", "ticket-ingress"]
```

### Rule 3: CRD Ownership — Never Let ArgoCD Prune Gateway CRDs

If ArgoCD prunes a GatewayClass CRD during a sync, all HTTPRoutes referencing it are deleted — full ingress outage. Install Gateway API CRDs as a separate App with pruning disabled.

```yaml
# App: gateway-crds
syncPolicy:
  automated:
    prune: false      # never prune CRDs
  syncOptions:
  - RespectIgnoreDifferences=true
```

---

## Namespace Layout

```
frontend     Istio Gateway(booking-gw) + HTTPRoute + cloudflared + React frontend
backend      auth, event, booking-api, booking-worker, payment, saved
db           PostgreSQL, Redis (worker-01 로컬 PV)
monitoring   VictoriaMetrics, Loki, Grafana, Alertmanager, Alloy, Tempo, OTel Collector
argocd       ArgoCD server, repo-server, application-controller 외
```

(원계획의 `ticket-*` 명명은 채택되지 않았고 위 구조로 확정됐다.)

NetworkPolicy default-deny per namespace + explicit allow rules — **적용 완료**. 단 ambient 메시에서는 파드 간 트래픽이 HBONE 포트 **15008/TCP**로 도착하므로, 포트를 제한하는 모든 허용 규칙에 15008을 반드시 포함해야 한다 (2026-06-12 네임스페이스 분리 마이그레이션에서 실제 장애로 확인된 교훈 — ztunnel 로그의 "NetworkPolicy is blocking HBONE port 15008"이 진단 단서였다).

---

## Implementation Order

```
 1. Cilium CNI                    install first — networking foundation
 2. Cilium LB-IPAM                assign LoadBalancer IPs (no MetalLB needed)
 3. Istio (Gateway mode only)     Gateway API implementation, no mesh sidecars yet
 4. ArgoCD                        GitOps from this point forward
 5. 로컬 PV (수동 — 계획은 local-path-provisioner)   storage before stateful services
 6. PostgreSQL + Redis             Deployments, PVCs
 7. Application services          raw manifests → ArgoCD Apps (ticket-backend)
 8. HTTPRoutes                    replace Caddy + Vite proxy, verify seat-availability split
 9. cloudflared                   external access via Cloudflare Tunnel
10. KEDA                          Redis stream scaler (booking.requests) + RPS scaler (예정)
11. Observability Phase 1         VictoriaMetrics + Loki + Grafana + Alertmanager → 배포 완료
12. Chaos Mesh                    run chaos suite before announcing any sale (예정)
13. k6 load tests                 from external LAN machine → 1차 수행됨 (load-test/k6-test.js)
14. Istio ambient (optional)      add mTLS after launch once baseline is stable → 도입 완료
15. Observability Phase 2         Tempo + OTel Collector once RAM headroom confirmed → 배포 완료
16. Longhorn migration            when node-loss RPO ≈ 0 becomes a requirement (예정)
```

---

## Full Architecture Diagram

```
Internet
    │
  Cloudflare Edge (TLS termination)
    │ (outbound tunnel — no port forwarding required)
  cloudflared pod [frontend]
    │
  Istio Gateway [frontend]
  (Gateway API HTTPRoutes: regex split for seat-availability)
    │
  Cilium eBPF dataplane (kube-proxy replacement, LB-IPAM, NetworkPolicy)
    │
┌──────────────────────────────────────────────────────────┐
│  Worker Nodes 01–05  [backend]                    │
│                                                          │
│  auth-service    event-service    booking-api            │
│  payment-service saved-service    booking-worker (×2–6)  │
│                                        ↑                 │
│                            KEDA: scales on               │
│                            booking.requests stream lag   │
│                            + booking-api RPS trigger     │
└──────────────────────────────────────────────────────────┘
    │
┌──────────────────────────────────────────────────────────┐
│  [db]                                           │
│  PostgreSQL (로컬 PV, one instance per service DB)│
│  Redis      (로컬 PV)                             │
└──────────────────────────────────────────────────────────┘
    │
┌──────────────────────────────────────────────────────────┐
│  [monitoring]                                            │
│  VictoriaMetrics  Loki  Grafana  Alertmanager            │
│  Hubble UI (Cilium network flows)                        │
└──────────────────────────────────────────────────────────┘
    │
┌──────────────────────────────────────────────────────────┐
│  [argocd]                                                │
│  ArgoCD (GitOps — all manifests from git)                │
└──────────────────────────────────────────────────────────┘
    │
  etcd cluster (external, dedicated VMs)
  etcd-01: 192.168.0.43 (k8s host)  ← quorum risk: same host as etcd-02
  etcd-02: 192.168.0.18 (k8s host)  ←
  etcd-03: 192.168.0.19 (k8s2 host) ← cross-host minority voter

  External load generator (LAN machine)
  k6 → 192.168.0.16 (lb-01) → Istio Gateway
  (separate from cluster to avoid polluting measurement)
```

<!-- mirror test 2026-06-11T07:33:38Z -->
