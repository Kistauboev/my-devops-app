# DevPlatform

A unified platform to onboard repos, auto-configure CI/CD, spin up preview environments, surface logs/metrics, and support prod deploys with manual approval.

## Structure

- `backend/` FastAPI API with:
  - Repository onboarding with GitHub App integration
  - Production deployment approval via GitHub Actions API
  - Webhook handler for automatic preview environment management
  - Logs and metrics endpoints
  - Secrets management (Vault/GitHub Secrets API support)
  - Kubernetes cluster management for preview environments
- `frontend/` Vite + React UI with:
  - Repository onboarding form
  - Production approval interface
  - Logs viewer
  - Metrics dashboard
- `infra/helm/devplatform/` Helm chart for deploying applications with ingress
- `.github/workflows/` CI, preview, and prod pipeline templates

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

## API Endpoints

- `GET /health` - Enhanced health check with service status and uptime
- `POST /onboard` - Onboard a repository (adds workflows, provisions secrets)
- `POST /approve` - Approve a production deployment
- `POST /webhook/github` - GitHub webhook receiver (handles PR events for preview environments)
- `GET /logs` - Fetch logs from Kubernetes pods (on-demand)
- `GET /logs/stream` - Stream logs in real-time using Server-Sent Events (SSE)
- `GET /metrics` - Fetch metrics from Kubernetes resources (CPU, Memory, HTTP rate)
- `GET /deployment/verify` - Verify zero-downtime deployment status

## Environment Variables

### Backend

- `GITHUB_APP_ID` - GitHub App ID
- `GITHUB_INSTALLATION_ID` - GitHub App installation ID
- `GITHUB_PRIVATE_KEY` - GitHub App private key (PEM format)
- `APPROVAL_TOKEN` - Token for production approval endpoint
- `KUBE_CONFIG` - Kubernetes kubeconfig (base64 encoded or file path)
- `VAULT_ADDR` - Vault server address (optional)
- `VAULT_TOKEN` - Vault authentication token (optional)
- `GITHUB_TOKEN` - GitHub token for secrets API (optional)

### Frontend

- `VITE_API_BASE` - Backend API base URL (default: http://localhost:8000)

## Secrets & Security

- No secrets are stored in code. Workflows expect registry creds and kubeconfig to be provided via secrets.
- Secrets Manager supports Vault and GitHub Secrets API with fallback to environment variables.
- Production deployments require manual approval via the `/approve` endpoint.

## Testing

Run backend tests:

```bash
cd backend
pytest test_main.py -v
```

Run frontend linting:

```bash
cd frontend
npm run lint
```

## Features Implemented

✅ Repository onboarding with workflow installation  
✅ GitHub App integration for repository access  
✅ Production deployment approval  
✅ Webhook-based preview environment management  
✅ **Real-time log streaming** (Server-Sent Events)  
✅ **Metrics dashboard with interactive charts** (CPU, Memory, HTTP rate)  
✅ **Auto-refreshing metrics** (updates every minute)  
✅ **HTTP request rate and error tracking**  
✅ **Enhanced health checks** with service status  
✅ **Zero-downtime deployment verification**  
✅ Logs retrieval from Kubernetes  
✅ Metrics retrieval from Kubernetes  
✅ Secrets management (Vault/GitHub Secrets API)  
✅ Cluster management for preview environments  
✅ Basic test suite

## Next Steps (Optional Enhancements)

- Integrate with Loki for advanced log aggregation
- Integrate with Prometheus/Grafana for advanced metrics
- Add authentication/authorization
- Add database for state management
- Enhance error handling and retry logic
- Add more comprehensive tests
