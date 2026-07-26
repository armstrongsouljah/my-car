import TelemetryDeck from "@telemetrydeck/sdk";
import { getUser } from "@/lib/api";

const APP_ID = process.env.NEXT_PUBLIC_TELEMETRYDECK_APP_ID;
const ANONYMOUS_ID_KEY = "mycar_telemetry_anonymous_id";

let client = null;

// A shared "anonymous" clientUser would merge every signed-out visitor into
// one TelemetryDeck user — persist a distinct per-browser id instead.
function getAnonymousId() {
  let id = localStorage.getItem(ANONYMOUS_ID_KEY);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(ANONYMOUS_ID_KEY, id);
  }
  return id;
}

function currentClientUser() {
  return getUser()?.id || getAnonymousId();
}

// Lazily created singleton — undefined APP_ID (e.g. local dev without the
// var set) turns every call below into a no-op instead of throwing.
function getClient() {
  if (!APP_ID || typeof window === "undefined") return null;
  if (!client) {
    client = new TelemetryDeck({ appID: APP_ID, clientUser: currentClientUser() });
  }
  // Re-sync on every call so a login/logout/account switch since the client
  // was created doesn't keep attributing signals to a stale identity.
  client.clientUser = currentClientUser();
  return client;
}

export function trackSignal(type, payload) {
  try {
    return Promise.resolve(getClient()?.signal(type, payload)).catch(() => {});
  } catch {
    return Promise.resolve();
  }
}
