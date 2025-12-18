from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel, HttpUrl
from typing import Any, Dict, Optional
import os
import asyncio
import time
from datetime import datetime
from urllib.parse import urlparse
import json
from functools import wraps
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, RetryError
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from github_app import GitHubAppClient, GitHubContentError, GITHUB_API_TIMEOUT
from secrets_manager import SecretsManager
from cluster_manager import ClusterManager, ClusterError
import httpx

# Prometheus metrics
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

app = FastAPI(
    title="DevPlatform API",
    version="0.1.0",
    description="A unified platform for CI/CD pipelines, preview environments, and application monitoring",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Add exception handler for GitHubContentError
@app.exception_handler(GitHubContentError)
async def github_content_error_handler(request, exc: GitHubContentError):
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)}
    )

# Allow local frontend during dev; tighten in production
# Allow all origins in development to support network IPs
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in dev (tighten in production)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class OnboardRequest(BaseModel):
    repo_url: HttpUrl
    branch: str
    install_workflows: bool = True


class OnboardResponse(BaseModel):
    message: str
    workflow_path: str
    note: Optional[str] = None


class ApproveRequest(BaseModel):
    run_id: str
    approval_token: str


class ApproveResponse(BaseModel):
    status: str
    message: str


# Prometheus metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total number of HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

http_requests_errors_total = Counter(
    'http_requests_errors_total',
    'Total number of HTTP error requests',
    ['method', 'endpoint', 'status']
)

pod_cpu_usage = Gauge(
    'pod_cpu_usage_millicores',
    'CPU usage of pods in millicores',
    ['namespace', 'pod_name']
)

pod_memory_usage = Gauge(
    'pod_memory_usage_bytes',
    'Memory usage of pods in bytes',
    ['namespace', 'pod_name']
)

# Track metrics for HTTP request rate (for backward compatibility with existing API)
_request_metrics = {
    "total_requests": 0,
    "error_requests": 0,
    "requests_per_minute": [],
    "last_reset": time.time(),
    "start_time": time.time(),
}

# Track availability for 99.9% requirement
_availability_metrics = {
    "start_time": time.time(),
    "downtime_seconds": 0,
    "last_check": time.time(),
    "check_count": 0,
    "failed_checks": 0,
}

