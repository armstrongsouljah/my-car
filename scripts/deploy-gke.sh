#!/usr/bin/env bash
#
# Provision GCP infra + deploy my-car to GKE (Autopilot).
# Idempotent-ish: safe to re-run; `gcloud ... create` is skipped if the resource exists.
#
# Prereqs: gcloud CLI (logged in, `gcloud auth login`), kubectl. Docker not
# required (uses `gcloud builds submit` / Cloud Build).
# Usage:
#   cp scripts/deploy-gke.env.example scripts/deploy-gke.env   # fill in secrets
#   set -a; . scripts/deploy-gke.env; set +a
#   ./scripts/deploy-gke.sh
#
set -euo pipefail
cd "$(dirname "$0")/.."

# ── Config ────────────────────────────────────────────────────────────────────
: "${PROJECT_ID:?set PROJECT_ID to your GCP project id}"
: "${REGION:=us-central1}"
: "${REPO:=mycar}"
: "${CLUSTER:=mycar-cluster}"
: "${PG:=mycar-pg}"
: "${REDIS:=mycar-redis}"
: "${NETWORK:=default}"
: "${IMAGE_TAG:=latest}"
: "${DB_PASSWORD:?set DB_PASSWORD}"
: "${DJANGO_SECRET_KEY:?set DJANGO_SECRET_KEY}"
: "${ADMIN_EMAIL:=admin@mycar.com}"
: "${ADMIN_PASSWORD:?set ADMIN_PASSWORD}"
: "${APP_HOST:?set APP_HOST e.g. app.example.com}"
: "${API_HOST:?set API_HOST e.g. api.example.com}"
: "${GOOGLE_OAUTH_CLIENT_ID:=}"

exists() { "$@" >/dev/null 2>&1; }

gcloud config set project "$PROJECT_ID" -q

# ── 1. Enable required APIs ────────────────────────────────────────────────────
gcloud services enable \
  container.googleapis.com sqladmin.googleapis.com redis.googleapis.com \
  servicenetworking.googleapis.com artifactregistry.googleapis.com \
  cloudbuild.googleapis.com -q

# ── 2. Artifact Registry ───────────────────────────────────────────────────────
exists gcloud artifacts repositories describe "$REPO" --location "$REGION" || \
  gcloud artifacts repositories create "$REPO" --repository-format=docker --location "$REGION" -q
REGISTRY="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}"

# ── 3. GKE Autopilot cluster ───────────────────────────────────────────────────
exists gcloud container clusters describe "$CLUSTER" --region "$REGION" || \
  gcloud container clusters create-auto "$CLUSTER" --region "$REGION" -q
gcloud container clusters get-credentials "$CLUSTER" --region "$REGION" -q

# ── 4. Private services access (VPC peering, needed once per network) ─────────
#     Lets Cloud SQL + Memorystore hand out private IPs reachable from GKE pods.
exists gcloud compute addresses describe mycar-vpc-range --global || \
  gcloud compute addresses create mycar-vpc-range --global --purpose=VPC_PEERING \
    --prefix-length=16 --network="$NETWORK" -q
gcloud services vpc-peerings connect --service=servicenetworking.googleapis.com \
  --ranges=mycar-vpc-range --network="$NETWORK" -q || true

# ── 5. Managed Postgres (Cloud SQL, private IP) ────────────────────────────────
exists gcloud sql instances describe "$PG" || gcloud sql instances create "$PG" \
  --database-version=POSTGRES_17 --edition=ENTERPRISE --tier=db-f1-micro --region "$REGION" \
  --network="$NETWORK" --no-assign-ip --root-password="$DB_PASSWORD" -q
exists gcloud sql databases describe mycar --instance "$PG" || \
  gcloud sql databases create mycar --instance "$PG" -q
exists gcloud sql users describe mycar --instance "$PG" || \
  gcloud sql users create mycar --instance "$PG" --password="$DB_PASSWORD" -q
PG_HOST=$(gcloud sql instances describe "$PG" --format='value(ipAddresses[0].ipAddress)')

