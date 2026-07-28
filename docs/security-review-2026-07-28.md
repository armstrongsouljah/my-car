# GlavBox — Security Review

**Date:** 28 July 2026 · **Branch:** `main` @ `36112f7` · **Scope:** `api/`, `frontend/`, `k8s/`, `docker-compose.yml`, CI

Findings marked **[verified]** were reproduced against a live test database using the real URLconf, views and permission classes.

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

**Fix:** override `queryset()` on `ProfileView` to return `User.objects.filter(pk=self.request.user.pk)`, *and* fix the base class so `delete()` actually honours `has_permission` — the dead guard is the root cause and the next `SmartDetailView` subclass will hit it too. Consider making `SmartDetailView.queryset()` raise rather than silently returning everything when no kwargs are supplied.

## 2. High — OTP brute force → account takeover

**`api/accounts/views.py:67`, `api/accounts/models.py:83`**

`VerifyEmailView` is `AllowAny` with no throttle class. `EmailVerificationOTP` has no attempt counter, and a wrong guess neither burns the OTP nor locks the account. The code is 6 digits with a 10-minute window, and `ResendOTPView` (also `AllowAny`, also unthrottled) lets an attacker mint a fresh window on demand for any unverified email. A successful guess returns a full access + refresh token pair.

**[verified]** Six consecutive wrong codes all returned 400, no `429`, and the OTP remained valid; the correct code then returned 200 with `tokens` in the body.

**Fix:** cap attempts per OTP record (3–5, then invalidate), add a scoped throttle to both verify and resend, and consider an 8-digit code.

## 3. High — deployment defaults ship a known super-admin password

**`docker-compose.yml:31`, `k8s/10-secret.example.yaml:24`**

Both default `ADMIN_PASSWORD` to the literal `change-me-admin-password`, and `seed_admin` runs on every boot creating a `is_superuser` account at the well-known address `admin@mycar.com`. Django admin is served at `/admin/` on the same public hostname as the API. If the template value ever reaches production unchanged, that's full admin over every user's data. `docker-compose.yml:26` similarly defaults `SECRET_KEY` to `dev-secret-key`, which would make forged session cookies and signed tokens trivial.

**Fix:** drop the fallbacks — make both variables required (`${ADMIN_PASSWORD:?set this}`) so a misconfigured deploy fails loudly instead of booting with a guessable admin. `seed_admin` already generates a random password when the variable is empty, which is the better default.

## 4. Medium — no throttling on authentication endpoints

`DEFAULT_THROTTLE_RATES` defines only `assistant_chat` and `support_request`, and `DEFAULT_THROTTLE_CLASSES` is never set — so login, register, OTP verify, OTP resend and token refresh have no rate limit at all.

**[verified]** 15 consecutive failed logins, all 401, no `429`.

**Fix:** add `anon`/`user` scoped throttles globally, plus a tighter scope on the auth endpoints. Note that per-IP throttling behind the GKE L7 load balancer needs `X-Forwarded-For` handled correctly or every request looks like it comes from the LB.

## 5. Medium — `DEBUG` defaults to `True`

`api/config/settings.py:11` and `docker-compose.yml:27` both default DEBUG on; `.env.example:3` ships `DEBUG=True`. A missing env var in production means stack traces with settings values, and `MEDIA_ROOT` served directly (`config/urls.py:28`). The k8s secret sets it to `False` explicitly, so this is a latent trap rather than a live exposure — but it's the wrong default to have.

**Fix:** `default=False`.

## 6. Medium — JWTs in `localStorage`

`frontend/lib/api.js:14-22` stores both access and refresh tokens in `localStorage`, readable by any script on the origin. There's no XSS vector in the app today, so this is a resilience issue: one injected script (or a compromised npm dependency) exfiltrates a 7-day refresh token rather than being confined to the session. `httpOnly` cookies would remove the class entirely, at the cost of CSRF handling.

## 7. Low — missing HSTS and secure-cookie flags

`SECURE_HSTS_SECONDS`, `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE` and `CSRF_COOKIE_SECURE` are all unset/false. `SECURE_PROXY_SSL_HEADER` is configured correctly and the Gateway redirects HTTP→HTTPS, so this is partly covered at the edge — but the admin session cookie has no `Secure` flag and there's no HSTS to stop a first-request downgrade. `X-Frame-Options: DENY`, `nosniff` and `Referrer-Policy` are all present and correct.

## 8. Low — Celery broker TLS verification disabled

`api/config/settings.py:236` sets `ssl_cert_reqs: CERT_NONE` for `rediss://`, so the encrypted broker connection accepts any certificate — MITM on that link is undetected. Fine on a private VPC to Memorystore; wrong if the broker is ever reachable over an untrusted path.

**Fix:** `CERT_REQUIRED` with the appropriate CA bundle.

## 9. Low — unrestricted upload file types

Neither `SupportAttachment.file` nor `Inspection.report` validates extension or content type. Support attachments are read back and attached to outbound email to the support inbox (`utils/Email.py`), so the endpoint can be used to mail arbitrary binaries to your team — throttled at 5/hour, and size/count are capped (5 files, 10MB). Django's `FileField` sanitizes the filename, so there's no path traversal.

**Fix:** allowlist extensions and content types on both fields.

## 10. Low — user enumeration

**[verified]** `POST /auth/register/` returns 400 `"User with this email already exists."` vs 201; `POST /auth/resend-otp/` returns 404 `"No account found with this email."` vs 200. Login itself is correctly generic. Low impact on its own, but it pairs with finding 2 to let an attacker locate unverified accounts to target.

## 11. Low — OTP generation and storage

`utils/Email.py:8` uses `random.choices`, which is a Mersenne Twister, not a CSPRNG — predictable given enough observed output. OTPs are also stored in plaintext and exposed in Django admin (`accounts/admin.py:14`).

**Fix:** `secrets.choice`; hash the stored OTP; drop the admin registration.

---

## Suggested order

1. Finding 1 — one-line fix, currently exploitable by any logged-in user
2. Findings 2 and 4 together — one throttle configuration pass
3. Finding 3 — remove the default before the next deploy
4. Finding 5 — flip the default
5. Findings 7–11 — hardening backlog
6. Finding 6 — needs an auth-flow design decision

## Notes on infrastructure

CI is in good shape: Workload Identity Federation rather than a service-account JSON key, deploys gated on tests, images tagged by SHA. The API container runs as a non-root user. Two smaller things: the frontend job uses `npm install` rather than `npm ci`, so CI can silently resolve past the lockfile; and gunicorn runs with `--timeout 0` (in both `entrypoint.sh` and `k8s/20-api.yaml`), which means a hung request occupies a thread forever — with `--workers 1 --threads 8`, eight of those take the pod down.
