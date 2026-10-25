const TOKEN_KEY = "af_access";
const REFRESH_KEY = "af_refresh";

export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/+$/, "");

export function toApiUrl(path: string): string {
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  if (!API_BASE_URL) return path;
  return `${API_BASE_URL}${path.startsWith("/") ? "" : "/"}${path}`;
}

export const getApiUrl = toApiUrl;

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setTokens(access: string, refresh: string) {
  localStorage.setItem(TOKEN_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
}

export function clearTokens() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (!headers.has("Content-Type") && init.body) headers.set("Content-Type", "application/json");
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const res = await fetch(toApiUrl(path), { ...init, headers });
  if (res.status === 401 && localStorage.getItem(REFRESH_KEY) && path !== "/api/v1/auth/refresh") {
    const refreshed = await fetch(toApiUrl("/api/v1/auth/refresh"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: localStorage.getItem(REFRESH_KEY) }),
    });
    if (refreshed.ok) {
      const data = (await refreshed.json()) as { access_token: string; refresh_token: string };
      setTokens(data.access_token, data.refresh_token);
      return request<T>(path, init);
    }
    clearTokens();
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail ?? body);
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  if (res.status === 204) return undefined as T;
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return res.json() as Promise<T>;
  return res as unknown as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) => request<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  put: <T>(path: string, body?: unknown) => request<T>(path, { method: "PUT", body: body ? JSON.stringify(body) : undefined }),
};

export type AuthUser = {
  id: number;
  email: string;
  full_name: string;
  role: string;
  role_name: string;
  region_id: number | null;
  region_name: string | null;
  institution_id: number | null;
  institution_name: string | null;
  demo: boolean;
};

export const ROLE_LABELS: Record<string, string> = {
  super_admin: "Super Admin",
  bureau_officer: "Bureau Officer",
  regional_officer: "Regional Officer",
  committee_member: "Committee Member",
  institution_user: "Institution User",
};

export const DEMO_ROLES = [
  { email: "super@approveflow.demo", role: "super_admin", label: "Super Admin" },
  { email: "bureau@approveflow.demo", role: "bureau_officer", label: "Bureau Officer" },
  { email: "regional@approveflow.demo", role: "regional_officer", label: "Regional Officer" },
  { email: "committee@approveflow.demo", role: "committee_member", label: "Committee Member" },
  { email: "institution@approveflow.demo", role: "institution_user", label: "Institution" },
];

export const DEMO_PASSWORD = "Demo@123";