# ── 6. Managed Redis (Memorystore, private IP) ─────────────────────────────────
exists gcloud redis instances describe "$REDIS" --region "$REGION" || \
  gcloud redis instances create "$REDIS" --region "$REGION" --tier=basic \
    --size=1 --redis-version=redis_7_0 --network="$NETWORK" --enable-auth -q
REDIS_HOST=$(gcloud redis instances describe "$REDIS" --region "$REGION" --format='value(host)')
REDIS_AUTH=$(gcloud redis instances get-auth-string "$REDIS" --region "$REGION")

# ── 7. Build & push images (Cloud Build, no local Docker needed) ──────────────
gcloud builds submit ./api --tag "${REGISTRY}/mycar-api:${IMAGE_TAG}" -q

gcloud builds submit ./frontend -q \
  --config=<(cat <<EOF
steps:
  - name: gcr.io/cloud-builders/docker
    args:
      - build
      - --build-arg
      - NEXT_PUBLIC_API_URL=https://${API_HOST}/api/v1
      - --build-arg
      - NEXT_PUBLIC_GOOGLE_CLIENT_ID=${GOOGLE_OAUTH_CLIENT_ID}
      - -t
      - ${REGISTRY}/mycar-frontend:${IMAGE_TAG}
      - .
images: ["${REGISTRY}/mycar-frontend:${IMAGE_TAG}"]
EOF
)

# ── 8. Namespace + secret (generated, never committed) ────────────────────────
kubectl apply -f k8s/00-namespace.yaml
kubectl -n mycar create secret generic mycar-env \
  --from-literal=SECRET_KEY="$DJANGO_SECRET_KEY" \
  --from-literal=DEBUG="False" \
  --from-literal=ALLOWED_HOSTS="${API_HOST},api" \
  --from-literal=DATABASE_URL="postgresql://mycar:${DB_PASSWORD}@${PG_HOST}:5432/mycar?sslmode=require" \
  --from-literal=REDIS_URL="redis://:${REDIS_AUTH}@${REDIS_HOST}:6379/1" \
  --from-literal=CELERY_BROKER_URL="redis://:${REDIS_AUTH}@${REDIS_HOST}:6379/0" \
  --from-literal=CELERY_RESULT_BACKEND="redis://:${REDIS_AUTH}@${REDIS_HOST}:6379/0" \
  --from-literal=CORS_ALLOWED_ORIGINS="https://${APP_HOST}" \
  --from-literal=FRONTEND_URL="https://${APP_HOST}" \
  --from-literal=ADMIN_EMAIL="$ADMIN_EMAIL" \
  --from-literal=ADMIN_PASSWORD="$ADMIN_PASSWORD" \
  --from-literal=GOOGLE_OAUTH_CLIENT_ID="$GOOGLE_OAUTH_CLIENT_ID" \
  --dry-run=client -o yaml | kubectl apply -f -

# ── 9. Deploy workloads (substitute image placeholders) ───────────────────────
export REGISTRY IMAGE_TAG
render() { envsubst '${REGISTRY} ${IMAGE_TAG}' < "$1"; }

# Migrate first, wait for completion, then roll out the rest.
render k8s/40-migrate-job.yaml | kubectl apply -f -
kubectl -n mycar wait --for=condition=complete job/migrate --timeout=300s

for f in k8s/20-api.yaml k8s/21-worker.yaml k8s/22-beat.yaml k8s/23-frontend.yaml; do
  render "$f" | kubectl apply -f -
done
kubectl apply -f k8s/50-ingress.yaml

# ── 10. Wait for rollout + report ──────────────────────────────────────────────
kubectl -n mycar rollout status deploy/api
kubectl -n mycar rollout status deploy/frontend
echo
echo "Ingress external IP (can take a few minutes to provision on first apply):"
kubectl -n mycar get ingress mycar -o jsonpath='{.status.loadBalancer.ingress[0].ip}'; echo
echo "Point ${APP_HOST} and ${API_HOST} DNS at that IP, then add a Google-managed TLS cert."