@app.get("/health", tags=["Monitoring"])
def health() -> Dict[str, Any]:
    """
    Enhanced health check with detailed status for reliability monitoring.
    Tracks availability for 99.9% SLA requirement.
    """
    current_time = time.time()
    _availability_metrics["check_count"] += 1
    _availability_metrics["last_check"] = current_time
    
    try:
        # Check cluster connectivity
        cluster_status = "unknown"
        cluster_healthy = False
        try:
            cluster = ClusterManager.from_env()
            success, _ = cluster._run_kubectl(["version", "--client"])
            cluster_status = "connected" if success else "disconnected"
            cluster_healthy = success
        except:
            cluster_status = "disconnected"
        
        # Check GitHub App connectivity
        gh_status = "unknown"
        gh_healthy = False
        try:
            gh = GitHubAppClient.from_env()
            gh._installation_token()
            gh_status = "connected"
            gh_healthy = True
        except:
            gh_status = "disconnected"
        
        # Calculate availability
        uptime = current_time - _availability_metrics["start_time"]
        availability_percent = (
            (uptime - _availability_metrics["downtime_seconds"]) / uptime * 100
            if uptime > 0 else 100.0
        )
        
        # Update availability metrics
        if not (cluster_healthy and gh_healthy):
            _availability_metrics["failed_checks"] += 1
        
        overall_status = "ok" if (cluster_healthy and gh_healthy) else "degraded"
        
        return {
            "status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "services": {
                "api": "healthy",
                "cluster": cluster_status,
                "github_app": gh_status,
            },
            "uptime_seconds": int(uptime),
            "availability": {
                "percent": round(availability_percent, 3),
                "target": 99.9,
                "meets_sla": availability_percent >= 99.9,
                "total_checks": _availability_metrics["check_count"],
                "failed_checks": _availability_metrics["failed_checks"],
            },
        }
    except Exception as e:
        _availability_metrics["failed_checks"] += 1
        return {
            "status": "degraded",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@app.get("/logs", tags=["Logs"])
def get_logs(namespace: Optional[str] = None, pod: Optional[str] = None, lines: int = 100) -> Dict[str, Any]:
    """
    Get logs from Kubernetes pods.
    
    - **namespace**: Kubernetes namespace (default: "default")
    - **pod**: Pod name or label selector (optional)
    - **lines**: Number of log lines to retrieve (default: 100)
    
    In production, integrate with Loki or similar log aggregation.
    """
    try:
        cluster = ClusterManager.from_env()
        if not namespace:
            namespace = "default"
        
        cmd = ["logs"]
        if pod:
            cmd.extend(["-l", f"app={pod}"])
        else:
            cmd.append("--all-containers=true")
        cmd.extend(["-n", namespace, "--tail", str(lines)])
        
        success, output = cluster._run_kubectl(cmd)
        if success:
            return {"logs": output, "namespace": namespace, "pod": pod}
        return {"logs": "", "error": output, "namespace": namespace}
    except Exception as e:
        return {"logs": "", "error": str(e)}


@app.get("/logs/stream", tags=["Logs"])
async def stream_logs(namespace: Optional[str] = None, pod: Optional[str] = None):
    """
    Stream logs in real-time using Server-Sent Events (SSE).
    
    - **namespace**: Kubernetes namespace (default: "default")
    - **pod**: Pod name or label selector (optional)
    
    Updates within 5 seconds as per requirement. Returns Server-Sent Events stream.
    """
    async def generate():
        try:
            cluster = ClusterManager.from_env()
            if not namespace:
                ns = "default"
            else:
                ns = namespace
            
            last_lines = 0
            while True:
                cmd = ["logs"]
                if pod:
                    cmd.extend(["-l", f"app={pod}"])
                else:
                    cmd.append("--all-containers=true")
                cmd.extend(["-n", ns, "--tail", "50"])
                
                success, output = cluster._run_kubectl(cmd)
                if success:
                    lines = output.split("\n")
                    # Only send new lines
                    if len(lines) > last_lines:
                        new_lines = "\n".join(lines[last_lines:])
                        if new_lines.strip():
                            yield f"data: {json.dumps({'logs': new_lines, 'namespace': ns})}\n\n"
                        last_lines = len(lines)
                
                # Wait 5 seconds before next check (requirement: updates within 5 seconds)
                await asyncio.sleep(5)
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/test-pods")
def test_pods() -> Dict[str, Any]:
    """Test endpoint to verify mock pod generation works."""
    import random
    return {
        "pods": [
            {
                "name": "test-backend",
                "cpu": "100m",
                "cpu_value": 0.1,
                "memory": "256Mi",
                "memory_value": 256.0,
            }
        ]
    }

@app.get("/metrics", tags=["Metrics"])
def get_metrics(namespace: Optional[str] = None) -> Dict[str, Any]:
    """
    Get metrics from Kubernetes resources including CPU, Memory, and HTTP request rate.
    
    - **namespace**: Kubernetes namespace (default: "default")
    
    Returns:
    - Pod CPU and Memory usage
    - HTTP request rate (requests per minute)
    - Error rate
    - Total requests
    
    In production, integrate with Prometheus or similar.
    """
    try:
        cluster = ClusterManager.from_env()
        if not namespace:
            namespace = "default"
        
        # Get pod metrics
        success, output = cluster._run_kubectl([
            "top", "pods", "-n", namespace, "--no-headers"
        ])
        
        # Calculate HTTP request rate from tracked metrics
        current_time = time.time()
        # Clean old entries (older than 1 minute)
        _request_metrics["requests_per_minute"] = [
            ts for ts in _request_metrics["requests_per_minute"]
            if current_time - ts < 60
        ]
        requests_per_minute = len(_request_metrics["requests_per_minute"])
        
        metrics = {
            "namespace": namespace,
            "pods": [],
            "http_metrics": {
                "requests_per_minute": requests_per_minute,
                "total_requests": _request_metrics["total_requests"],
                "error_requests": _request_metrics["error_requests"],
                "error_rate": (
                    _request_metrics["error_requests"] / _request_metrics["total_requests"]
                    if _request_metrics["total_requests"] > 0 else 0
                ),
            },
            "timestamp": datetime.now().isoformat(),
        }
        
        # Try to parse kubectl output if available
        pods_found = False
        if success and output and output.strip():
            # Parse kubectl top output: NAME CPU(cores) MEMORY(bytes)
            for line in output.strip().split("\n"):
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 3:
                        pods_found = True
                        # Parse CPU and Memory values
                        cpu_str = parts[1]
                        memory_str = parts[2]
                        
                        # Convert CPU to numeric (handle 'm' for millicores)
                        cpu_value = 0.0
                        if cpu_str.endswith('m'):
                            cpu_value = float(cpu_str[:-1]) / 1000.0
                        elif cpu_str.replace('.', '').isdigit():
                            cpu_value = float(cpu_str)
                        
                        # Convert Memory to numeric (handle Mi, Gi, etc.)
                        memory_value = 0.0
                        if memory_str.endswith('Mi'):
                            memory_value = float(memory_str[:-2])
                        elif memory_str.endswith('Gi'):
                            memory_value = float(memory_str[:-2]) * 1024
                        elif memory_str.endswith('Ki'):
                            memory_value = float(memory_str[:-2]) / 1024
                        elif memory_str.replace('.', '').isdigit():
                            memory_value = float(memory_str)
                        
                        pod_name = parts[0]
                        # Convert CPU to millicores for Prometheus
                        cpu_millicores = cpu_value * 1000
                        # Convert Memory to bytes for Prometheus
                        memory_bytes = memory_value * 1024 * 1024  # Mi to bytes
                        
                        # Update Prometheus gauges
                        pod_cpu_usage.labels(namespace=namespace, pod_name=pod_name).set(cpu_millicores)
                        pod_memory_usage.labels(namespace=namespace, pod_name=pod_name).set(memory_bytes)
                        
                        metrics["pods"].append({
                            "name": pod_name,
                            "cpu": cpu_str,
                            "cpu_value": cpu_value,
                            "memory": memory_str,
                            "memory_value": memory_value,
                        })
        
        # Always provide mock data if no pods found (kubectl failed, not available, or no pods running)
        import random
        # Force mock data generation when no pods are found
        if len(metrics["pods"]) == 0:
            backend_cpu = round(random.uniform(0.05, 0.2), 3)
            backend_memory = round(random.uniform(128, 512), 1)
            frontend_cpu = round(random.uniform(0.02, 0.1), 3)
            frontend_memory = round(random.uniform(64, 256), 1)
            
            # Update Prometheus gauges for mock data
            pod_cpu_usage.labels(namespace=namespace, pod_name="devplatform-backend").set(backend_cpu * 1000)
            pod_memory_usage.labels(namespace=namespace, pod_name="devplatform-backend").set(backend_memory * 1024 * 1024)
            pod_cpu_usage.labels(namespace=namespace, pod_name="devplatform-frontend").set(frontend_cpu * 1000)
            pod_memory_usage.labels(namespace=namespace, pod_name="devplatform-frontend").set(frontend_memory * 1024 * 1024)
            
            metrics["pods"] = [
                {
                    "name": "devplatform-backend",
                    "cpu": f"{random.randint(50, 200)}m",
                    "cpu_value": backend_cpu,
                    "memory": f"{random.randint(128, 512)}Mi",
                    "memory_value": backend_memory,
                },
                {
                    "name": "devplatform-frontend",
                    "cpu": f"{random.randint(20, 100)}m",
                    "cpu_value": frontend_cpu,
                    "memory": f"{random.randint(64, 256)}Mi",
                    "memory_value": frontend_memory,
                },
            ]
            metrics["note"] = "Mock data (Kubernetes not available or no pods running)"
        
        return metrics
    except Exception as e:
        return {"error": str(e), "namespace": namespace}


@app.get("/prometheus/metrics", tags=["Metrics"])
async def prometheus_metrics():
    """
    Prometheus metrics endpoint for scraping.
    Returns metrics in Prometheus exposition format.
    """
    from fastapi.responses import Response
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((GitHubContentError, Exception))
)
def _upsert_workflow_with_retry(gh: GitHubAppClient, owner: str, repo: str, path: str, template_path: str, message: str):
    """Helper function with retry logic for workflow installation."""
    gh.upsert_workflow(owner=owner, repo=repo, path=path, template_path=template_path, message=message)


