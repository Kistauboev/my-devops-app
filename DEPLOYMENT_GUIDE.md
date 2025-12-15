# DevPlatform Deployment Guide

Complete guide for deploying DevPlatform to production.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development](#local-development)
3. [Docker Deployment](#docker-deployment)
4. [Kubernetes Deployment](#kubernetes-deployment)
5. [GitHub App Setup](#github-app-setup)
6. [Secrets Management](#secrets-management)
7. [Production Checklist](#production-checklist)

## Prerequisites

- Docker and Docker Compose (for containerized deployment)
- Kubernetes cluster (for production deployment)
- kubectl configured
- Helm 3.x (for Kubernetes deployment)
- GitHub App (for repository onboarding)

## Local Development

### Option 1: Using Docker Compose

```bash
# Copy environment variables
cp .env.example .env
# Edit .env with your values

# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Option 2: Manual Start

See `QUICK_START.md` for detailed instructions.

## Docker Deployment

### Build Images

```bash
# Build backend
cd backend
docker build -t devplatform-backend:latest .

# Build frontend
cd ../frontend
docker build -t devplatform-frontend:latest .
```

### Run Containers

```bash
# Backend
docker run -d \
  --name devplatform-backend \
  -p 8000:8000 \
  --env-file .env \
  devplatform-backend:latest

# Frontend
docker run -d \
  --name devplatform-frontend \
  -p 80:80 \
  -e VITE_API_BASE=http://your-backend-url:8000 \
  devplatform-frontend:latest
```

## Kubernetes Deployment

### Using Helm Chart

The project includes a Helm chart for deploying applications managed by DevPlatform.

#### Deploy a Preview Environment

```bash
helm upgrade --install preview-123 infra/helm/devplatform \
  --namespace pr-123 \
  --create-namespace \
  --set image.repository=ghcr.io/your-org/your-app \
  --set image.tag=pr-123-abc123 \
  --set ingress.host=pr-123.devplatform.local \
  --set namespace=pr-123
```

#### Deploy Production

```bash
helm upgrade --install prod infra/helm/devplatform \
  --namespace prod \
  --create-namespace \
  --set image.repository=ghcr.io/your-org/your-app \
  --set image.tag=latest \
  --set ingress.host=app.devplatform.local \
  --set namespace=prod \
  --set replicaCount=3
```

### Deploy DevPlatform Itself

To deploy the DevPlatform backend and frontend to Kubernetes:

#### 1. Create Namespace

```bash
kubectl create namespace devplatform
```

#### 2. Create Secrets

```bash
kubectl create secret generic devplatform-secrets \
  --from-literal=GITHUB_APP_ID=your_app_id \
  --from-literal=GITHUB_INSTALLATION_ID=your_installation_id \
  --from-literal=GITHUB_PRIVATE_KEY="$(cat your-private-key.pem)" \
  --from-literal=APPROVAL_TOKEN=your_token \
  --from-literal=KUBE_CONFIG="$(cat ~/.kube/config | base64)" \
  -n devplatform
```

#### 3. Deploy Backend

```yaml
# backend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: devplatform-backend
  namespace: devplatform
spec:
  replicas: 2
  selector:
    matchLabels:
      app: devplatform-backend
  template:
    metadata:
      labels:
        app: devplatform-backend
    spec:
      containers:
      - name: backend
        image: devplatform-backend:latest
        ports:
        - containerPort: 8000
        envFrom:
        - secretRef:
            name: devplatform-secrets
        resources:
          requests:
            memory: "256Mi"
            cpu: "200m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: devplatform-backend
  namespace: devplatform
spec:
  selector:
    app: devplatform-backend
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP
```

```bash
kubectl apply -f backend-deployment.yaml
```

#### 4. Deploy Frontend

```yaml
# frontend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: devplatform-frontend
  namespace: devplatform
spec:
  replicas: 2
  selector:
    matchLabels:
      app: devplatform-frontend
  template:
    metadata:
      labels:
        app: devplatform-frontend
    spec:
      containers:
      - name: frontend
        image: devplatform-frontend:latest
        ports:
        - containerPort: 80
        env:
        - name: VITE_API_BASE
          value: "http://devplatform-backend.devplatform.svc.cluster.local"
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "200m"
---
apiVersion: v1
kind: Service
metadata:
  name: devplatform-frontend
  namespace: devplatform
spec:
  selector:
    app: devplatform-frontend
  ports:
  - port: 80
    targetPort: 80
  type: ClusterIP
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: devplatform-frontend
  namespace: devplatform
spec:
  ingressClassName: nginx
  rules:
  - host: devplatform.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: devplatform-frontend
            port:
              number: 80
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: devplatform-backend
            port:
              number: 80
```

```bash
kubectl apply -f frontend-deployment.yaml
```

## GitHub App Setup

### 1. Create GitHub App

1. Go to your GitHub organization settings
2. Navigate to "Developer settings" > "GitHub Apps"
3. Click "New GitHub App"
4. Configure:
   - **Name**: DevPlatform
   - **Homepage URL**: Your DevPlatform URL
   - **Webhook URL**: `https://your-domain.com/webhook/github`
   - **Webhook secret**: Generate a secure secret
   - **Repository permissions**:
     - Contents: Read & Write
     - Metadata: Read-only
     - Secrets: Read & Write (for secrets API)
   - **Subscribe to events**: Pull requests, Push

### 2. Install GitHub App

1. After creating the app, click "Install App"
2. Select the organization or repositories
3. Note the **Installation ID** from the URL

### 3. Generate Private Key

1. In your GitHub App settings, click "Generate a private key"
2. Save the `.pem` file securely
3. Convert to environment variable format:
   ```bash
   # Replace newlines with \n
   cat your-app.pem | sed ':a;N;$!ba;s/\n/\\n/g'
   ```

### 4. Configure Environment Variables

```bash
export GITHUB_APP_ID=123456
export GITHUB_INSTALLATION_ID=12345678
export GITHUB_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n..."
```

## Secrets Management

### Option 1: HashiCorp Vault

```bash
# Install Vault (example)
helm repo add hashicorp https://helm.releases.hashicorp.com
helm install vault hashicorp/vault

# Configure environment
export VAULT_ADDR=http://vault:8200
export VAULT_TOKEN=your-token
```

### Option 2: GitHub Secrets API

Uses the GitHub App token automatically when available.

### Option 3: Kubernetes Secrets

```bash
kubectl create secret generic app-secrets \
  --from-literal=REGISTRY_USERNAME=username \
  --from-literal=REGISTRY_PASSWORD=password \
  -n your-namespace
```

## Production Checklist

### Security

- [ ] All secrets stored in secrets manager (no hardcoded values)
- [ ] HTTPS/TLS enabled for all endpoints
- [ ] CORS configured for production domains only
- [ ] Rate limiting implemented
- [ ] Authentication/authorization added (if needed)
- [ ] Security headers configured

### Reliability

- [ ] Health checks configured
- [ ] Readiness and liveness probes set
- [ ] Resource limits and requests defined
- [ ] Rolling update strategy configured (zero-downtime)
- [ ] Monitoring and alerting set up
- [ ] Log aggregation configured (Loki, ELK, etc.)
- [ ] Metrics collection configured (Prometheus, etc.)

### Performance

- [ ] Horizontal pod autoscaling configured
- [ ] Resource limits appropriate for workload
- [ ] CDN configured for frontend (if applicable)
- [ ] Database connection pooling (if applicable)
- [ ] Caching strategy implemented

### Operations

- [ ] Backup strategy for persistent data
- [ ] Disaster recovery plan
- [ ] Documentation complete
- [ ] Runbooks for common issues
- [ ] CI/CD pipelines tested
- [ ] Rollback procedures documented

### Testing

- [ ] All unit tests passing
- [ ] Integration tests passing
- [ ] Load testing completed
- [ ] Security scanning completed
- [ ] 24-hour availability test (for 99.9% requirement)

## Monitoring

### Health Checks

```bash
# Check backend health
curl http://your-backend:8000/health

# Expected response:
{
  "status": "ok",
  "services": {
    "api": "healthy",
    "cluster": "connected",
    "github_app": "connected"
  }
}
```

### Metrics Endpoint

```bash
curl http://your-backend:8000/metrics?namespace=prod
```

### Logs

```bash
# Stream logs
curl -N http://your-backend:8000/logs/stream?namespace=prod
```

## Troubleshooting

### Backend Not Starting

1. Check environment variables are set correctly
2. Verify GitHub App credentials
3. Check Kubernetes connectivity (if using KUBE_CONFIG)
4. Review logs: `docker logs devplatform-backend` or `kubectl logs -n devplatform devplatform-backend`

### Frontend Not Connecting

1. Verify `VITE_API_BASE` is set correctly
2. Check CORS settings in backend
3. Verify backend is accessible from frontend
4. Check browser console for errors

### Preview Environments Not Deploying

1. Verify webhook is configured correctly
2. Check GitHub App has repository permissions
3. Verify Kubernetes cluster is accessible
4. Check Helm chart is valid: `helm template test infra/helm/devplatform`

### Production Deployment Failing

1. Check approval token is correct
2. Verify GitHub Actions run ID is valid
3. Check Kubernetes cluster connectivity
4. Verify image exists in registry
5. Check resource limits and quotas

## Support

For issues or questions:
- Review `TESTING_GUIDE.md` for testing procedures
- Check `IMPLEMENTATION_SUMMARY.md` for feature details
- Review logs and metrics endpoints for diagnostics

