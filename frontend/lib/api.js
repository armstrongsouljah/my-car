const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

// ── Token storage ─────────────────────────────────────────────────────────────
export function getTokens() {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem("mycar_tokens");
  return raw ? JSON.parse(raw) : null;
}

export function setTokens(tokens) {
  localStorage.setItem("mycar_tokens", JSON.stringify(tokens));
}

export function setUser(user) {
  localStorage.setItem("mycar_user", JSON.stringify(user));
}

export function getUser() {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem("mycar_user");
  return raw ? JSON.parse(raw) : null;
}

export function clearSession() {
  localStorage.removeItem("mycar_tokens");
  localStorage.removeItem("mycar_user");
}

export function isLoggedIn() {
  return !!getTokens()?.access;
}

// ── Fetch wrapper with automatic refresh ─────────────────────────────────────
async function refreshAccessToken() {
  const tokens = getTokens();
  if (!tokens?.refresh) return null;

  const response = await fetch(`${API_URL}/auth/token/refresh/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh: tokens.refresh }),
  });

  if (!response.ok) {
    clearSession();
    return null;
  }

  const data = await response.json();
  const updated = { access: data.access, refresh: data.refresh || tokens.refresh };
  setTokens(updated);
  return updated.access;
}

export async function api(path, { method = "GET", body, isForm = false } = {}) {
  const tokens = getTokens();
  const headers = {};
  if (tokens?.access) headers["Authorization"] = `Bearer ${tokens.access}`;
  if (body && !isForm) headers["Content-Type"] = "application/json";

  const doFetch = (accessToken) =>
    fetch(`${API_URL}${path}`, {
      method,
      headers: {
        ...headers,
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      },
      body: body ? (isForm ? body : JSON.stringify(body)) : undefined,
    });

  let response = await doFetch(tokens?.access);

  if (response.status === 401 && tokens?.refresh) {
    const newAccess = await refreshAccessToken();
    if (!newAccess) {
      if (typeof window !== "undefined") window.location.href = "/";
      throw new Error("Session expired");
    }
    response = await doFetch(newAccess);
  }

  if (response.status === 204) return null;

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const message =
      data?.detail ||
      (data && typeof data === "object" ? Object.values(data).flat().join(" ") : null) ||
      "Something went wrong";
    const error = new Error(message);
    error.status = response.status;
    error.data = data;
    throw error;
  }

  return data;
}
