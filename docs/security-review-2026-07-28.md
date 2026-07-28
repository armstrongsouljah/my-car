# GlavBox — Security Review

**Date:** 28 July 2026 · **Branch:** `main` @ `36112f7` · **Scope:** `api/`, `frontend/`, `k8s/`, `docker-compose.yml`, CI

Findings marked **[verified]** were reproduced against a live test database using the real URLconf, views and permission classes.

> **Status:** findings 1–5 and 7–11 are fixed on `fix/security-hardening`. **Finding 6 (JWTs in `localStorage`) is the only one left open** — it needs an auth-flow design decision rather than a patch, so it hasn't been touched. Fixing 9 also resolved a separate production bug: support requests with attachments were never delivered at all — see the note under that finding.
>
> `manage.py check --deploy` went from `W004, W008, W012, W016` to clean (only `W021`, HSTS preload, which is deliberately opt-in).

---

## Summary

| # | Severity | Finding |
|---|----------|---------|
| 1 | **Critical** | `DELETE /api/v1/auth/profile/` deletes *other people's* accounts |
| 2 | **High** | Email-verification OTP can be brute-forced → account takeover |
| 3 | **High** | Deployment defaults ship a known super-admin password |
| 4 | **Medium** | No throttling on login / register / OTP endpoints |
| 5 | **Medium** | `DEBUG` defaults to `True` |
| 6 | **Medium** | JWTs stored in `localStorage` |
| 7 | **Low** | Missing HSTS and secure-cookie flags |
| 8 | **Low** | Celery TLS certificate verification disabled |
| 9 | **Low** | Unrestricted upload file types |
| 10 | **Low** | User enumeration on register / resend-OTP |
| 11 | **Low** | OTPs generated with non-cryptographic RNG, stored in plaintext |

**What's already solid:** object-level ownership scoping across cars, services, expenses, inspections, reminders and conversations is correct and I could not break it. No SQL injection, SSRF, unsafe deserialization or XSS surface. Google ID tokens are properly verified server-side. Dependencies are fully patched. CI uses Workload Identity Federation with no long-lived cloud keys. No secrets in git history.

---

## 1. Critical — any user can delete any account

**`api/utils/Views.py:256` + `api/accounts/views.py:169`**

`SmartDetailView.delete()` never calls `self.has_permission("DELETE")`, so the `deletable = False` guard on line 284 is dead code. `ProfileView` inherits that `delete()` and does not override `queryset()`, so the default `self.model.objects.filter(**kwargs)` runs with **no kwargs** — matching every row in the user table. `.first()` then resolves via `User.Meta.ordering = ["-date_joined"]` to the most recently registered user.

Net effect: any authenticated user sending `DELETE /api/v1/auth/profile/` deletes whichever account signed up most recently — not their own. Repeating it with the same token walks down the table. `on_delete=CASCADE` takes the victim's cars, services, expenses, inspections and reminders with them.

