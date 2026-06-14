# Autoscaling System Test — 2026-06-14

End-to-end validation of every autoscaler in the booking app (KEDA ScaledObjects +
CPU HPAs), driven by k6 load and synthetic stream injection. This session also
uncovered and fixed several silently-broken triggers and a homepage regression.

Companion to [`LOAD_SHEDDING.md`](./LOAD_SHEDDING.md) (capacity ceiling / DestinationRule).

---

## Scope: the autoscalers

| Workload | Type | Trigger | Min→Max | How tested |
|---|---|---|---|---|
| event-service | KEDA | Prometheus RPS `÷60` | 2→8 | k6 GET flood |
| booking-api | KEDA | Prometheus RPS `÷80` **+** P95 latency `÷0.1` | 2→8 | k6 seat-availability read flood |
| booking-worker | KEDA | redis-streams **lag** `÷10` | 2→6 | synthetic stream injection |
| admission-worker | KEDA | redis-streams **lag** `÷100` | 1→6 | synthetic stream injection |
| auth-service | HPA | CPU 70% | 1→3 | not load-tested (functional) |
| payment-service | HPA | CPU 70% | 1→3 | not load-tested (functional) |

**KEDA scaling math:** `desiredReplicas = ceil(metricValue / threshold)`, where
`metricValue` is the whole query/lag (the HPA shows it per-replica as
`avgValue = metricValue / replicas`).

---

## Environment

- **k6**: Docker container on a dedicated VM `192.168.0.63`, outside the cluster,
  streaming metrics to VictoriaMetrics (`192.168.0.24:30428`) via
  `experimental-prometheus-rw`.
- **Target**: gateway `192.168.0.100` (Istio ambient + Cilium).
- **Script**: [`load-test/k6-keda-test.js`](../../load-test/k6-keda-test.js),
  `SCENARIO` env var selects one isolated target (`event` / `booking-api` / `worker`).
- **Observation**: server-side metrics in VictoriaMetrics + `kubectl` polling watchers.

Run form:
```bash
docker run --rm -i --network host \
  -e SCENARIO=<event|booking-api|worker> \
  -e K6_PROMETHEUS_RW_SERVER_URL=http://192.168.0.24:30428/api/v1/write \
  -e K6_PROMETHEUS_RW_TREND_STATS="p(50),p(95),p(99),min,max" \
  grafana/k6:latest run --out experimental-prometheus-rw - < ~/k6-keda-test.js
```

---

## Prerequisite fixes (without these, nothing scaled)

### 1. metrics-server was missing → CPU HPAs were dead
The auth/payment HPAs read `cpu: <unknown>/70%` and could not scale
(`FailedGetResourceMetric`, `pods.metrics.k8s.io` not found). Installed
metrics-server v0.7.2 (`--kubelet-insecure-tls`) → HPAs now report real CPU.
Manifest: `manifest/cluster/metrics-server.yaml`.

### 2. Backend pod metrics were never scraped → RPS/latency triggers read 0 forever
`http_requests_total` was absent from VictoriaMetrics for **all** backend pods
(`up=0`). Root cause (via `hubble observe`): Alloy (hostNetwork DaemonSet) scrapes
`:8000` plaintext; istio-cni redirects it into the pod's ztunnel, which
re-originates the final hop from link-local `169.254.7.127` (Cilium identity
`world`). Backend's `default-deny-ingress` dropped that hop. Real app traffic was
unaffected (it rides HBONE `:15008`, already allowed). Fix:
`manifest/booking/19-allow-host-metrics-scrape.yaml` (CiliumNetworkPolicy
`fromCIDR: 169.254.7.127/32` on `:8000`). After: all backend pods `up=1`, metrics flow.

> Lesson: any default-deny namespace with ambient-meshed pods needing plaintext
> Prometheus scraping needs this allow.

---

## Results

### event-service — RPS trigger ✅ validated live

Ramp 80→150→300→480 RPS. Scaled cleanly, each step matching `ceil(RPS/60)`:

| RPS | Replicas |
|---|---|
| 80 | 2 (min — `ceil(80/60)=2`) |
| 150 | 3 |
| 300 | 5 |
| 480 | **8** (max) |

- 234,985 requests, **p95 8.12ms**, threshold pass.
- **0.56% failures — all Envoy 503 load-shed** (1160) during scale-up lag; the app
  served 100% 2xx. `max=6.31s` latency tail at the transition moments.

### booking-api — RPS trigger ✅ validated live (latency trigger fixed, see below)

Ramp 120→240→400→560 RPS, `ceil(RPS/80)`:

| RPS | Replicas |
|---|---|
| 120 | 2 (min) |
| 240 | 3 |
| 400 | 5 |
| 560 | **7** |

- 308,519 requests, **p95 7.87ms**, `max=200ms`, **0.15% fail** (373 Envoy 503), 100% app 2xx.
- **Only 11 of 200 VUs needed** — latency so low that concurrency stayed tiny;
  the read path has large headroom above 560 RPS.
- postgres peaked at **141m CPU** (0.14 cores) — never the bottleneck.

### booking-worker — redis-streams lag ✅ validated by injection

The natural `SCENARIO=worker` run **could not** trigger it for two reasons:
1. **Seat ceiling**: 800 seats deplete in ~86s (922 booking-requests, 800 confirmed),
   so the sustained booking-request rate (~10.7/s) never exceeded the 2-worker
   drain (~13/s) → no backlog.
