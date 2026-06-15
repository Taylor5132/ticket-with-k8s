import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { Banner } from "../components";

vi.mock("../api", () => ({
  api: vi.fn(),
}));

import { api } from "../api";
const mockApi = vi.mocked(api);

const mockPerformance = {
  id: "72",
  title: "테스트 공연",
  poster_url: "http://example.com/poster.jpg",
  venue_name: "테스트 홀",
  area: "서울",
  genre: "뮤지컬",
  start_date: "2026-07-01",
  end_date: "2026-07-31",
  status: "공연중",
};

afterEach(() => {
  vi.clearAllMocks();
});

describe("Banner", () => {
  it("초기 렌더링 시 null을 반환한다", () => {
    mockApi.mockImplementation(() => new Promise(() => {}));
    const { container } = render(
      <MemoryRouter>
        <Banner />
      </MemoryRouter>
    );
    expect(container.firstChild).toBeNull();
  });

  it("데이터 로드 후 공연 정보를 렌더링한다", async () => {
    mockApi.mockResolvedValue({ items: [mockPerformance] });
    render(
      <MemoryRouter>
        <Banner />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByText("테스트 공연")).toBeInTheDocument();
    });
    expect(screen.getByText("뮤지컬")).toBeInTheDocument();
    expect(screen.getByText("테스트 홀 · 서울")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "자세히 보기" })).toHaveAttribute(
      "href",
      "/performances/72"
    );
  });

  it("API 오류 시 null을 유지한다", async () => {
    mockApi.mockRejectedValue(new Error("network error"));
    const { container } = render(
      <MemoryRouter>
        <Banner />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(container.firstChild).toBeNull();
    });
  });

  it("PINNED_IDS에 없는 id는 목록에서 제외한다", async () => {
    mockApi.mockResolvedValue({
      items: [{ ...mockPerformance, id: "9999" }],
    });
    const { container } = render(
      <MemoryRouter>
        <Banner />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(container.firstChild).toBeNull();
    });
  });
});
