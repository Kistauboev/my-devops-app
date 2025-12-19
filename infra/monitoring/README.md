# Prometheus & Grafana Setup

This directory contains Kubernetes manifests for deploying Prometheus and Grafana monitoring stack.

## Quick Start

### 1. Deploy Prometheus

```bash
kubectl apply -f prometheus-deployment.yaml
```

### 2. Deploy Grafana

```bash
kubectl apply -f grafana-deployment.yaml
```

### 3. Access the Services

**Prometheus:**
- Port-forward: `kubectl port-forward -n monitoring svc/prometheus 9090:9090`
- Access: http://localhost:9090

**Grafana:**
- Port-forward: `kubectl port-forward -n monitoring svc/grafana 3000:3000`
- Access: http://localhost:3000
- Default credentials: `admin` / `admin`

## Configuration

### Prometheus

Prometheus is configured to scrape:
- `devplatform-backend` service at `/prometheus/metrics` endpoint
- Any pods with annotation `prometheus.io/scrape: "true"`

Configuration is in `prometheus-deployment.yaml` ConfigMap.

### Grafana

Grafana comes pre-configured with:
- Prometheus datasource (auto-configured)
- DevPlatform dashboard with:
  - HTTP Requests Rate
  - HTTP Error Rate
  - Pod CPU Usage
  - Pod Memory Usage
  - Request Duration (p50, p95)

## Metrics Exposed

The backend exposes the following Prometheus metrics:

- `http_requests_total` - Total HTTP requests (labeled by method, endpoint, status)
- `http_requests_errors_total` - Total HTTP errors (labeled by method, endpoint, status)
- `http_request_duration_seconds` - HTTP request duration histogram
- `pod_cpu_usage_millicores` - Pod CPU usage in millicores (labeled by namespace, pod_name)
- `pod_memory_usage_bytes` - Pod memory usage in bytes (labeled by namespace, pod_name)

## Backend Endpoint

The backend exposes Prometheus metrics at:
- `/prometheus/metrics` - Prometheus exposition format

## Troubleshooting

### Check Prometheus Targets

1. Access Prometheus UI: http://localhost:9090
2. Go to Status → Targets
3. Verify `devplatform-backend` target is UP

### Check Grafana Datasource

1. Access Grafana UI: http://localhost:3000
2. Go to Configuration → Data Sources
3. Verify Prometheus datasource is configured and working

### View Logs

```bash
# Prometheus logs
kubectl logs -n monitoring deployment/prometheus

# Grafana logs
kubectl logs -n monitoring deployment/grafana
```

## Production Considerations

For production deployments, consider:
- Persistent storage for Prometheus (update volume to PersistentVolumeClaim)
- Persistent storage for Grafana (update volume to PersistentVolumeClaim)
- Ingress configuration for external access
- Authentication/authorization for Grafana
- Resource limits adjustment based on scale
- Prometheus retention policy adjustment
- AlertManager integration for alerting