2. **Wrong metric** (see fixes): the trigger read XPENDING, pinned at ~0.

After switching to `lagCount`, a **4000-entry injection** scaled it **2→4→6**;
6 workers drained the backlog in ~80s, then it returned to 2.

### admission-worker — redis-streams lag ✅ validated by injection

A **50,000-entry `work-stream` injection** scaled it **1→4→6** (drained in ~25s —
batch-of-10 reads, no sleep, so much faster than booking-worker), then returned to 1.

### auth-service / payment-service — CPU HPA ⚙️ functional, not load-tested

Report real CPU after the metrics-server fix; a bcrypt-login CPU test was deferred
(burns real node CPU). Left at baseline.

---

## Trigger bugs found & fixed

### A. booking-api latency trigger returned a multi-element vector → `<unknown>`
`histogram_quantile(0.95, rate(...[2m]))` ran **without `sum by (le)`**, producing
one P95 per `(pod,handler)`. KEDA rejects a multi-element result, so the metric was
permanently `<unknown>` and never fired. Fixed in `11-keda-scaledobjects.yaml`:
```promql
ceil(histogram_quantile(0.95,
  sum(rate(http_request_duration_seconds_bucket{service="booking-api",handler!="/metrics"}[2m])) by (le)
) / 0.1)
```
plus `ignoreNullValues: "true"`. (Note: seat-availability P95 is ~8ms, so this
trigger can't fire on reads anyway — it's for the DB-slow/write path.)

### B. booking-worker & admission-worker used `pendingEntriesCount` (XPENDING) → never fired
Both workers ack every message immediately (`finally: r.xack`), so XPENDING — what
`pendingEntriesCount` measures — is pinned at ~0 regardless of backlog. **Proven**:
a 3000-entry injection produced `lag=3000` but KEDA's metric stayed **0**. Fixed:
switched both to **`lagCount`** (unread backlog = entries-added − entries-read).
KEDA 2.20.1 supports it.

> Lesson: for KEDA redis-streams with fast-acking consumers, use `lagCount`, not
> `pendingEntriesCount`.

### C. event-service `/performances` pagination broke the homepage (regression)
A `limit=100` default (intended as OOM protection) was deployed by CI and **broke
the dashboard**, which fetches the full catalog once and derives every view
client-side — it showed the 100 oldest shows and emptied the "오픈 예정" row.
Reverted: `limit` is now optional (default returns all). OOM is mitigated by the
512Mi bump + the load test targeting `/{id}` instead of the list endpoint.

---

## Reproducing the worker tests (injection method)

The seat ceiling blocks a natural worker backlog, so inject directly. Safe because
both workers drain injected entries:

```bash
# booking-worker: malformed entries (worker KeyErrors then acks in finally) — safe
kubectl -n db exec deploy/redis -- sh -c \
  'for i in $(seq 1 4000); do printf "XADD booking.requests * f %s\n" "$i"; done | redis-cli'

# admission-worker: must be WELL-FORMED (it does NOT ack on error → poison risk).
# issue_token sets a token key (600s TTL, self-expiring) then acks.
kubectl -n db exec deploy/redis -- sh -c \
  'for i in $(seq 1 50000); do printf "XADD work-stream * performance_id 287 show_date 2026-07-01 user_id synth%s\n" "$i"; done | redis-cli'

# watch
watch -n2 'kubectl get hpa,deploy -n backend | grep -E "worker"'

# cleanup (entries are acked; safe to trim)
kubectl -n db exec deploy/redis -- redis-cli XTRIM booking.requests MAXLEN 100
kubectl -n db exec deploy/redis -- redis-cli XTRIM work-stream MAXLEN 100
```

Data reset before the natural `SCENARIO=worker` run: see
[`LOAD_SHEDDING.md` → Data Reset Commands](./LOAD_SHEDDING.md#data-reset-commands)
(frees the 800 seats + resets points; required or k6 skips on no-available-seats).

---

## Validation status summary

| Scaler | Trigger | Status |
|---|---|---|
| event-service | RPS | ✅ validated live (2→8) |
| booking-api | RPS | ✅ validated live (2→7) |
| booking-api | P95 latency | 🔧 query fixed; not exercisable by fast reads |
| booking-worker | stream lag | ✅ fixed (`lagCount`) + validated (2→6) |
| admission-worker | stream lag | ✅ fixed (`lagCount`) + validated (1→6) |
| auth-service | CPU | ⚙️ functional (metrics-server); not load-tested |
| payment-service | CPU | ⚙️ functional (metrics-server); not load-tested |

**Net:** three silently-dead triggers fixed (backend metrics scrape, booking-api
latency query, both worker `lagCount`) plus the metrics-server install and a
homepage regression — all things that *looked* configured but didn't work.

---

## Cross-cutting observations

- **Load shedding works as designed**: during every scale-up step, the
  DestinationRule sheds excess with fast Envoy 503s rather than queueing — the app
  itself never returned a 5xx in any test.
- **Reactive-scaling lag is the cost**: KEDA reacts to a 1–2 min rate window, so
  the brief 503 shedding + latency tail at each step is inherent, not a defect
  (event 0.56%, booking-api 0.15%).
- **The read path has huge headroom**: booking-api sustained ~560 RPS on 11 VUs
  with postgres at 0.14 cores.
- **Scale-down**: all scalers held at peak for the HPA's default 300s stabilization
  window, then returned to min — no flapping.
