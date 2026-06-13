# Load Shedding — Design, Test Results, and Configuration

## Problem

Under extreme traffic spikes, accepting all requests while the system is saturated is worse than rejecting them. When the booking-worker pipeline backs up, HTTP latency climbs for all users rather than a subset receiving a fast error. This document records the load test campaign that established the capacity ceiling and the DestinationRule configuration that enforces it.

---

## Architecture: How the three layers interact

```
traffic spike
     │
     ▼
KEDA / HPA — expand capacity up to maxReplicaCount
     │
     ▼ (ceiling reached)
DestinationRule — reject excess traffic with 503 before it queues
     │
     ▼ (traffic within ceiling)
booking-worker pipeline — drains Redis stream at ~42 msg/s (6 replicas × 7/s)
```

- **KEDA** scales booking-api (max 8), booking-worker (max 6), and event-service (max 8) based on RPS and queue depth. It expands capacity reactively up to its ceiling.
- **HPA** covers auth-service (max 3) and payment-service (max 3). These are not in the hot path during load tests — auth-service is only hit at login, payment-service is gated by worker throughput.
- **DestinationRule** (new) protects the ceiling KEDA already established. Once replicas are maxed, without shedding, Envoy queues indefinitely — causing cascading latency across all users.

---

## Load Test Methodology

**Tool**: k6 running in a Docker container on a dedicated Ubuntu VM (192.168.0.63), outside the cluster.

**Script**: `load-test/k6-test.js`

**Flow per VU** (full booking flow):
1. GET seat-availability
2. POST queue/join
3. Poll GET queue/status until admitted (max 60s)
4. POST booking-requests
5. Poll GET booking-requests/{id} until confirmed (max 15s)

**Stage design**: Stepped ramp to capture the inflection point precisely.
```
1m ramp → 3m hold at 30% VUs
1m ramp → 3m hold at 60% VUs
1m ramp → 3m hold at 100% VUs
30s ramp-down
```
Each 3-minute hold gives KEDA enough time to fully scale and stabilize (KEDA polls every 15s). Results at each step reflect the **fully autoscaled** state, not a transient.

**Safety**: `abortOnFail: true` at 20% error rate stops the test before cascade.

**Data reset between runs**: Required — 10 test performances × 80 seats = 800 total seats per run.

---

## Results

| VUs | RPS | P95 latency | Failure rate | `booking_confirm_ms` p95 | Status |
|-----|-----|-------------|--------------|--------------------------|--------|
| 100 | 32  | 25ms        | 0%           | 1.06s                    | ✓ healthy |
| 300 | 98  | 95ms        | 0%           | 6.16s                    | ✓ healthy |
| 500 | 145 | **813ms** ❌ | 0%           | **15.11s**               | ✗ degraded |

### Key findings

**The ceiling is between 300 and 500 VUs (~98–145 RPS).**

The P95 jump from 95ms → 813ms at only a 1.67× VU increase (vs a clean 3.8× jump at 100→300) is the classic nonlinear inflection — something saturated.

**The bottleneck is the booking-worker pipeline, not the HTTP layer.**

`booking_confirm_ms` p95 grew: 1s → 6s → 15s. The HTTP failure rate stayed at 0% throughout — requests were being accepted and queued but the async worker couldn't drain them fast enough. KEDA had already scaled workers to max 6 replicas; raising `maxReplicaCount` would hit PostgreSQL connection limits.

**KEDA is not the problem, it's already at its ceiling.**

By the time each 3-minute hold period ended, KEDA had fully scaled. The 500 VU degradation is the true system ceiling with autoscaling active, not a scaling-lag artifact.

---

## DestinationRule Configuration

**File**: `manifest/booking/13-destination-rules.yaml`

### booking-api

```yaml
connectionPool:
  http:
    http1MaxPendingRequests: 100   # shed when >100 requests queue for a connection
    http2MaxRequests: 200
outlierDetection:
  consecutive5xxErrors: 5
  interval: 10s
  baseEjectionTime: 30s
  maxEjectionPercent: 50
```

**Why 100**: At 300 VUs (safe), concurrent requests to booking-api total ~2 (Little's Law: 98 RPS × 0.022s avg = 2.2). The threshold of 100 is far above safe-zone concurrency so it never triggers under normal load, while capping extreme spikes before they cascade into the worker queue.

### event-service

```yaml
connectionPool:
  http:
    http1MaxPendingRequests: 200
    http2MaxRequests: 400
outlierDetection:
  consecutive5xxErrors: 5
  interval: 10s
  baseEjectionTime: 30s
  maxEjectionPercent: 50
```

**Why higher than booking-api**: event-service is read-only (no writes, no async pipeline). It can absorb more concurrent load without cascading effects. Its KEDA threshold is also more conservative (60 RPS/replica vs 80 for booking-api).

### What the 503 UO means

When `http1MaxPendingRequests` is exceeded, Envoy returns `503` with the `x-envoy-overloaded` flag (`UO` in access logs). Clients receive a fast error rather than a slow timeout. The frontend should treat this as a "system busy, try again" signal.

---

## Data Reset Commands

Run before each load test to restore 800 seats and reset user points.

```bash
# booking_db
kubectl -n db exec deploy/postgres -- psql -U postgres -d booking_db -c "
  DELETE FROM bookings
  WHERE performance_id IN ('287','170','236','80','99','126','185','215','41','290')
    AND performance_date = '2026-07-01';"

kubectl -n db exec deploy/postgres -- psql -U postgres -d booking_db -c "
  DELETE FROM booking_requests
  WHERE performance_id IN ('287','170','236','80','99','126','185','215','41','290')
    AND show_date = '2026-07-01';"

# payment_db
K6_USERS=$(kubectl -n db exec deploy/postgres -- psql -U postgres -d auth_db -t -A -c \
  "SELECT string_agg(quote_literal(id), ',') FROM users WHERE provider = 'dev' AND login_id LIKE 'k6-vu-%';")
kubectl -n db exec deploy/postgres -- psql -U postgres -d payment_db -c "
  DELETE FROM payment_history WHERE user_id IN ($K6_USERS);
  UPDATE point_balances SET balance = 9999999, updated_at = now() WHERE user_id IN ($K6_USERS);"

# Redis
kubectl -n db exec deploy/redis -- redis-cli DEL booking.requests
kubectl -n db exec deploy/redis -- redis-cli XGROUP CREATE booking.requests booking-workers '$' MKSTREAM
kubectl -n db exec deploy/redis -- redis-cli DEL \
  queue:287:2026-07-01 queue:170:2026-07-01 queue:236:2026-07-01 \
  queue:80:2026-07-01  queue:99:2026-07-01  queue:126:2026-07-01 \
  queue:185:2026-07-01 queue:215:2026-07-01 queue:41:2026-07-01  \
  queue:290:2026-07-01
```

## Running the Load Test

From the Docker VM (`192.168.0.63`):

```bash
docker run --rm -i \
  --network host \
  -e K6_PROMETHEUS_RW_SERVER_URL=http://192.168.0.24:30428/api/v1/write \
  -e K6_PROMETHEUS_RW_TREND_STATS="p(50),p(95),p(99),min,max" \
  grafana/k6:latest run --out experimental-prometheus-rw - < ~/k6-test.js
```

Metrics stream live into VictoriaMetrics and appear in the Grafana k6 dashboard in real time.

**To change load level**: edit `TARGET_VUS` in `load-test/k6-test.js`. All stage targets and `NUM_USERS` derive from this single constant. Re-copy to the Docker VM before each run.
