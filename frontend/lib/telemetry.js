import TelemetryDeck from "@telemetrydeck/sdk";
import { getUser } from "@/lib/api";

const APP_ID = process.env.NEXT_PUBLIC_TELEMETRYDECK_APP_ID;

let client = null;

// Lazily created singleton — undefined APP_ID (e.g. local dev without the
// var set) turns every call below into a no-op instead of throwing.
function getClient() {
  if (!APP_ID || typeof window === "undefined") return null;
  if (!client) {
    client = new TelemetryDeck({
      appID: APP_ID,
      clientUser: getUser()?.id || "anonymous",
    });
  }
  return client;
}

export function trackSignal(type, payload) {
  getClient()?.signal(type, payload);
}
