const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001/api/v1";
// Prefer an explicit media origin when the API URL doesn't follow the
// `.../api/v{n}` convention (custom proxy path, versionless API, etc.) —
// falls back to stripping that suffix for the common case.
const API_ORIGIN = process.env.NEXT_PUBLIC_MEDIA_ORIGIN || API_URL.replace(/\/api\/v\d+\/?$/, "");

// Media files (car photos, inspection reports) come back as relative paths.
export function mediaUrl(path) {
  if (!path) return null;
  return path.startsWith("http") ? path : `${API_ORIGIN}${path}`;
}

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

// Attaches the current access token, retries once against a refreshed token
// on a 401, and redirects to /login if the refresh itself fails. Shared by
// api() (JSON) and downloadFile() (blob) so the auth/retry flow can't drift
// between the two.
async function fetchWithAuthRetry(path, options = {}) {
  const tokens = getTokens();
  const doFetch = (accessToken) =>
    fetch(`${API_URL}${path}`, {
      ...options,
      headers: {
        ...(options.headers || {}),
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      },
    });

  let response = await doFetch(tokens?.access);

  if (response.status === 401 && tokens?.refresh) {
    const newAccess = await refreshAccessToken();
    if (!newAccess) {
      if (typeof window !== "undefined") {
        const next = window.location.pathname + window.location.search;
        window.location.href = `/login?next=${encodeURIComponent(next)}`;
      }
      throw new Error("Session expired");
    }
    response = await doFetch(newAccess);
  }

  return response;
}

// Recursively collects every string leaf out of an error response body,
// however deeply nested -- a flat {field: ["msg"]} shape was the only case
// `Object.values(data).flat().join(" ")` handled correctly; one non-string
// value anywhere in there (e.g. a nested {code, detail} object) got
// coerced by .join() into the literal text "[object Object]" instead of
// throwing or falling back to the generic message (see #134).
function extractErrorMessages(value) {
  if (typeof value === "string") return [value];
  if (Array.isArray(value)) return value.flatMap(extractErrorMessages);
  if (value && typeof value === "object") return Object.values(value).flatMap(extractErrorMessages);
  return [];
}

export async function api(path, { method = "GET", body, isForm = false } = {}) {
  const headers = {};
  if (body && !isForm) headers["Content-Type"] = "application/json";

  const response = await fetchWithAuthRetry(path, {
    method,
    headers,
    body: body ? (isForm ? body : JSON.stringify(body)) : undefined,
  });

  if (response.status === 204) return null;

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const message =
      (typeof data?.detail === "string" && data.detail) ||
      extractErrorMessages(data).join(" ") ||
      "Something went wrong";
    const error = new Error(message);
    error.status = response.status;
    error.data = data;
    throw error;
  }

  return data;
}

// Binary downloads (PDFs, etc.) skip api()'s JSON parsing but reuse its
// token-refresh flow, then trigger a save via a throwaway object URL.
export async function downloadFile(path, filename) {
  const response = await fetchWithAuthRetry(path);

  if (!response.ok) throw new Error("Something went wrong");

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
