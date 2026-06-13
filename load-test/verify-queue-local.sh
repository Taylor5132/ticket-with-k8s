#!/usr/bin/env bash
# 대기열 파이프라인 로컬 검증 — Ubuntu VM(docker 사용 가능 환경)에서 실행.
#   1) docker compose up --build -d   로 전체 스택을 먼저 띄운 뒤
#   2) bash load-test/verify-queue-local.sh
#
# 검증 흐름: 줄서기(join) → Dispatcher가 줄에서 빼기 → admission-worker가 토큰 발급
#            → status가 admitted → 토큰 게이트 통과해 예매요청 성공 / 토큰 없으면 403
set -euo pipefail

BASE="${BASE:-http://localhost:8004}"   # booking-api
PERF="${PERF:-1}"
DATE="${DATE:-2026-07-01}"

echo "== 0. 테스트 유저 토큰 발급 (auth dev-login) =="
TOKEN=$(curl -s -X POST http://localhost:8001/auth/dev-login \
  -H 'Content-Type: application/json' \
  -d '{"provider":"dev","login_id":"queue-tester","display_name":"큐테스터"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
AUTH=(-H "Authorization: Bearer $TOKEN")
echo "  JWT 확보 완료"

echo "== 1. 토큰 없이 예매요청 → 403 기대 (게이트 동작 확인) =="
code=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$BASE/booking-requests" "${AUTH[@]}" \
  -H 'Content-Type: application/json' \
  -d "{\"performance_id\":\"$PERF\",\"seat_id\":\"A-1\",\"show_date\":\"$DATE\"}")
echo "  HTTP $code  ($([ "$code" = 403 ] && echo '✓ 게이트가 막음' || echo '✗ 게이트 안 막힘'))"

echo "== 2. 대기열 진입 (queue/join) =="
curl -s -X POST "$BASE/queue/join?performance_id=$PERF&show_date=$DATE" "${AUTH[@]}"; echo

echo "== 3. Dispatcher+Worker가 처리할 때까지 status 폴링 (최대 15초) =="
for i in $(seq 1 15); do
  resp=$(curl -s "$BASE/queue/status?performance_id=$PERF&show_date=$DATE" "${AUTH[@]}")
  echo "  [$i] $resp"
  if echo "$resp" | grep -q '"admitted": *true'; then echo "  ✓ 입장 허가됨 (토큰 발급 확인)"; break; fi
  sleep 1
done

echo "== 4. 토큰 보유 상태로 예매요청 → 200 기대 =="
code=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$BASE/booking-requests" "${AUTH[@]}" \
  -H 'Content-Type: application/json' \
  -d "{\"performance_id\":\"$PERF\",\"seat_id\":\"A-1\",\"show_date\":\"$DATE\"}")
echo "  HTTP $code  ($([ "$code" = 200 ] && echo '✓ 게이트 통과해 예매 접수' || echo '✗ 실패'))"

echo "== 완료 =="