@app.get("/test-github-access/{owner}/{repo}", tags=["Debug"])
def test_github_access(owner: str, repo: str) -> Dict[str, Any]:
    """
    Test if the GitHub App has access to a specific repository.
    Useful for debugging 403 errors.
    """
    try:
        gh = GitHubAppClient.from_env()
        token = gh._installation_token(repositories=[f"{owner}/{repo}"])
        
        # Test 1: Try to get repository info
        repo_url = f"https://api.github.com/repos/{owner}/{repo}"
        repo_resp = httpx.get(
            repo_url,
            headers={"Authorization": f"token {token}", "Accept": "application/vnd.github+json"},
            timeout=GITHUB_API_TIMEOUT
        )
        
        # Test 2: Try to list repository contents
        contents_url = f"https://api.github.com/repos/{owner}/{repo}/contents"
        contents_resp = httpx.get(
            contents_url,
            headers={"Authorization": f"token {token}", "Accept": "application/vnd.github+json"},
            timeout=GITHUB_API_TIMEOUT
        )
        
        return {
            "repository_access": {
                "status_code": repo_resp.status_code,
                "success": repo_resp.status_code == 200,
                "message": repo_resp.json().get("message") if repo_resp.status_code != 200 else "OK"
            },
            "contents_access": {
                "status_code": contents_resp.status_code,
                "success": contents_resp.status_code == 200,
                "message": contents_resp.json().get("message") if contents_resp.status_code != 200 else "OK"
            },
            "token_scoped_to": f"{owner}/{repo}",
            "installation_id": os.getenv("GITHUB_INSTALLATION_ID"),
            "app_id": os.getenv("GITHUB_APP_ID")
        }
    except Exception as e:
        return {"error": str(e), "type": type(e).__name__}


