// k6 load test — Booking App full flow
// Run from Docker VM:
//   export K6_PROMETHEUS_RW_SERVER_URL=http://192.168.0.24:30428/api/v1/write
//   export K6_PROMETHEUS_RW_TREND_STATS=p(50),p(95),p(99),min,max
//   k6 run --out experimental-prometheus-rw k6-test.js

import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";

// ── Custom metrics ──────────────────────────────────────────────────
const bookingConfirmedRate = new Rate("booking_confirmed");
const queueWaitMs          = new Trend("queue_wait_ms",    true);
const bookingConfirmMs     = new Trend("booking_confirm_ms", true);

// ── Config ──────────────────────────────────────────────────────────
const BASE_URL   = "http://192.168.0.100";
const TARGET_VUS = 100;   // single knob — change this per run (30 → 60 → 100)
const NUM_USERS  = TARGET_VUS;

// 10 future performances all on 2026-07-01 (80 fresh seats each)
const PERFS = ["287","170","236","80","99","126","185","215","41","290"];
const SHOW_DATE = "2026-07-01";

export const options = {
  scenarios: {
    booking_flow: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: [
        { duration: "1m",  target: Math.round(TARGET_VUS * 0.3) },  // step 1: 30%
        { duration: "3m",  target: Math.round(TARGET_VUS * 0.3) },  // hold
        { duration: "1m",  target: Math.round(TARGET_VUS * 0.6) },  // step 2: 60%
        { duration: "3m",  target: Math.round(TARGET_VUS * 0.6) },  // hold
        { duration: "1m",  target: TARGET_VUS },                    // step 3: 100%
        { duration: "3m",  target: TARGET_VUS },                    // hold
        { duration: "30s", target: 0 },
      ],
    },
  },
  thresholds: {
    "http_req_duration{status:200}": ["p(95)<500"],
    http_req_failed: [
      "rate<0.01",
      { threshold: "rate<0.20", abortOnFail: true },  // hard stop before cascade
    ],
  },
};

// ── setup(): login all VU users, return tokens[] ────────────────────
export function setup() {
  const tokens = [];
  for (let i = 1; i <= NUM_USERS; i++) {
    const res = http.post(
      `${BASE_URL}/api/auth/dev-login`,
      JSON.stringify({ provider: "dev", login_id: `k6-vu-${i}`, display_name: `K6 VU ${i}` }),
      { headers: { "Content-Type": "application/json" } }
    );
    check(res, { "login 200": (r) => r.status === 200 });
    tokens.push(res.json("access_token"));
  }
  return { tokens };
}

// ── default: one full booking attempt per iteration ─────────────────
export default function (data) {
  const token = data.tokens[(__VU - 1) % NUM_USERS];
  const perfId = PERFS[(__VU - 1) % PERFS.length];
  const authHdr = { headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" } };

  // 1. Get seat availability
  const availRes = http.get(
    `${BASE_URL}/api/performances/${perfId}/seat-availability?show_date=${SHOW_DATE}`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
  if (!check(availRes, { "seat-avail 200": (r) => r.status === 200 })) {
    sleep(1);
    return;
  }
  const seats = availRes.json("seats").filter((s) => s.status === "AVAILABLE");
  if (seats.length === 0) {
    // All seats filled for this performance/date — skip
    sleep(2);
    return;
  }
  // Pick a seat based on VU number to minimize contention
  const seat = seats[(__VU - 1) % seats.length];

  // 2. Join queue
  const queueStart = Date.now();
  const joinRes = http.post(
    `${BASE_URL}/api/queue/join?performance_id=${perfId}&show_date=${SHOW_DATE}`,
    null,
    authHdr
  );
  if (!check(joinRes, { "queue join 200": (r) => r.status === 200 })) {
    sleep(1);
    return;
  }
  let admitted = joinRes.json("position") <= 1;

  // 3. Poll queue until admitted (max 60s)
  const queueDeadline = Date.now() + 60000;
  while (!admitted && Date.now() < queueDeadline) {
    sleep(2);
    const statusRes = http.get(
      `${BASE_URL}/api/queue/status?performance_id=${perfId}&show_date=${SHOW_DATE}`,
      authHdr
    );
    if (statusRes.status === 200) {
      admitted = statusRes.json("admitted") === true;
    }
  }
  queueWaitMs.add(Date.now() - queueStart);

  if (!admitted) {
    sleep(1);
    return;
  }

  // 4. Submit booking request
  const bookStart = Date.now();
  const bookRes = http.post(
    `${BASE_URL}/api/booking-requests`,
    JSON.stringify({ performance_id: perfId, seat_id: seat.seat_id, show_date: SHOW_DATE }),
    authHdr
  );
  if (!check(bookRes, { "book request 200": (r) => r.status === 200 })) {
    sleep(1);
    return;
  }
  const requestId = bookRes.json("request_id");

  // 5. Poll booking status (max 15s)
  const bookDeadline = Date.now() + 15000;
  let finalStatus = "PENDING";
  while (finalStatus === "PENDING" && Date.now() < bookDeadline) {
    sleep(1);
    const pollRes = http.get(`${BASE_URL}/api/booking-requests/${requestId}`, authHdr);
    if (pollRes.status === 200) {
      finalStatus = pollRes.json("status");
    }
  }
  bookingConfirmMs.add(Date.now() - bookStart);
  bookingConfirmedRate.add(finalStatus === "CONFIRMED");

  sleep(1);
}
