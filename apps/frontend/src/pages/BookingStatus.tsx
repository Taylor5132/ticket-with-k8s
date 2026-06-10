import React, { useEffect, useMemo, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import type { BookingRequestState } from "../types";
import { formatShowDate } from "../format";

const failureMsg: Record<string, string> = {
  SEAT_ALREADY_BOOKED: "이미 예매된 좌석입니다. 다른 좌석을 선택해 주세요.",
  INSUFFICIENT_POINTS: "보유 포인트가 부족합니다. 다른 좌석을 선택하거나 포인트가 많은 데모 사용자로 로그인해 주세요.",
  PAYMENT_FAILED: "결제 처리 중 문제가 발생했습니다. 잠시 후 다시 시도해 주세요.",
  WORKER_ERROR: "예매 처리 중 문제가 발생했습니다. 잠시 후 다시 시도해 주세요.",
};

export default function BookingStatus() {
  const { token } = useAuth();
  const [searchParams] = useSearchParams();
  const requestIds = useMemo(
    () => (searchParams.get("ids") ?? "").split(",").filter(Boolean),
    [searchParams]
  );
  const [states, setStates] = useState<Record<string, BookingRequestState>>({});
  const stoppedRef = useRef(false);

  useEffect(() => {
    if (requestIds.length === 0 || !token) return;
    stoppedRef.current = false;
    const poll = async () => {
      if (stoppedRef.current) return;
      try {
        const results = await Promise.all(
          requestIds.map((rid) => api<BookingRequestState>(`/api/booking-requests/${rid}`, token))
        );
        const next: Record<string, BookingRequestState> = {};
        for (const r of results) next[r.request_id] = r;
        setStates(next);
        if (results.every((r) => r.status === "CONFIRMED" || r.status === "FAILED")) {
          stoppedRef.current = true;
        }
      } catch {}
    };
    poll();
    const timer = setInterval(poll, 1000);
    return () => { stoppedRef.current = true; clearInterval(timer); };
  }, [requestIds, token]);

  const results = Object.values(states);
  const allDone = results.length === requestIds.length &&
    results.every((r) => r.status === "CONFIRMED" || r.status === "FAILED");
  const confirmed = results.filter((r) => r.status === "CONFIRMED");
  const failed = results.filter((r) => r.status === "FAILED");

  if (!allDone || results.length === 0) {
    return (
      <section className="statusPage">
        <div className="spinner" />
        <h1>예매 요청 처리 중입니다</h1>
        <p>좌석과 포인트를 확인하고 있습니다. 잠시만 기다려 주세요.</p>
      </section>
    );
  }

  if (confirmed.length === requestIds.length) {
    return (
      <section className="statusPage">
        <div className="statusIcon success">✓</div>
        <h1>예매가 완료되었습니다</h1>
        {confirmed[0]?.show_date && <p className="statusDate">{formatShowDate(confirmed[0].show_date)}</p>}
        <p>{requestIds.length > 1 ? `${requestIds.length}석 모두 예매가 완료되었습니다.` : "마이페이지에서 예매내역과 결제내역을 확인할 수 있습니다."}</p>
        <div className="statusActions">
          <Link className="button primary" to="/mypage">마이페이지에서 확인</Link>
          <Link className="button" to="/">공연 목록으로</Link>
        </div>
      </section>
    );
  }

  return (
    <section className="statusPage">
      <div className="statusIcon failure">✕</div>
      <h1>{confirmed.length > 0 ? "일부 예매에 실패했습니다" : "예매에 실패했습니다"}</h1>
      {confirmed.length > 0 && <p>{confirmed.length}석은 예매가 완료되었습니다.</p>}
      <p>{failureMsg[failed[0]?.failure_reason ?? ""] ?? "알 수 없는 문제로 예매에 실패했습니다."}</p>
      <div className="statusActions">
        <Link className="button primary" to="/">공연 목록으로</Link>
      </div>
    </section>
  );
}
