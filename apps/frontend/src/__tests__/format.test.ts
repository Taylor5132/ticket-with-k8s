import { describe, it, expect } from "vitest";
import { formatShowDate, formatDateDot, formatPeriod } from "../format";

describe("formatShowDate", () => {
  it("날짜를 한국어 요일과 함께 포맷한다", () => {
    expect(formatShowDate("2026-07-01")).toBe("2026년 7월 1일 (수)");
  });

  it("일요일을 올바르게 포맷한다", () => {
    expect(formatShowDate("2026-07-05")).toBe("2026년 7월 5일 (일)");
  });

  it("토요일을 올바르게 포맷한다", () => {
    expect(formatShowDate("2026-07-04")).toBe("2026년 7월 4일 (토)");
  });

  it("월을 한 자리로 표시한다", () => {
    expect(formatShowDate("2026-01-01")).toBe("2026년 1월 1일 (목)");
  });
});

describe("formatDateDot", () => {
  it("하이픈을 점으로 변환한다", () => {
    expect(formatDateDot("2026-07-01")).toBe("2026.07.01");
  });

  it("하이픈이 여러 개여도 모두 변환한다", () => {
    expect(formatDateDot("2026-12-31")).toBe("2026.12.31");
  });
});

describe("formatPeriod", () => {
  it("시작일과 종료일이 같으면 단일 날짜를 반환한다", () => {
    expect(formatPeriod("2026-07-01", "2026-07-01")).toBe("2026.07.01");
  });

  it("시작일과 종료일이 다르면 범위를 반환한다", () => {
    expect(formatPeriod("2026-07-01", "2026-07-31")).toBe("2026.07.01 - 2026.07.31");
  });
});
