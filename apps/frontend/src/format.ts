const KO_DAYS = ["일", "월", "화", "수", "목", "금", "토"];

export function formatShowDate(s: string): string {
  const [y, m, d] = s.split("-").map(Number);
  const dow = new Date(y, m - 1, d).getDay();
  return `${y}년 ${m}월 ${d}일 (${KO_DAYS[dow]})`;
}

export function formatDateDot(s: string): string {
  return s.replace(/-/g, ".");
}

export function formatPeriod(start: string, end: string): string {
  return start === end ? formatDateDot(start) : `${formatDateDot(start)} - ${formatDateDot(end)}`;
}
