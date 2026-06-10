export type User = {
  id: string;
  provider: string;
  login_id: string;
  display_name: string;
};

export type PerformanceSummary = {
  id: string;
  title: string;
  poster_url: string | null;
  venue_name: string;
  area: string;
  genre: string;
  start_date: string;
  end_date: string;
  status: string;
};

export type Seat = {
  seat_id: string;
  row: string;
  number: number;
  grade: string;
  price: number;
  status: "AVAILABLE" | "OCCUPIED";
};

export type BookingRequestState = {
  request_id: string;
  status: "PENDING" | "PROCESSING" | "CONFIRMED" | "FAILED";
  failure_reason?: string;
  show_date?: string;
};
