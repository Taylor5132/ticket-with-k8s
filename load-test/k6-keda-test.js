// k6 KEDA scaler test — Booking App
// =====================================================================
// Purpose: drive ONE KEDA ScaledObject at a time to its scaling ceiling
// and observe replicas grow. Companion to k6-test.js (system-ceiling /
// DestinationRule test); this one isolates the autoscaler triggers.
//
// Select a scenario with the SCENARIO env var (only one runs per invocation):
//   SCENARIO=event        → event-service  (Prometheus RPS, threshold 60/replica, min2 max8)
//   SCENARIO=booking-api  → booking-api    (Prometheus RPS 80/replica + P95 latency, min2 max8)
//   SCENARIO=worker       → booking-worker + admission-worker (Redis stream backlog)
//
// KEDA math: desiredReplicas = ceil(metricValue / threshold), where
// metricValue is the WHOLE query result (e.g. total RPS, total stream pending).
//   event-service : ceil(totalRPS / 60)   → >120 RPS leaves min 2; ~480 → max 8
//   booking-api   : ceil(totalRPS / 80)   → >160 RPS leaves min 2; ~640 → max 8
//                   AND ceil(P95_seconds / 0.1) fires independently
//   booking-worker: ceil(streamPending / 10) → >20 pending leaves min 2; >60 → max 6
//
// Run from the Docker VM (192.168.0.63), streaming metrics to VictoriaMetrics:
//   docker run --rm -i --network host \
//     -e SCENARIO=event \
//     -e K6_PROMETHEUS_RW_SERVER_URL=http://192.168.0.24:30428/api/v1/write \
//     -e K6_PROMETHEUS_RW_TREND_STATS="p(50),p(95),p(99),min,max" \
//     grafana/k6:latest run --out experimental-prometheus-rw - < ~/k6-keda-test.js
//
// Watch scaling in another terminal:
//   watch -n2 'kubectl get hpa,scaledobject -n backend; echo; kubectl get pods -n backend -o wide | grep -E "event-service|booking-api|booking-worker|admission-worker"'
//
// NOTE on `worker`: it submits real bookings → run the data-reset commands
// in docs/ops/LOAD_SHEDDING.md before AND after. `event` and `booking-api`
// are pure reads (no writes, no reset needed).
// =====================================================================

import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";

// ── Custom metrics ──────────────────────────────────────────────────
const bookingConfirmedRate = new Rate("booking_confirmed");
const queueWaitMs          = new Trend("queue_wait_ms",      true);
const bookingConfirmMs     = new Trend("booking_confirm_ms", true);

// ── Config ──────────────────────────────────────────────────────────
const BASE_URL  = __ENV.BASE_URL || "http://192.168.0.100";
const SCENARIO  = __ENV.SCENARIO || "event";

// 10 future performances on 2026-07-01 (80 fresh seats each)
const PERFS     = ["287","170","236","80","99","126","185","215","41","290"];
const SHOW_DATE = "2026-07-01";

// Token pool size — only `booking-api` and `worker` need auth.
const TOKEN_POOL = SCENARIO === "event" ? 0 : 120;

// ── Scenario definitions ─────────────────────────────────────────────
// Each uses constant/ramping-arrival-rate so we control RPS directly —
// RPS is the exact quantity KEDA's Prometheus triggers measure.
const SCENARIOS = {
  // event-service: ceil(RPS/60). Walk 2→3→5→8 replicas.
  event: {
    executor: "ramping-arrival-rate",
    startRate: 0,
    timeUnit: "1s",
    preAllocatedVUs: 200,
    maxVUs: 600,
    stages: [
      { duration: "1m", target: 80  },  // warm-up, stays at min 2
      { duration: "3m", target: 80  },
      { duration: "1m", target: 150 },  // → ~3 replicas
      { duration: "3m", target: 150 },
      { duration: "1m", target: 300 },  // → ~5 replicas
      { duration: "3m", target: 300 },
      { duration: "1m", target: 480 },  // → max 8 replicas
      { duration: "3m", target: 480 },
      { duration: "30s", target: 0   },
    ],
    exec: "eventLoad",
  },

  // booking-api: ceil(RPS/80) + latency trigger. Walk 2→3→5→7 replicas.
  "booking-api": {
    executor: "ramping-arrival-rate",
    startRate: 0,
    timeUnit: "1s",
    preAllocatedVUs: 200,
    maxVUs: 700,
    stages: [
      { duration: "1m", target: 120 },  // min 2
      { duration: "3m", target: 120 },
      { duration: "1m", target: 240 },  // → 3
      { duration: "3m", target: 240 },
      { duration: "1m", target: 400 },  // → 5
      { duration: "3m", target: 400 },
      { duration: "1m", target: 560 },  // → 7
      { duration: "3m", target: 560 },
      { duration: "30s", target: 0   },
    ],
    exec: "bookingApiLoad",
  },

  // booking-worker + admission-worker: build a Redis stream backlog.
  // Full booking flow at sustained concurrency pushes booking-requests
  // faster than ~13 msg/s drain (2 replicas × ~6.5/s) → pending climbs.
  worker: {
    executor: "ramping-vus",
    startVUs: 0,
    stages: [
      { duration: "1m", target: 60  },
      { duration: "5m", target: 60  },  // hold — let backlog accumulate
      { duration: "1m", target: 120 },
      { duration: "5m", target: 120 },  // push harder
      { duration: "30s", target: 0  },
    ],
    exec: "workerLoad",
  },
};