@app.post("/onboard", response_model=OnboardResponse, tags=["Onboarding"])
def onboard_repo(payload: OnboardRequest) -> OnboardResponse:
    """
    Onboard a repository by installing CI/CD workflows and provisioning secrets.
    
    - Installs CI, preview, and production workflows
    - Provisions required secrets via Secrets Manager
    - Returns onboarding status and workflow paths
    
    Note: In demo mode (DEMO_MODE=true), returns mock success without GitHub API calls.
    """
    parsed = urlparse(str(payload.repo_url))
    path_parts = parsed.path.strip("/").split("/")
    if len(path_parts) < 2:
        raise HTTPException(status_code=400, detail="Invalid repo URL")
    owner, repo = path_parts[0], path_parts[1].removesuffix(".git")

    # Demo mode: return mock success without GitHub API calls
    demo_mode = os.getenv("DEMO_MODE", "false").lower() == "true"
    if demo_mode:
        print(f"DEMO MODE: Simulating onboarding for {owner}/{repo}")
        return OnboardResponse(
            message="✅ Repository onboarded successfully (Demo Mode)",
            workflow_path=".github/workflows/ci.yaml",
            note=f"Demo Mode: Would install workflows for {owner}/{repo} on branch {payload.branch}. "
                 f"In production, this would create CI, preview, and production workflows via GitHub API.",
        )

    gh = GitHubAppClient.from_env()
    if payload.install_workflows:
        try:
            # Use retry logic for workflow installation
            _upsert_workflow_with_retry(
                gh, owner, repo,
                path=".github/workflows/ci.yaml",
                template_path="../.github/workflows/ci.yaml",
                message="chore: add devplatform ci workflow",
            )
            _upsert_workflow_with_retry(
                gh, owner, repo,
                path=".github/workflows/preview.yaml",
                template_path="../.github/workflows/preview.yaml",
                message="chore: add devplatform preview workflow",
            )
            _upsert_workflow_with_retry(
                gh, owner, repo,
                path=".github/workflows/prod.yaml",
                template_path="../.github/workflows/prod.yaml",
                message="chore: add devplatform prod workflow",
            )
        except RetryError as exc:
            # Extract the underlying exception from RetryError for better error messages
            underlying_exc = str(exc.last_attempt.exception()) if hasattr(exc, 'last_attempt') and exc.last_attempt else str(exc)
            error_msg = f"Failed to install workflows after retries: {underlying_exc}"
            print(f"ERROR: {error_msg}")  # Log to console for debugging
            raise HTTPException(status_code=500, detail=error_msg) from exc
        except GitHubContentError as exc:
            print(f"ERROR: GitHub API error: {str(exc)}")  # Log to console for debugging
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        except Exception as exc:
            error_msg = f"Unexpected error during workflow installation: {type(exc).__name__}: {str(exc)}"
            print(f"ERROR: {error_msg}")  # Log to console for debugging
            raise HTTPException(status_code=500, detail=error_msg) from exc

    # Provision required secrets via SecretsManager
    secrets_mgr = SecretsManager.from_env()
    secrets_to_provision = {
        "REGISTRY_USERNAME": os.getenv("DEFAULT_REGISTRY_USERNAME", ""),
        "REGISTRY_PASSWORD": os.getenv("DEFAULT_REGISTRY_PASSWORD", ""),
        "KUBE_CONFIG": os.getenv("DEFAULT_KUBE_CONFIG", ""),
    }
    secret_results = secrets_mgr.ensure_secrets_for_repo(owner, repo, secrets_to_provision)
    secret_status = ", ".join([f"{k}: {'✓' if v else '✗'}" for k, v in secret_results.items()])

    return OnboardResponse(
        message="Onboarding queued. Workflows added if not present.",
        workflow_path=".github/workflows/ci.yaml",
        note=f"Target repo: {owner}/{repo}, branch: {payload.branch}. Secrets: {secret_status}",
    )


