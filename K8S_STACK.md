# Kubernetes Infrastructure Stack

> Decision document for migrating the ticketing platform to the on-premises Kubernetes cluster.  
> Audience: team members joining the K8s migration phase.  
> Last updated after cross-validating every claim against actual application code.

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

**Decision**: Cilium with eBPF-based kube-proxy replacement.

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

## Service Mesh: Deferred (Application Does Not Need L7 Mesh)

**Decision**: No service mesh at initial launch. Evaluate Istio ambient after traffic patterns are established.

### Why the "Mesh Adds 25ms" Argument Doesn't Apply Here

A common argument for sidecarless mesh is eliminating per-hop sidecar latency for multi-service call chains. **This app's synchronous user-facing request path has only one hop: Gateway → service.**

Evidence from the code:
- JWT is verified locally in every service (`common.py:33–40`) — no call to auth-service per request
- booking-api receives a booking request, enqueues it to `booking.requests` Redis stream, and returns immediately
- The downstream chain (worker → event-service → payment-service) is **asynchronous** — it happens in the background worker, not in the user's response path

The remaining value of a service mesh for this app is **mTLS between services**. Cilium's mutual auth has been in beta for years and is not production-grade for this use case. If mTLS is required, use **Istio ambient mode** (stable as of Istio 1.22+), which adds a node-level ztunnel without sidecars.

**For now**: Cilium NetworkPolicy with default-deny covers lateral movement. Add Istio ambient when the team has operational capacity.

---

## Ingress: Istio Gateway + Kubernetes Gateway API + Cilium LB-IPAM

**Decision**: Istio as the Gateway API implementation. Cilium LB-IPAM for LoadBalancer IPs (no MetalLB needed — Cilium is already installed).

### Why Not Cilium Gateway for This App

Cilium Gateway API does not support **regex path rewrite**. This application has a hard routing requirement: `/api/performances/{id}/seat-availability` must route to `booking-api`, while all other `/api/performances/*` routes go to `event-service`. This split requires a regex match that Cilium Gateway cannot express — it is a runtime blocker.

Istio Gateway handles this correctly.

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

In Kubernetes: run `cloudflared` as a Deployment in `ticket-ingress` namespace. It connects to the Istio Gateway service's ClusterIP (not a LoadBalancer). Cilium LB-IPAM handles internal cluster-to-cluster LoadBalancer IPs.

---

## Observability: VictoriaMetrics + Loki + Grafana (Tracing Deferred)

**Decision**: Deploy metrics + logs + dashboards now. Defer Tempo/Pyroscope/OTel until after first live sale.

### Why Defer Tracing

Full LGTM (VictoriaMetrics + Loki + Tempo + Pyroscope + OTel Collector) costs ~1.5–2 GB RAM and adds per-request CPU overhead from span collection — precisely when the cluster needs every cycle for booking throughput. ArgoCD (see below) also requires ~1–1.5 GB. Tracing can be enabled after the first sale gives baseline data.

### Phase 1 Stack (launch)

| Signal | Tool |
|---|---|
| Metrics | VictoriaMetrics |
| Logs | Loki + Promtail (DaemonSet) |
| Visualization | Grafana |
| Alerting | Alertmanager → Slack (warning) / PagerDuty (critical) |

### Phase 2 Stack (post-launch)

Add Tempo (traces) + OpenTelemetry Collector once baseline RAM headroom is confirmed.

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

**Decision**: Start with local-path-provisioner. Migrate to Longhorn when data HA is required.

### Why Not Longhorn at Launch

Longhorn replicates every write over the LAN before acknowledging it to PostgreSQL. PostgreSQL flushes WAL on every commit (fsync). This means every transaction crosses the LAN twice — on the hot path that users wait for during seat confirmation. At ~1ms LAN latency + 2 replicas, that adds ~2ms per write, which compounds across a flash sale.

Longhorn also costs ~1–2 vCPU and 4–5 GB RAM across the cluster for its managers and CSI components.

**local-path-provisioner** uses a node-local directory — fsync writes go to the local disk, sub-millisecond. Node loss means data loss for that node's PVC.

**Upgrade trigger**: when the team requires RPO ≈ 0 on node failure, migrate to Longhorn with `dataLocality: best-effort` (primary replica stays local, secondary crosses LAN only for durability).

---

## ArgoCD Integration

ArgoCD manages all Kubernetes manifests as GitOps. Resource cost: ~0.3–0.5 vCPU / 1–1.5 GB RAM — fits within the 25 GB headroom alongside a deferred tracing stack.

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
ticket-ingress     Istio Gateway, HTTPRoute, cloudflared Deployment
ticket-web         React frontend Deployment
ticket-backend     auth, event, booking-api, booking-worker, payment, saved
ticket-data        PostgreSQL StatefulSet, Redis StatefulSet
monitoring         VictoriaMetrics, Loki, Grafana, Alertmanager
argocd             ArgoCD server, repo-server, application-controller
```

Cilium NetworkPolicy with default-deny per namespace. Explicit allow rules per service pair.

---

## Implementation Order

```
 1. Cilium CNI                    install first — networking foundation
 2. Cilium LB-IPAM                assign LoadBalancer IPs (no MetalLB needed)
 3. Istio (Gateway mode only)     Gateway API implementation, no mesh sidecars yet
 4. ArgoCD                    storage before stateful services
 6. PostgreSQL + Redis                GitOps from this point forward
 5. local-path-provisioner         StatefulSets, PVCs
 7. Application services          raw manifests → ArgoCD Apps (ticket-backend)
 8. HTTPRoutes                    replace Caddy + Vite proxy, verify seat-availability split
 9. cloudflared                   external access via Cloudflare Tunnel
10. KEDA                          Redis stream scaler (booking.requests) + RPS scaler
11. Observability Phase 1         VictoriaMetrics + Loki + Grafana + Alertmanager
12. Chaos Mesh                    run chaos suite before announcing any sale
13. k6 load tests                 from external LAN machine, with pre-generated tokens
14. Istio ambient (optional)      add mTLS after launch once baseline is stable
15. Observability Phase 2         Tempo + OTel Collector once RAM headroom confirmed
16. Longhorn migration            when node-loss RPO ≈ 0 becomes a requirement
```

---

## Full Architecture Diagram

```
Internet
    │
  Cloudflare Edge (TLS termination)
    │ (outbound tunnel — no port forwarding required)
  cloudflared pod [ticket-ingress]
    │
  Istio Gateway [ticket-ingress]
  (Gateway API HTTPRoutes: regex split for seat-availability)
    │
  Cilium eBPF dataplane (kube-proxy replacement, LB-IPAM, NetworkPolicy)
    │
┌──────────────────────────────────────────────────────────┐
│  Worker Nodes 01–05  [ticket-backend]                    │
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
│  [ticket-data]                                           │
│  PostgreSQL (local-path PVC, one instance per service DB)│
│  Redis      (local-path PVC)                             │
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