if (!SCENARIOS[SCENARIO]) {
  throw new Error(`Unknown SCENARIO="${SCENARIO}". Use one of: ${Object.keys(SCENARIOS).join(", ")}`);
}

export const options = {
  scenarios: { [SCENARIO]: SCENARIOS[SCENARIO] },
  thresholds: {
    // Keep a hard cutoff so a misconfigured run can't hammer the cluster forever.
    http_req_failed: [{ threshold: "rate<0.30", abortOnFail: true }],
  },
};

// ── setup(): login token pool (only when a scenario needs auth) ──────
export function setup() {
  const tokens = [];
  for (let i = 1; i <= TOKEN_POOL; i++) {
    const res = http.post(
      `${BASE_URL}/api/auth/dev-login`,
      JSON.stringify({ provider: "dev", login_id: `k6-vu-${i}`, display_name: `K6 VU ${i}` }),
      { headers: { "Content-Type": "application/json" } }
    );
    check(res, { "login 200": (r) => r.status === 200 });
    if (res.status === 200) tokens.push(res.json("access_token"));
  }
  return { tokens };
}

// ── event-service load: pure public GETs, no auth, no writes ─────────
export function eventLoad() {
  const perfId = PERFS[(__VU - 1) % PERFS.length];
  // Mix the JOIN-heavy listing with the single-row detail lookup.
  if (__ITER % 2 === 0) {
    const r = http.get(`${BASE_URL}/api/performances`);
    check(r, { "perf-list 200": (x) => x.status === 200 });
  } else {
    const r = http.get(`${BASE_URL}/api/performances/${perfId}`);
    check(r, { "perf-detail 200": (x) => x.status === 200 });
  }
}

// ── booking-api load: seat-availability read (routes to booking-api) ─
export function bookingApiLoad(data) {
  const token  = data.tokens[(__VU - 1) % data.tokens.length];
  const perfId = PERFS[(__VU - 1) % PERFS.length];
  const r = http.get(
    `${BASE_URL}/api/performances/${perfId}/seat-availability?show_date=${SHOW_DATE}`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
  check(r, { "seat-avail 200": (x) => x.status === 200 });
}

// ── worker load: full booking flow to build Redis stream backlog ─────
export function workerLoad(data) {
  const token  = data.tokens[(__VU - 1) % data.tokens.length];
  const perfId = PERFS[(__VU - 1) % PERFS.length];
  const authHdr = { headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" } };

  const availRes = http.get(
    `${BASE_URL}/api/performances/${perfId}/seat-availability?show_date=${SHOW_DATE}`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
  if (!check(availRes, { "seat-avail 200": (r) => r.status === 200 })) { sleep(1); return; }
  const seats = availRes.json("seats").filter((s) => s.status === "AVAILABLE");
  if (seats.length === 0) { sleep(2); return; }
  const seat = seats[(__VU - 1) % seats.length];

  const queueStart = Date.now();
  const joinRes = http.post(
    `${BASE_URL}/api/queue/join?performance_id=${perfId}&show_date=${SHOW_DATE}`,
    null, authHdr
  );
  if (!check(joinRes, { "queue join 200": (r) => r.status === 200 })) { sleep(1); return; }
  let admitted = joinRes.json("position") <= 1;

  const queueDeadline = Date.now() + 60000;
  while (!admitted && Date.now() < queueDeadline) {
    sleep(2);
    const statusRes = http.get(
      `${BASE_URL}/api/queue/status?performance_id=${perfId}&show_date=${SHOW_DATE}`,
      authHdr
    );
    if (statusRes.status === 200) admitted = statusRes.json("admitted") === true;
  }
  queueWaitMs.add(Date.now() - queueStart);
  if (!admitted) { sleep(1); return; }

  const bookStart = Date.now();
  const bookRes = http.post(
    `${BASE_URL}/api/booking-requests`,
    JSON.stringify({ performance_id: perfId, seat_id: seat.seat_id, show_date: SHOW_DATE }),
    authHdr
  );
  if (!check(bookRes, { "book request 200": (r) => r.status === 200 })) { sleep(1); return; }
  const requestId = bookRes.json("request_id");

  const bookDeadline = Date.now() + 15000;
  let finalStatus = "PENDING";
  while (finalStatus === "PENDING" && Date.now() < bookDeadline) {
    sleep(1);
    const pollRes = http.get(`${BASE_URL}/api/booking-requests/${requestId}`, authHdr);
    if (pollRes.status === 200) finalStatus = pollRes.json("status");
  }
  bookingConfirmMs.add(Date.now() - bookStart);
  bookingConfirmedRate.add(finalStatus === "CONFIRMED");
  sleep(1);
}
