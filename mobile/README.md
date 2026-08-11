# GlavBox mobile (React Native + Expo)

Native Android/iOS client for GlavBox/my-car — a separate codebase from
`../frontend/` (the Next.js PWA), sharing the same Django REST API
(`../api/`) as-is. See issue #101 for the full background/decision log.

## Stack

- Expo SDK 57 (managed workflow), TypeScript, `expo-router` (file-based
  routing under `src/app/`).
- Auth: JWT against `../api/`'s existing `/auth/login/` +
  `/auth/token/refresh/` endpoints, tokens in `expo-secure-store`
  (Keychain/Keystore on native; falls back to `localStorage` on the web
  target, which has no SecureStore implementation — see `src/lib/storage.ts`).
- Navigation: standard `expo-router` `Tabs` (Garage / Reminders / Expenses /
  Settings) — deliberately not the template's default
  `expo-router/unstable-native-tabs`, which Expo itself flags as unstable.

## Getting started

```bash
npm install
# .env is already committed with a working local default -- see its
# comments about localhost vs 10.0.2.2 vs your LAN IP if you need to point
# it at something other than an emulator on this same machine.
npx expo start
```

Then press `a` for Android, `i` for iOS, or `w` for web. The Django API
(`../api/`) needs to be running separately (`uv run python manage.py
runserver 8001` from `api/`), and for the web target specifically, its
`CORS_ALLOWED_ORIGINS` needs to include whatever origin `expo start --web`
picks (native targets aren't subject to CORS at all).

## Status

Garage (cars list) and Settings (signed-in user + logout) are real,
API-wired screens. Reminders and Expenses are still placeholders. See #101
for what's next.
