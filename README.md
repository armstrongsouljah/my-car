# My Car 🚗

A monolith repository for **My Car** — a mobile-first app where car owners register and track as many cars as they like, log service history with smart interval reminders, record general inspections, and track car-related expenses with month-on-month analytics.

## Stack

| Layer      | Tech                                                        |
|------------|-------------------------------------------------------------|
| API        | Django + Django REST Framework (packages managed with `uv`) |
| Frontend   | Next.js (App Router) + Tailwind CSS, mobile-first           |
| Database   | PostgreSQL 17                                               |
| Cache      | Redis (car information caching via `django-redis`)          |
| Async      | Celery worker + beat (OTP/welcome emails, daily reminder sweep) |
| Deployment | GitHub Actions → Artifact Registry → GKE (`mycar-gke`) |

## Repository layout

```
my-car/
├── docker-compose.yml        # db, redis, api, worker, beat, frontend
├── .github/workflows/        # CI: test → build/push images → deploy to GKE
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

Deploys to **Google Kubernetes Engine** (Autopilot), with Postgres on Cloud SQL and Redis on Memorystore. See [docs/deploy-gke.md](docs/deploy-gke.md) for the full setup (first-time provisioning via `scripts/deploy-gke.sh`, and the one-time Workload Identity Federation setup for CI).

Pushing to `main` triggers `.github/workflows/deploy.yml`:

1. **test** — `uv sync` + `pytest`
2. **build-and-push** — builds `api/` and `frontend/` images and pushes them to **Artifact Registry**
3. **deploy** — re-runs the migrate Job, then rolls the new images out to the `api`, `worker`, `beat`, and `frontend` Deployments on GKE

Required repository configuration (Settings → Secrets and variables → Actions → Secrets; auth itself is via Workload Identity Federation, no long-lived keys):

| Type   | Name                                        |
|--------|----------------------------------------------|
| Secret | `GCP_PROJECT_ID`, `GCP_REGION`, `GCP_CLUSTER`, `GCP_WORKLOAD_IDENTITY_PROVIDER`, `GCP_SERVICE_ACCOUNT`, `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_GOOGLE_CLIENT_ID`, `NEXT_PUBLIC_CLOUDINARY_CLOUD_NAME`, `NEXT_PUBLIC_CLOUDINARY_UPLOAD_PRESET` |

## Roadmap

- **GPS tracking** — integrate tracking chips / sourced GPS trackers (sellable to users); the `Car` model is the anchor point for a future `tracker` relation
- Fuel-efficiency analytics from litres + odometer deltas
- Shared garages (family / fleet access)
