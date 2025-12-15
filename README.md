# DevPlatform (initial scaffold)

Goal: a unified platform to onboard repos, auto-configure CI/CD, spin up preview environments, surface logs/metrics, and support prod deploys with manual approval. This scaffold seeds backend, frontend, Helm chart, and GitHub Actions templates so you can start iterating.

## Structure

- `backend/` FastAPI API (onboard repo, approve prod deploy, GitHub webhooks).
- `frontend/` Vite + React minimal UI (forms for onboarding and approval placeholders).
- `infra/helm/devplatform/` Helm chart for deploying an arbitrary app image with ingress.
- `.github/workflows/` CI, preview, and prod pipeline templates.

## Quick start (local)

1. Backend

```
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

2. Frontend (basic static UI)

```
cd frontend
npm install
npm run dev -- --host
```

3. Helm chart render test

```
helm template devplatform infra/helm/devplatform \
  --set image.repository=ghcr.io/your-org/your-app \
  --set image.tag=dev
```

## Workflows overview

- `ci.yaml`: lint/test/build/push image on pushes/PRs. Uses GHCR by default; requires `REGISTRY_USERNAME`, `REGISTRY_PASSWORD` secrets or OIDC setup.
- `preview.yaml`: on PR, deploys a preview env via Helm to namespace `pr-<num>` with ingress host `pr-<num>.devplatform.local`. Requires a reachable cluster + kubeconfig secret `KUBE_CONFIG`.
- `prod.yaml`: on main, builds image then waits for manual approval (GitHub environment or manual job) before Helm rolling update to `prod` namespace.

## Secrets & security

- No secrets are stored in code. Workflows expect registry creds and kubeconfig to be provided via secrets. Replace with Vault/External Secrets Operator in real deployments.

## Next steps

- Hook backend to a GitHub App for repo write access to drop workflow files.
- Wire backend to call ArgoCD/Helm or your cluster API to create/delete preview namespaces.
- Point frontend forms to backend endpoints and embed Grafana/Loki dashboards.
