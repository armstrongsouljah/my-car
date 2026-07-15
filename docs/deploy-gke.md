# Deploy my-car to Google Kubernetes Engine (GKE)

Deploys the four app workloads — **api** (Django + Gunicorn), **worker** (Celery), **beat** (Celery beat), and **frontend** (Next.js) — to a GKE Autopilot cluster. Postgres and Redis run as **managed GCP services** (Cloud SQL for PostgreSQL + Memorystore for Redis, both on private IPs), not in-cluster.

Everything is scripted. The manifests live in `k8s/` and the provisioning/deploy driver is `scripts/deploy-gke.sh`.

```
k8s/
  00-namespace.yaml        Namespace: mycar
  10-secret.example.yaml   Secret template (the script generates the real one)
  20-api.yaml              Deployment + Service (Gunicorn, :8001)
  21-worker.yaml           Celery worker Deployment
  22-beat.yaml             Celery beat Deployment (singleton)
  23-frontend.yaml         Deployment + Service (Next.js, :3000)
  40-migrate-job.yaml      One-off: migrate + seed_admin
  50-gateway.yaml          Gateway + HTTPRoutes (GKE Gateway API)
scripts/
  deploy-gke.sh            Provision GCP + build images + deploy
  deploy-gke.env.example   Config/secrets template (copy to deploy-gke.env)
```

---

## Quick start

```bash
# 1. Prereqs: gcloud CLI (gcloud auth login done), kubectl, a GCP project with billing enabled.
gcloud config set project <your-project-id>

# 2. Fill in config + secrets
cp scripts/deploy-gke.env.example scripts/deploy-gke.env
$EDITOR scripts/deploy-gke.env        # set PROJECT_ID at minimum

# 3. Run it
set -a; . scripts/deploy-gke.env; set +a
./scripts/deploy-gke.sh
```

The script is idempotent-ish — re-running skips resources that already exist and re-applies manifests.

## What the script does

1. Enables the required APIs (GKE, Cloud SQL, Memorystore, Service Networking, Artifact Registry, Cloud Build).
2. Creates an **Artifact Registry** Docker repo and a **GKE Autopilot** cluster (fully managed nodes, VPC-native by default).
3. Sets up **private services access** (a one-time VPC peering range) so Cloud SQL and Memorystore can hand out private IPs reachable from GKE pods — no public IPs, no Cloud SQL Auth Proxy sidecar needed.
4. Provisions **Cloud SQL for PostgreSQL** (db-f1-micro, private IP) and **Memorystore for Redis** (Basic tier, AUTH enabled, private IP).
5. Builds both images via **Cloud Build** (`gcloud builds submit`) — no local Docker needed. `NEXT_PUBLIC_API_URL` is baked into the frontend image at build time.
6. Generates the `mycar-env` Secret from your env vars (Postgres over `sslmode=require`, Redis with AUTH).
7. Runs the **migrate Job** and waits for it, then rolls out api / worker / beat / frontend and the Gateway.
8. Prints the Gateway's external IP.

## After it runs

Point DNS at the Gateway IP the script prints:

```
app.example.com  ->  <gateway IP>     # frontend
api.example.com  ->  <gateway IP>     # Django API + /admin
```

