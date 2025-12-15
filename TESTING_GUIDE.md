# DevPlatform Testing Guide

This guide helps you test all the new features that were implemented.

## Prerequisites

1. **Backend Setup**
   ```bash
   cd backend
   python -m venv .venv
   # On Windows:
   .venv\Scripts\activate
   # On Linux/Mac:
   source .venv/bin/activate
   
   pip install -r requirements.txt
   ```

2. **Frontend Setup**
   ```bash
   cd frontend
   npm install
   ```

## Starting the Services

### Terminal 1: Backend
```bash
cd backend
# Activate virtual environment first
uvicorn main:app --reload --port 8000
```

The backend will be available at `http://localhost:8000`

### Terminal 2: Frontend
```bash
cd frontend
npm run dev
```

The frontend will be available at `http://localhost:5173`

## Testing the Features

### 1. Health Check Endpoint

**Test via Browser/curl:**
```bash
curl http://localhost:8000/health
```

**Expected Response:**
```json
{
  "status": "ok",
  "timestamp": "2025-12-15T...",
  "services": {
    "api": "healthy",
    "cluster": "connected" or "disconnected",
    "github_app": "connected" or "disconnected"
  },
  "uptime_seconds": 123
}
```

**Test via Frontend:**
1. Open `http://localhost:5173`
2. Click "Check backend health" button
3. Verify detailed health status is displayed

### 2. Real-time Log Streaming

**Test via Frontend:**
1. Navigate to "3) Logs (Real-time Streaming)" section
2. Enter a namespace (e.g., "default")
3. Click "Start Streaming"
4. You should see:
   - A green streaming indicator
   - Logs appearing in real-time (updates every 5 seconds)
5. Click "Stop Streaming" to stop

**Test via curl (SSE):**
```bash
curl -N http://localhost:8000/logs/stream?namespace=default
```

**Note:** For this to work, you need a Kubernetes cluster with pods running. Without a cluster, you'll see connection errors, which is expected.

### 3. Metrics Dashboard with Charts

**Test via Frontend:**
1. Navigate to "4) Metrics Dashboard" section
2. Enter a namespace (e.g., "default")
3. Metrics will auto-refresh every 60 seconds
4. You should see:
   - **HTTP Request Metrics Cards**: Requests/Min, Total Requests, Error Rate
   - **HTTP Request Rate Chart**: Line chart showing requests per minute over time
   - **CPU Usage Chart**: Line chart showing CPU usage per pod over time
   - **Memory Usage Chart**: Line chart showing memory usage per pod over time
   - **Pod Metrics Table**: Current CPU and Memory values for each pod

**Test via API:**
```bash
curl http://localhost:8000/metrics?namespace=default
```

**Expected Response:**
```json
{
  "namespace": "default",
  "pods": [
    {
      "name": "pod-name",
      "cpu": "100m",
      "cpu_value": 0.1,
      "memory": "256Mi",
      "memory_value": 256.0
    }
  ],
  "http_metrics": {
    "requests_per_minute": 5,
    "total_requests": 42,
    "error_requests": 2,
    "error_rate": 0.0476
  },
  "timestamp": "2025-12-15T..."
}
```

**Note:** Metrics will accumulate as you make API requests. The HTTP metrics track requests to the API itself.

### 4. On-demand Logs

**Test via Frontend:**
1. Navigate to "3) Logs" section
2. Enter a namespace
3. Click "Fetch Logs"
4. Logs should appear in the text area

**Test via API:**
```bash
curl "http://localhost:8000/logs?namespace=default&lines=50"
```

### 5. Zero-downtime Deployment Verification

**Test via API:**
```bash
curl "http://localhost:8000/deployment/verify?namespace=prod"
```

**Expected Response:**
```json
{
  "namespace": "prod",
  "ready_pods": 3,
  "total_pods": 3,
  "zero_downtime": true,
  "timestamp": "2025-12-15T..."
}
```

## Testing Without Kubernetes

If you don't have a Kubernetes cluster set up, you can still test:

1. **Health Check** - Will work, but cluster status will show "disconnected"
2. **HTTP Metrics** - Will work and track API requests
3. **Logs/Metrics Endpoints** - Will return errors (expected without cluster)
4. **Frontend UI** - All UI components will work, but some features require a cluster

## Testing the Complete Flow

### 1. Onboard a Repository
1. In the frontend, enter a GitHub repository URL
2. Enter a branch name (e.g., "main")
3. Click "Submit"
4. **Note:** This requires GitHub App credentials to be set in environment variables

### 2. Approve Production Deployment
1. Enter a GitHub Actions run ID
2. Enter the approval token (from `APPROVAL_TOKEN` env var)
3. Click "Approve"
4. **Note:** This requires GitHub App credentials and a valid run ID

## Environment Variables for Full Testing

To test all features, set these environment variables:

```bash
# GitHub App (for onboarding and approvals)
export GITHUB_APP_ID="your_app_id"
export GITHUB_INSTALLATION_ID="your_installation_id"
export GITHUB_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n..."

# Approval token
export APPROVAL_TOKEN="your_secret_token"

# Kubernetes (for logs, metrics, deployments)
export KUBE_CONFIG="your_kubeconfig_content"

# Optional: Secrets Manager
export VAULT_ADDR="http://vault:8200"
export VAULT_TOKEN="your_vault_token"
```

## Automated Testing

Run the backend test suite:

```bash
cd backend
pytest test_main.py -v
```

All 7 tests should pass:
- ✅ Health endpoint test
- ✅ Onboard endpoint test (missing env)
- ✅ Approve endpoint test (invalid token)
- ✅ Approve endpoint test (valid token)
- ✅ Webhook endpoint test
- ✅ Logs endpoint test
- ✅ Metrics endpoint test

## Troubleshooting

### Frontend not connecting to backend
- Check that backend is running on port 8000
- Check CORS settings in `backend/main.py`
- Verify `VITE_API_BASE` environment variable if using custom URL

### Logs/Metrics not working
- Ensure Kubernetes cluster is accessible
- Check `KUBE_CONFIG` environment variable
- Verify `kubectl` is installed and working

### Charts not displaying
- Check browser console for errors
- Verify `recharts` is installed: `npm list recharts`
- Ensure metrics data is being received (check Network tab)

### Real-time streaming not working
- Check browser console for EventSource errors
- Verify backend is running and accessible
- Check that SSE endpoint is responding: `curl -N http://localhost:8000/logs/stream`

## Next Steps

1. **Set up a Kubernetes cluster** (minikube, kind, or cloud provider)
2. **Configure GitHub App** for repository onboarding
3. **Set up secrets manager** (Vault or GitHub Secrets API)
4. **Deploy to production** using the Helm charts

For more details, see `IMPLEMENTATION_SUMMARY.md`.

