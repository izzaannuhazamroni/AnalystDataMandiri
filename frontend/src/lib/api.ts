import { getSupabase } from "./supabase";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init: { method?: string; body?: unknown }, token?: string): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API}${path}`, {
      method: init.method ?? "GET",
      headers: {
        ...(init.body ? { "Content-Type": "application/json" } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: init.body ? JSON.stringify(init.body) : undefined,
    });
  } catch {
    throw new Error("Tidak dapat terhubung ke server analitik. Pastikan backend berjalan.");
  }
  if (!res.ok) {
    let detail = `Permintaan gagal (${res.status})`;
    try {
      const j = await res.json();
      if (typeof j.detail === "string") detail = j.detail;
      else if (Array.isArray(j.detail)) detail = "Input tidak valid.";
    } catch {
      /* abaikan */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

/** Request terautentikasi (JWT Supabase). */
export async function api<T>(path: string, init: { method?: string; body?: unknown } = {}): Promise<T> {
  const { data } = await getSupabase().auth.getSession();
  const token = data.session?.access_token;
  if (!token) throw new Error("Sesi berakhir. Silakan login ulang.");
  return request<T>(path, init, token);
}

/** Request publik (halaman share, read-only). */
export function publicApi<T>(path: string, init: { method?: string; body?: unknown } = {}): Promise<T> {
  return request<T>(path, init);
}
