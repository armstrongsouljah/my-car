# GlavBox 🚗

A monolith repository for **GlavBox** — a mobile-first app where car owners register and track as many cars as they like, log service history with smart interval reminders, record general inspections, and track car-related expenses with month-on-month analytics.

> The product was renamed from "My Car" to GlavBox. Infrastructure identifiers created under the old name (the `my-car/` repo path, the `admin@mycar.com` seeded super admin address, container/service names like `my-car-api`) are retained as-is — renaming them isn't worth the churn. `DEFAULT_FROM_EMAIL` (all outgoing app email) is a required env var — see `.env.example` — since `mycar.com` isn't a domain we control.

## Stack

| Layer      | Tech                                                        |
|------------|-------------------------------------------------------------|
| API        | Django + Django REST Framework (packages managed with `uv`) |
| Frontend   | Next.js (App Router) + Tailwind CSS, mobile-first           |
| Database   | PostgreSQL 17                                               |
| Cache      | Redis (car information caching via `django-redis`)          |
| Async      | Celery worker + beat (OTP/welcome emails, daily reminder sweep) |
| Deployment | GitHub Actions → self-managed DigitalOcean droplet (Docker Compose + Caddy) |

## Repository layout

```
my-car/
├── docker-compose.yml        # db, redis, api, worker, beat, frontend
├── docker-compose.prod.yml   # production override — adds Caddy (reverse proxy + TLS)
├── Caddyfile                 # app.glavbox.com / api.glavbox.com routing
├── .github/workflows/        # CI: test → deploy to the droplet over SSH
├── api/                      # Django REST Framework monolith
│   ├── config/               # settings, urls, celery app
│   ├── utils/                # shared craft: Views, Serializers, QueryParams,
│   │                         # Permissions, Constants, Exception, Message,
│   │                         # Email, Cache (Redis car caching)
│   ├── accounts/             # auth: register + OTP verify, login, Google,
│   │                         # profile, change password, deactivate account
│   ├── cars/                 # the garage — unlimited cars per owner
│   ├── services/             # service history, intervals & reminders
│   ├── inspections/          # general inspections + optional report upload
│   ├── expenses/             # expense log + month-on-month analytics
│   └── tasks.py              # celery tasks (emails, daily reminder sweep)
└── frontend/                 # Next.js app (login/signup → dashboard)
```

The `utils/` folder and the views/serializers follow the same craft style as `nivo-api`: `SmartAPIView` / `SmartPaginationAPIView` / `SmartDetailView` base views, `Create` / `Edit` / `List` / `Detail` serializer split, `CustomValidation` structured errors, and `QueryParams` helpers.

## Features

**Authentication**
- Email + password registration with OTP email verification (tokens issued on verify)
- Sign in with Google (frontend obtains a Google ID token; API verifies and issues JWTs)
- JWT auth (simplejwt) with refresh rotation and blacklisting
- Owners can **deactivate their accounts at will** (Settings → Danger zone)

**Garage**
- Register and track unlimited cars (make, model, plate, VIN, fuel type, odometer)
- Car detail and list responses are **cached in Redis** and invalidated on any change

**Service history & reminders**
- Log services with the next-service interval rule — e.g. *5,000 km or 6 months*, *10,000 km or 12 months* — **whichever comes first** applies
- Reminder statuses: `ok` → `due_soon` (within 500 km / 30 days) → `overdue`
- General inspection reminders so owners know the state of their vehicle; inspection reports can optionally be uploaded
- Daily Celery beat sweep emails owners a per-car digest of anything due

**Expenses**
- Log garage visits, modification parts, fuel (with litres), insurance, and more
- `GET /api/v1/expenses/analytics/` returns month-on-month totals, per-category breakdowns and change vs the previous month

## Getting started

```bash
cp .env.example .env          # fill in secrets (or run with dev defaults)
docker compose up --build
```

| Service   | URL                          |
|-----------|------------------------------|
| Frontend  | http://localhost:3000        |
| API       | http://localhost:8000/api/v1 |
| Admin     | http://localhost:8000/admin  |

On first boot the API runs migrations and **seeds the super admin `admin@mycar.com`** (password from `ADMIN_PASSWORD`; a random one is generated and printed to the logs if unset).

### Local API development (uv)

```bash
cd api
uv sync                        # install dependencies
uv run python manage.py migrate
uv run python manage.py runserver
uv run pytest                  # run the test suite
```

### Local frontend development

```bash
cd frontend
npm install
npm run dev
npm run lint               # ESLint (next/core-web-vitals)
npm test                   # Jest + React Testing Library
```

### Pre-commit hooks

Linting runs automatically on every commit (ruff + black for `api/`, ESLint for `frontend/`, plus general hygiene hooks); pytest and Jest run on push.

```bash
cd api && uv sync          # installs pre-commit (dev dependency)
uv run pre-commit install --hook-type pre-commit --hook-type pre-push
```

## Key endpoints

```
POST   /api/v1/auth/register/            POST  /api/v1/auth/verify-email/
POST   /api/v1/auth/login/               POST  /api/v1/auth/google/
POST   /api/v1/auth/account/deactivate/  GET   /api/v1/auth/profile/

GET|POST   /api/v1/cars/                 GET|PATCH|DELETE /api/v1/cars/<id>/
GET|POST   /api/v1/services/             GET   /api/v1/services/reminders/
GET|POST   /api/v1/inspections/          (multipart `report` upload optional)
GET|POST   /api/v1/expenses/             GET   /api/v1/expenses/analytics/
```

## Deployment

Deploys to a single self-managed **DigitalOcean droplet** running Postgres, Redis, and the app itself as plain Docker containers via Compose, with **Caddy** in front as the reverse proxy and automatic Let's Encrypt TLS terminator (`app.glavbox.com` / `api.glavbox.com`). Moved off GCP (GKE/Cloud SQL/Memorystore) in August 2026 — each of those was billed as a separate managed service, which added up to a lot more than one droplet running the same workload for a project this size.

- `docker-compose.yml` — the base stack (`db`, `redis`, `api`, `worker`, `beat`, `frontend`); dev-safe defaults (`ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, port bindings) that a deployment overrides via `.env`, never by editing the file.
- `docker-compose.prod.yml` — override that adds `caddy` (`docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d`).
- `Caddyfile` — routes the two domains to the `frontend`/`api` containers.

Pushing to `main` triggers `.github/workflows/deploy-droplet.yml`:

1. **test** / **test-frontend** — `uv run pytest`, `npm run lint`, `npm test`, `npm run build`
2. **deploy** — syncs `api/`, `frontend/`, and the compose/Caddy files to the droplet over SSH, builds the images there, runs migrations, and brings the stack up (`docker compose up -d --wait`, gated on the `api` container's healthcheck)

Single environment for now — every push to `main` deploys straight to production. Splitting this into a dev/prod promotion flow (main → dev, release tag → prod) is tracked in #81.

Required repository configuration (Settings → Secrets and variables → Actions → Secrets):

| Type   | Name                                        |
|--------|----------------------------------------------|
| Secret | `DROPLET_HOST`, `DROPLET_SSH_KEY`, `DROPLET_SSH_FINGERPRINT` (a dedicated deploy keypair, not anyone's personal key) |

## Roadmap

- **GPS tracking** — integrate tracking chips / sourced GPS trackers (sellable to users); the `Car` model is the anchor point for a future `tracker` relation
- Fuel-efficiency analytics from litres + odometer deltas
- Shared garages (family / fleet access)