**[verified]** One attacker token: victim deleted (attacker's own account untouched); repeated calls took the table from 5 users to 1; victim's cars went 1 → 0.

**Fixed:** `ProfileView.queryset()` now scopes to `self.request.user.pk`; `delete()` and `patch()` honour `has_permission`/`has_object_permission`; and the base `queryset()` raises `ImproperlyConfigured` rather than silently matching the whole table when given no lookup kwargs, so the next subclass that forgets to scope itself fails loudly.

## 2. High — OTP brute force → account takeover

**`api/accounts/views.py:67`, `api/accounts/models.py:83`**

`VerifyEmailView` is `AllowAny` with no throttle class. `EmailVerificationOTP` has no attempt counter, and a wrong guess neither burns the OTP nor locks the account. The code is 6 digits with a 10-minute window, and `ResendOTPView` (also `AllowAny`, also unthrottled) lets an attacker mint a fresh window on demand for any unverified email. A successful guess returns a full access + refresh token pair.

**[verified]** Six consecutive wrong codes all returned 400, no `429`, and the OTP remained valid; the correct code then returned 200 with `tokens` in the body.

**Fixed:** a `failed_attempts` counter burns the code after 5 wrong guesses, `verify()` uses a constant-time compare, and both verify and resend carry their own throttle scope keyed on the target email. The code is still 6 digits — the attempt cap, not the width, is what closes the brute force.

## 3. High — deployment defaults ship a known super-admin password

**`docker-compose.yml:31`, `k8s/10-secret.example.yaml:24`**

Both default `ADMIN_PASSWORD` to the literal `change-me-admin-password`, and `seed_admin` runs on every boot creating a `is_superuser` account at the well-known address `admin@mycar.com`. Django admin is served at `/admin/` on the same public hostname as the API. If the template value ever reaches production unchanged, that's full admin over every user's data. `docker-compose.yml:26` similarly defaults `SECRET_KEY` to `dev-secret-key`, which would make forged session cookies and signed tokens trivial.

**Fixed:** the `change-me-admin-password` fallbacks are gone from both Compose and the k8s template — empty now means `seed_admin` generates a random password and logs it once. `SECRET_KEY` is required in Compose (`${SECRET_KEY:?...}`).

## 4. Medium — no throttling on authentication endpoints

`DEFAULT_THROTTLE_RATES` defines only `assistant_chat` and `support_request`, and `DEFAULT_THROTTLE_CLASSES` is never set — so login, register, OTP verify, OTP resend and token refresh have no rate limit at all.

**[verified]** 15 consecutive failed logins, all 401, no `429`.

**Fixed:** baseline `anon`/`user` throttle classes plus per-endpoint scopes for login, register and the two OTP routes. The OTP scopes key on the target email rather than IP, so a distributed attacker can't grind one account from a pool of addresses.

**Action needed on deploy:** set `NUM_PROXIES=2` in the k8s secret. DRF otherwise reads the whole `X-Forwarded-For`, which the caller can spoof; behind the Gateway the header is `<client>, <gclb>`, so 2 hops back is the real client.

## 5. Medium — `DEBUG` defaults to `True`

`api/config/settings.py:11` and `docker-compose.yml:27` both default DEBUG on; `.env.example:3` ships `DEBUG=True`. A missing env var in production means stack traces with settings values, and `MEDIA_ROOT` served directly (`config/urls.py:28`). The k8s secret sets it to `False` explicitly, so this is a latent trap rather than a live exposure — but it's the wrong default to have.

**Fixed:** `default=False`, so a deployed environment missing the variable fails closed.

## 6. Medium — JWTs in `localStorage`

`frontend/lib/api.js:14-22` stores both access and refresh tokens in `localStorage`, readable by any script on the origin. There's no XSS vector in the app today, so this is a resilience issue: one injected script (or a compromised npm dependency) exfiltrates a 7-day refresh token rather than being confined to the session. `httpOnly` cookies would remove the class entirely, at the cost of CSRF handling.

## 7. Low — missing HSTS and secure-cookie flags

`SECURE_HSTS_SECONDS`, `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE` and `CSRF_COOKIE_SECURE` are all unset/false. `SECURE_PROXY_SSL_HEADER` is configured correctly and the Gateway redirects HTTP→HTTPS, so this is partly covered at the edge — but the admin session cookie has no `Secure` flag and there's no HSTS to stop a first-request downgrade. `X-Frame-Options: DENY`, `nosniff` and `Referrer-Policy` are all present and correct.

**Fixed:** all four now default to on-unless-`DEBUG`, so local HTTP development is unaffected and deployments are hardened without extra env vars. HSTS is one year with `includeSubDomains`; preload stays opt-in because submitting to the browser preload list is hard to reverse. `/health/` is exempt from the SSL redirect so k8s probes still work.

## 8. Low — Celery broker TLS verification disabled

`api/config/settings.py:236` sets `ssl_cert_reqs: CERT_NONE` for `rediss://`, so the encrypted broker connection accepts any certificate — MITM on that link is undetected. Fine on a private VPC to Memorystore; wrong if the broker is ever reachable over an untrusted path.

**Fixed:** now `CERT_REQUIRED`, with `CELERY_BROKER_SSL_CA_CERTS` for brokers behind a private CA.

## 9. Low — unrestricted upload file types

Neither `SupportAttachment.file` nor `Inspection.report` validates extension or content type. Support attachments are read back and attached to outbound email to the support inbox (`utils/Email.py`), so the endpoint can be used to mail arbitrary binaries to your team — throttled at 5/hour, and size/count are capped (5 files, 10MB). Django's `FileField` sanitizes the filename, so there's no path traversal.

**Fixed:** both surfaces now allowlist images and PDFs by extension *and* content type (`utils/Uploads.py`).

### Related production bug found while fixing this — support attachments were never delivered

Attachments were written to `MEDIA_ROOT` during the request and re-read by `send_support_request_email_task`. That task runs in the **worker** pod, which has its own empty `/app/media` — no volume is defined in any k8s manifest, and the API deployment runs 2 replicas besides. The worker hit `FileNotFoundError`, the task died, and *no* email went out: not the attachments, not even the message text. Requests without attachments never touch the filesystem, which is why only those arrived. `docker-compose.yml` shares a `media_data` volume between `api` and `worker`, so it worked locally and only broke in production.

**[verified]** Reproduced by wiping `MEDIA_ROOT` between the request and the task: `FileNotFoundError`, zero emails sent, support request row stranded in the database.

**Fixed:** attachment bytes now travel in the Celery task payload and are never written to storage, so there is no shared-filesystem requirement. The `SupportAttachment` model is dropped; `SupportRequest.attachment_names` keeps the filenames so an admin record can be matched to the email thread. A combined 10MB cap across the batch keeps the broker message bounded.

**Still open:** `Inspection.report` has the same root cause. Reports are written to the API pod's ephemeral disk, so they're lost on restart, invisible to the other replica, and `report_url` points at `/media/...`, which isn't routed at all when `DEBUG=False`. Uploads there are effectively write-only today. That needs real object storage (GCS) rather than the payload trick, since reports are meant to be read back later.

## 10. Low — user enumeration

**[verified]** `POST /auth/register/` returns 400 `"User with this email already exists."` vs 201; `POST /auth/resend-otp/` returns 404 `"No account found with this email."` vs 200. Login itself is correctly generic. Low impact on its own, but it pairs with finding 2 to let an attacker locate unverified accounts to target.

**Fixed:** all three routes now return identical status and body regardless of whether the address exists. Registering with a taken address returns the same 201 and emails the actual account holder a "you already have an account" notice instead of creating anything; `verify-email` collapses every failure to one message. DRF's auto-generated `UniqueValidator` on the email field had to be disabled explicitly — it was answering "already exists" before the view was ever reached.

**UX trade-off:** the signup form can no longer say "that email is taken." The frontend copy now covers both cases and the notice email points the user to sign in. Say the word if you'd rather have the clearer error back — it's a small revert.

## 11. Low — OTP generation and storage

`utils/Email.py:8` uses `random.choices`, which is a Mersenne Twister, not a CSPRNG — predictable given enough observed output. OTPs are also stored in plaintext and exposed in Django admin (`accounts/admin.py:14`).

**Fixed:** `secrets.choice` for generation; codes are stored as an HMAC keyed on `SECRET_KEY` (a plain hash is useless here — the whole 6-digit space hashes in under a second, but a database-only leak doesn't include `SECRET_KEY`); the admin registration is gone. The user-facing code is still 6 digits — only the stored column changed.

---

## What's left

**Finding 6 (JWTs in `localStorage`)** is the only numbered finding still open. Moving to `httpOnly` cookies removes the token-theft class entirely, but it needs CSRF handling and touches every API call in the frontend — a design decision rather than a patch.

Two items outside the numbered findings:

- **`Inspection.report` has the same shared-storage problem** that broke support attachments. Reports go to the API pod's ephemeral disk, so they're lost on restart, invisible to the second replica, and `report_url` points at `/media/...`, which isn't routed when `DEBUG=False`. Those uploads are effectively write-only today. The payload approach used for support attachments doesn't transfer, since reports are meant to be read back later — this one needs object storage.
- **`--timeout 0` on gunicorn** (in both `entrypoint.sh` and `k8s/20-api.yaml`) means a hung request occupies a thread forever. With `--workers 1 --threads 8`, eight of those take the pod down.

## Notes on infrastructure

CI is in good shape: Workload Identity Federation rather than a service-account JSON key, deploys gated on tests, images tagged by SHA. The API container runs as a non-root user. Two smaller things: the frontend job uses `npm install` rather than `npm ci`, so CI can silently resolve past the lockfile; and gunicorn runs with `--timeout 0` (in both `entrypoint.sh` and `k8s/20-api.yaml`), which means a hung request occupies a thread forever — with `--workers 1 --threads 8`, eight of those take the pod down.