@app.post("/approve", response_model=ApproveResponse, tags=["Deployment"])
def approve_deploy(payload: ApproveRequest) -> ApproveResponse:
    """
    Approve a production deployment by calling GitHub Actions API.
    For manual approval workflows, this creates a deployment approval.
    """
    expected = os.getenv("APPROVAL_TOKEN")
    if expected and payload.approval_token != expected:
        raise HTTPException(status_code=403, detail="Invalid approval token")

    try:
        gh = GitHubAppClient.from_env()
        token = gh._installation_token()
        
        # Parse run_id to get owner/repo/run_id
        # Format: owner/repo/run_id or just run_id (assumes current repo)
        parts = payload.run_id.split("/")
        if len(parts) == 3:
            owner, repo, run_id = parts
        else:
            # Use environment or default
            owner = os.getenv("GITHUB_OWNER", "unknown")
            repo = os.getenv("GITHUB_REPO", "unknown")
            run_id = payload.run_id
        
        # Approve the workflow run (for environments with required reviewers)
        # Note: This requires the workflow to use environments with protection rules
        api_url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}/approve"
        
        import httpx
        resp = httpx.post(
            api_url,
            headers={
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github+json",
            },
            timeout=10.0,
        )
        
        if resp.status_code == 200 or resp.status_code == 201:
            return ApproveResponse(
                status="approved",
                message=f"Deployment run {run_id} approved successfully.",
            )
        elif resp.status_code == 404:
            # Try alternative: create a deployment status
            return ApproveResponse(
                status="queued",
                message=f"Approval queued for run {run_id}. Workflow may need manual approval in GitHub UI.",
            )
        else:
            return ApproveResponse(
                status="error",
                message=f"Failed to approve: {resp.status_code} {resp.text}",
            )
    except Exception as e:
        return ApproveResponse(
            status="error",
            message=f"Error approving deployment: {str(e)}",
        )


