export async function api<T>(path: string, token?: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init?.headers ?? {}),
    },
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    const err = new Error(
      error?.detail?.message ?? error?.message ?? "문제가 발생했습니다. 잠시 후 다시 시도해 주세요.",
    ) as Error & { status?: number; code?: string };
    err.status = response.status;
    err.code = error?.detail?.code ?? error?.code;  // 예: NO_ADMISSION_TOKEN
    throw err;
  }
  return response.json();
}
