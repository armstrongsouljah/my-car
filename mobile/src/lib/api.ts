import { deleteItem, getItem, setItem } from '@/lib/storage';

// Ports frontend/lib/api.js's fetch-wrapper + token-refresh shape to native.
// Two real differences from the web version:
// - Token storage (see lib/storage.ts) is async (native Keychain/Keystore
//   access), so token reads/writes are all async here, unlike the web
//   frontend's synchronous localStorage — callers (see auth-context.tsx)
//   load tokens once on boot rather than reading them fresh on every render.
// - No `window.location` redirect-on-expired-session; auth-context.tsx's
//   state drives navigation instead (see its logout() call site).
const API_URL = process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8001/api/v1';
// Same "strip /api/v{n}" fallback as the web client — see frontend/lib/api.js.
const API_ORIGIN = process.env.EXPO_PUBLIC_MEDIA_ORIGIN || API_URL.replace(/\/api\/v\d+\/?$/, '');

const TOKENS_KEY = 'mycar_tokens';
const USER_KEY = 'mycar_user';

export type Tokens = { access: string; refresh: string };

export function mediaUrl(path?: string | null) {
  if (!path) return null;
  return path.startsWith('http') ? path : `${API_ORIGIN}${path}`;
}

// ── Token storage (expo-secure-store — Keychain on iOS, Keystore on Android;
// localStorage on web, see lib/storage.ts) ──────────────────────────────────
export async function getTokens(): Promise<Tokens | null> {
  const raw = await getItem(TOKENS_KEY);
  return raw ? JSON.parse(raw) : null;
}

export async function setTokens(tokens: Tokens) {
  await setItem(TOKENS_KEY, JSON.stringify(tokens));
}

export async function setUser(user: unknown) {
  await setItem(USER_KEY, JSON.stringify(user));
}

export async function getUser<T = unknown>(): Promise<T | null> {
  const raw = await getItem(USER_KEY);
  return raw ? JSON.parse(raw) : null;
}

export async function clearSession() {
  await deleteItem(TOKENS_KEY);
  await deleteItem(USER_KEY);
}

// ── Fetch wrapper with automatic refresh ─────────────────────────────────────
async function refreshAccessToken(): Promise<string | null> {
  const tokens = await getTokens();
  if (!tokens?.refresh) return null;

  const response = await fetch(`${API_URL}/auth/token/refresh/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh: tokens.refresh }),
  });

  if (!response.ok) {
    await clearSession();
    return null;
  }

  const data = await response.json();
  const updated = { access: data.access, refresh: data.refresh || tokens.refresh };
  await setTokens(updated);
  return updated.access;
}

type ApiOptions = {
  method?: string;
  body?: unknown;
  isForm?: boolean;
};

// Thrown when a 401 survives a refresh attempt — auth-context.tsx catches
// this specifically to drive the redirect-to-login (see its wrapped api calls).
export class SessionExpiredError extends Error {
  constructor() {
    super('Session expired');
  }
}

async function fetchWithAuthRetry(path: string, options: RequestInit = {}) {
  const tokens = await getTokens();
  const doFetch = (accessToken?: string | null) =>
    fetch(`${API_URL}${path}`, {
      ...options,
      headers: {
        ...(options.headers as Record<string, string> | undefined),
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      },
    });

  let response = await doFetch(tokens?.access);

  if (response.status === 401 && tokens?.refresh) {
    const newAccess = await refreshAccessToken();
    if (!newAccess) throw new SessionExpiredError();
    response = await doFetch(newAccess);
  }

  return response;
}

// Recursively collects every string leaf out of an error response body,
// however deeply nested -- mirrors frontend/lib/api.js's fix for the same
// bug (see #134): a flat {field: ["msg"]} shape was the only case
// Object.values(data).flat().join(' ') handled correctly; one non-string
// value anywhere in there got coerced into the literal text "[object
// Object]" instead of falling back to the generic message.
function extractErrorMessages(value: unknown): string[] {
  if (typeof value === 'string') return [value];
  if (Array.isArray(value)) return value.flatMap(extractErrorMessages);
  if (value && typeof value === 'object') return Object.values(value).flatMap(extractErrorMessages);
  return [];
}

export async function api(path: string, { method = 'GET', body, isForm = false }: ApiOptions = {}) {
  const headers: Record<string, string> = {};
  if (body && !isForm) headers['Content-Type'] = 'application/json';

  const response = await fetchWithAuthRetry(path, {
    method,
    headers,
    body: body ? (isForm ? (body as BodyInit) : JSON.stringify(body)) : undefined,
  });

  if (response.status === 204) return null;

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const message =
      (typeof data?.detail === 'string' && data.detail) ||
      extractErrorMessages(data).join(' ') ||
      'Something went wrong';
    const error = new Error(message) as Error & { status?: number; data?: unknown };
    error.status = response.status;
    error.data = data;
    throw error;
  }

  return data;
}