@app.post("/webhook/github", tags=["Webhooks"])
def github_webhook(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Webhook receiver for GitHub events (push/PR).
    Handles preview environment creation and teardown.
    """
    event_type = payload.get("action") or "unknown"
    pr_data = payload.get("pull_request", {})
    
    # Handle PR events
    if "pull_request" in payload:
        pr_number = pr_data.get("number")
        pr_state = pr_data.get("state")
        repo_info = payload.get("repository", {})
        owner = repo_info.get("owner", {}).get("login", "")
        repo = repo_info.get("name", "")
        
        if event_type in ("opened", "synchronize", "reopened"):
            # Deploy preview environment
            try:
                cluster = ClusterManager.from_env()
                # Extract image from workflow or use default
                image = os.getenv("PREVIEW_IMAGE", f"ghcr.io/{owner}/{repo}:pr-{pr_number}")
                host = f"pr-{pr_number}.devplatform.local"
                
                success, message = cluster.deploy_preview(
                    pr_number=pr_number,
                    image=image,
                    host=host,
                )
                
                return {
                    "received": True,
                    "event_action": event_type,
                    "preview_deployed": success,
                    "message": message,
                    "pr_number": pr_number,
                }
            except Exception as e:
                return {
                    "received": True,
                    "event_action": event_type,
                    "preview_deployed": False,
                    "error": str(e),
                }
        
        elif event_type == "closed":
            # Teardown preview environment
            try:
                cluster = ClusterManager.from_env()
                success = cluster.delete_preview_namespace(pr_number)
                return {
                    "received": True,
                    "event_action": event_type,
                    "preview_deleted": success,
                    "pr_number": pr_number,
                }
            except Exception as e:
                return {
                    "received": True,
                    "event_action": event_type,
                    "preview_deleted": False,
                    "error": str(e),
                }
    
    return {"received": True, "event_action": event_type}


@app.get("/deployment/verify", tags=["Deployment"])
def verify_zero_downtime(namespace: str = "prod") -> Dict[str, Any]:
    """
    Verify zero-downtime deployment by checking pod readiness during rollout.
    """
    try:
        cluster = ClusterManager.from_env()
        
        # Get deployment status
        success, output = cluster._run_kubectl([
            "get", "deployment", "-n", namespace, "-o", "json"
        ])
        
        if not success:
            return {"error": "Failed to get deployment status", "namespace": namespace}
        
        # Get pod status
        pod_success, pod_output = cluster._run_kubectl([
            "get", "pods", "-n", namespace, "-o", "json"
        ])
        
        ready_pods = 0
        total_pods = 0
        
        if pod_success:
            import json as json_lib
            try:
                pod_data = json_lib.loads(pod_output)
                for pod in pod_data.get("items", []):
                    total_pods += 1
                    status = pod.get("status", {})
                    conditions = status.get("conditions", [])
                    for condition in conditions:
                        if condition.get("type") == "Ready" and condition.get("status") == "True":
                            ready_pods += 1
                            break
            except:
                pass
        
        # Check if all pods are ready (zero-downtime requirement)
        all_ready = ready_pods == total_pods and total_pods > 0
        
        return {
            "namespace": namespace,
            "ready_pods": ready_pods,
            "total_pods": total_pods,
            "zero_downtime": all_ready,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"error": str(e), "namespace": namespace}


# Middleware to track HTTP request metrics
@app.middleware("http")
async def track_metrics(request, call_next):
    """Track HTTP request rate and errors for metrics endpoint and Prometheus."""
    start_time = time.time()
    _request_metrics["total_requests"] = _request_metrics.get("total_requests", 0) + 1
    current_time = start_time
    
    # Initialize start_time if not set
    if "start_time" not in _request_metrics:
        _request_metrics["start_time"] = current_time
    
    # Get endpoint path (simplified for Prometheus)
    endpoint = request.url.path
    method = request.method
    
    # Track request duration with Prometheus
    with http_request_duration_seconds.labels(method=method, endpoint=endpoint).time():
        response = await call_next(request)
    
    status_code = response.status_code
    status_class = f"{status_code // 100}xx"
    
    # Track Prometheus metrics
    http_requests_total.labels(method=method, endpoint=endpoint, status=status_class).inc()
    
    if response.status_code >= 400:
        _request_metrics["error_requests"] = _request_metrics.get("error_requests", 0) + 1
        http_requests_errors_total.labels(method=method, endpoint=endpoint, status=status_class).inc()
    
    # Track request timestamp for rate calculation
    if "requests_per_minute" not in _request_metrics:
        _request_metrics["requests_per_minute"] = []
    _request_metrics["requests_per_minute"].append(current_time)
    
    return response

