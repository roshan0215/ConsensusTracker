function resolveApiBase() {
  // In local dev, prefer same-origin + Next rewrites to avoid CORS entirely.
  if (typeof window !== "undefined") {
    const host = window.location.hostname;
    if (host === "localhost" || host === "127.0.0.1") return "";
  }
  return process.env.NEXT_PUBLIC_API_BASE_URL || "";
}

export function getToken() {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem("ct_access_token");
}

export function setToken(token) {
  window.localStorage.setItem("ct_access_token", token);
}

export function clearToken() {
  window.localStorage.removeItem("ct_access_token");
}

export async function apiFetch(path, { method = "GET", body, auth = true } = {}) {
  const API_BASE = resolveApiBase();
  const headers = { "Content-Type": "application/json" };
  if (auth) {
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (res.status === 401 && typeof window !== "undefined") {
    // Token missing/expired (common after backend restart if SECRET_KEY changed).
    clearToken();
    if (!window.location.pathname.startsWith("/signin")) {
      window.location.href = "/signin";
    }
  }
  const text = await res.text();
  let json;
  try {
    json = text ? JSON.parse(text) : null;
  } catch {
    json = null;
  }
  if (!res.ok) {
    const msg = json?.detail || json?.message || text || `HTTP ${res.status}`;
    throw new Error(msg);
  }
  return json;
}