Then add TLS: create a Google-managed `Certificate` and attach it to an `https` listener on the Gateway in `k8s/50-gateway.yaml` (see [GKE Gateway TLS docs](https://cloud.google.com/kubernetes-engine/docs/how-to/managed-certs-gateway)), once DNS points at the Gateway's external IP.

Verify:

```bash
kubectl -n mycar get pods
kubectl -n mycar get gateway,httproute
kubectl -n mycar logs deploy/api
kubectl -n mycar logs deploy/worker    # confirm tasks flowing
```

## CI/CD (GitHub Actions)

`.github/workflows/deploy.yml` builds/pushes images to Artifact Registry and rolls them out to the GKE cluster on every push to `main`, authenticating via **Workload Identity Federation** (no service account keys). One-time setup:

```bash
PROJECT_ID=<your-project-id>
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
REPO_OWNER_SLASH_NAME=<org-or-user>/my-car

# Workload Identity Pool + OIDC provider trusting GitHub Actions
gcloud iam workload-identity-pools create github-pool --location=global \
  --display-name="GitHub Actions"
gcloud iam workload-identity-pools providers create-oidc github-provider \
  --location=global --workload-identity-pool=github-pool \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
  --attribute-condition="assertion.repository=='${REPO_OWNER_SLASH_NAME}'"

# Deployer service account, scoped to this repo only
gcloud iam service-accounts create mycar-deployer
gcloud iam service-accounts add-iam-policy-binding \
  "mycar-deployer@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github-pool/attribute.repository/${REPO_OWNER_SLASH_NAME}"

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:mycar-deployer@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role=roles/container.developer
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:mycar-deployer@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role=roles/artifactregistry.writer
```

Then set repository secrets (Settings → Secrets and variables → Actions → Secrets). None of these are used for authentication itself — that's Workload Identity Federation — but they're set as Secrets rather than Variables in this repo:

| Secret | Value |
|--------|-------|
| `GCP_PROJECT_ID` | `<your-project-id>` |
| `GCP_REGION` | e.g. `us-central1` |
| `GCP_CLUSTER` | must match `CLUSTER` in `scripts/deploy-gke.env` |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | `projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github-pool/providers/github-provider` |
| `GCP_SERVICE_ACCOUNT` | `mycar-deployer@<your-project-id>.iam.gserviceaccount.com` |
| `NEXT_PUBLIC_API_URL` | e.g. `https://api.example.com/api/v1` |
| `NEXT_PUBLIC_GOOGLE_CLIENT_ID` | your Google OAuth client id |

## Design notes / gotchas

- **Gateway API, not legacy Ingress.** Newer GKE clusters (including Autopilot) route external traffic through the Gateway API controllers (`gke-l7-global-external-managed` etc.) rather than the classic `networking.k8s.io/v1 Ingress` + `gce` IngressClass. A plain `Ingress` object is silently never reconciled on these clusters (no events, no address, ever) — `k8s/50-gateway.yaml` uses `Gateway` + `HTTPRoute` instead.
- **Migrations run once, in a Job.** The api container is started with an explicit `gunicorn` command, which makes `entrypoint.sh` skip its built-in migrate/seed — so the 2 api replicas don't race. `40-migrate-job.yaml` owns `migrate` + `seed_admin`. The CI workflow re-runs this Job on every deploy.
- **beat stays at `replicas: 1`** with a `Recreate` strategy — multiple schedulers double-fire periodic tasks.
- **Media files:** `docker-compose` shares a `media_data` volume across api/worker. On GKE this isn't automatic. Either mount a `PersistentVolumeClaim` (Filestore-backed) on api + worker, or (recommended) switch Django to Google Cloud Storage with `django-storages`. Until then, uploaded media won't be shared between pods.
- **Frontend build arg:** `NEXT_PUBLIC_API_URL` is compiled in, so changing the API domain requires rebuilding the frontend image (re-run the script, or push to `main`).
- **Cloud SQL / Memorystore use private IPs**, not the Cloud SQL Auth Proxy — the one-time VPC peering range set up in step 4 is what makes this work. If you ever move workloads off GKE Autopilot's default VPC, redo that peering on the new network.
- **Secrets never get committed:** `scripts/deploy-gke.env` and `k8s/secret.yaml` are gitignored; the live Secret is generated imperatively.
- **Cost:** the default SKUs (db-f1-micro, Memorystore Basic 1GB, Autopilot pay-per-pod) are a low-cost footprint; scale up for production load.

## Cleanup

```bash
gcloud container clusters delete "$CLUSTER" --region "$REGION" --quiet
gcloud sql instances delete "$PG" --quiet
gcloud redis instances delete "$REDIS" --region "$REGION" --quiet
gcloud artifacts repositories delete "$REPO" --location "$REGION" --quiet
```
