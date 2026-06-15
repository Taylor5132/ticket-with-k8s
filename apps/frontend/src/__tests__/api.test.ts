import { describe, it, expect, vi, beforeEach } from "vitest";
import { api } from "../api";

const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

beforeEach(() => {
  mockFetch.mockReset();
});

describe("api", () => {
  it("성공 응답이면 JSON을 반환한다", async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({ data: "test" }),
    });
    const result = await api("/test");
    expect(result).toEqual({ data: "test" });
  });

  it("token이 있으면 Authorization 헤더를 포함한다", async () => {
    mockFetch.mockResolvedValue({ ok: true, json: async () => ({}) });
    await api("/test", "my-token");
    expect(mockFetch).toHaveBeenCalledWith(
      "/test",
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: "Bearer my-token" }),
      })
    );
  });

  it("token이 없으면 Authorization 헤더를 포함하지 않는다", async () => {
    mockFetch.mockResolvedValue({ ok: true, json: async () => ({}) });
    await api("/test");
    const headers = mockFetch.mock.calls[0][1].headers;
    expect(headers).not.toHaveProperty("Authorization");
  });

  it("오류 응답에서 detail.message로 에러를 던진다", async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 400,
      json: async () => ({ detail: { message: "잘못된 요청", code: "BAD_REQUEST" } }),
    });
    await expect(api("/test")).rejects.toThrow("잘못된 요청");
  });

  it("에러 객체에 status와 code를 설정한다", async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 403,
      json: async () => ({ detail: { message: "권한 없음", code: "FORBIDDEN" } }),
    });
    try {
      await api("/test");
    } catch (e: any) {
      expect(e.status).toBe(403);
      expect(e.code).toBe("FORBIDDEN");
    }
  });

  it("detail이 없으면 기본 메시지로 에러를 던진다", async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => ({}),
    });
    await expect(api("/test")).rejects.toThrow(
      "문제가 발생했습니다. 잠시 후 다시 시도해 주세요."
    );
  });

  it("JSON 파싱 실패 시 기본 메시지로 에러를 던진다", async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => { throw new Error("parse error"); },
    });
    await expect(api("/test")).rejects.toThrow(
      "문제가 발생했습니다. 잠시 후 다시 시도해 주세요."
    );
  });

  it("init 옵션을 fetch에 전달한다", async () => {
    mockFetch.mockResolvedValue({ ok: true, json: async () => ({}) });
    await api("/test", undefined, { method: "POST", body: JSON.stringify({ x: 1 }) });
    expect(mockFetch).toHaveBeenCalledWith(
      "/test",
      expect.objectContaining({ method: "POST" })
    );
  });
});
