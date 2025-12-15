from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, HttpUrl
from typing import Any, Dict, Optional
import os
import asyncio
import time
from datetime import datetime
from urllib.parse import urlparse
import json

from github_app import GitHubAppClient, GitHubContentError
from secrets_manager import SecretsManager
from cluster_manager import ClusterManager, ClusterError

app = FastAPI(title="DevPlatform API", version="0.1.0")

# Add exception handler for GitHubContentError
@app.exception_handler(GitHubContentError)
async def github_content_error_handler(request, exc: GitHubContentError):
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)}
    )

# Allow local frontend during dev; tighten in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
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


# Track metrics for HTTP request rate
_request_metrics = {
    "total_requests": 0,
    "error_requests": 0,
    "requests_per_minute": [],
    "last_reset": time.time(),
}

@app.get("/health")
def health() -> Dict[str, Any]:
    """Enhanced health check with detailed status for reliability monitoring."""
    try:
        # Check cluster connectivity
        cluster_status = "unknown"
        try:
            cluster = ClusterManager.from_env()
            success, _ = cluster._run_kubectl(["version", "--client"])
            cluster_status = "connected" if success else "disconnected"
        except:
            cluster_status = "disconnected"
        
        # Check GitHub App connectivity
        gh_status = "unknown"
        try:
            gh = GitHubAppClient.from_env()
            gh._installation_token()
            gh_status = "connected"
        except:
            gh_status = "disconnected"
        
        return {
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "api": "healthy",
                "cluster": cluster_status,
                "github_app": gh_status,
            },
            "uptime_seconds": int(time.time() - _request_metrics.get("start_time", time.time())),
        }
    except Exception as e:
        return {
            "status": "degraded",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


@app.get("/logs")
def get_logs(namespace: Optional[str] = None, pod: Optional[str] = None, lines: int = 100) -> Dict[str, Any]:
    """
    Get logs from Kubernetes pods.
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


@app.get("/logs/stream")
async def stream_logs(namespace: Optional[str] = None, pod: Optional[str] = None):
    """
    Stream logs in real-time using Server-Sent Events (SSE).
    Updates within 5 seconds as per requirement.
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


@app.get("/metrics")
def get_metrics(namespace: Optional[str] = None) -> Dict[str, Any]:
    """
    Get metrics from Kubernetes resources including CPU, Memory, and HTTP request rate.
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
        
        # If no pods found and kubectl failed, provide mock data for testing/demo
        if not success or not output:
            # Generate mock pod data for demonstration when Kubernetes is not available
            import random
            mock_pods = [
                {
                    "name": "devplatform-backend",
                    "cpu": f"{random.randint(50, 200)}m",
                    "cpu_value": random.uniform(0.05, 0.2),
                    "memory": f"{random.randint(128, 512)}Mi",
                    "memory_value": random.uniform(128, 512),
                },
                {
                    "name": "devplatform-frontend",
                    "cpu": f"{random.randint(20, 100)}m",
                    "cpu_value": random.uniform(0.02, 0.1),
                    "memory": f"{random.randint(64, 256)}Mi",
                    "memory_value": random.uniform(64, 256),
                },
            ]
            metrics["pods"] = mock_pods
            metrics["note"] = "Mock data (Kubernetes not available)"
        
        if success and output:
            # Parse kubectl top output: NAME CPU(cores) MEMORY(bytes)
            for line in output.strip().split("\n"):
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 3:
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
                        
                        metrics["pods"].append({
                            "name": parts[0],
                            "cpu": cpu_str,
                            "cpu_value": cpu_value,
                            "memory": memory_str,
                            "memory_value": memory_value,
                        })
        
        # If no pods found (no Kubernetes or no pods running), provide mock data for demo
        if len(metrics["pods"]) == 0:
            import random
            mock_pods = [
                {
                    "name": "devplatform-backend",
                    "cpu": f"{random.randint(50, 200)}m",
                    "cpu_value": random.uniform(0.05, 0.2),
                    "memory": f"{random.randint(128, 512)}Mi",
                    "memory_value": random.uniform(128, 512),
                },
                {
                    "name": "devplatform-frontend",
                    "cpu": f"{random.randint(20, 100)}m",
                    "cpu_value": random.uniform(0.02, 0.1),
                    "memory": f"{random.randint(64, 256)}Mi",
                    "memory_value": random.uniform(64, 256),
                },
            ]
            metrics["pods"] = mock_pods
            metrics["note"] = "Mock data (Kubernetes not available or no pods running)"
        
        return metrics
    except Exception as e:
        return {"error": str(e), "namespace": namespace}


@app.post("/onboard", response_model=OnboardResponse)
def onboard_repo(payload: OnboardRequest) -> OnboardResponse:
    """
    Placeholder for onboarding logic.
    Intended flow: use GitHub App token to add CI/preview/prod workflows
    to the target repo and bootstrap secrets via your secrets manager.
    """
    parsed = urlparse(str(payload.repo_url))
    path_parts = parsed.path.strip("/").split("/")
    if len(path_parts) < 2:
        raise HTTPException(status_code=400, detail="Invalid repo URL")
    owner, repo = path_parts[0], path_parts[1].removesuffix(".git")

    gh = GitHubAppClient.from_env()
    if payload.install_workflows:
        try:
            gh.upsert_workflow(
                owner=owner,
                repo=repo,
                path=".github/workflows/ci.yaml",
                template_path="../.github/workflows/ci.yaml",
                message="chore: add devplatform ci workflow",
            )
            gh.upsert_workflow(
                owner=owner,
                repo=repo,
                path=".github/workflows/preview.yaml",
                template_path="../.github/workflows/preview.yaml",
                message="chore: add devplatform preview workflow",
            )
            gh.upsert_workflow(
                owner=owner,
                repo=repo,
                path=".github/workflows/prod.yaml",
                template_path="../.github/workflows/prod.yaml",
                message="chore: add devplatform prod workflow",
            )
        except GitHubContentError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

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


@app.post("/approve", response_model=ApproveResponse)
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


@app.post("/webhook/github")
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


@app.get("/deployment/verify")
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
    """Track HTTP request rate and errors for metrics endpoint."""
    _request_metrics["total_requests"] = _request_metrics.get("total_requests", 0) + 1
    current_time = time.time()
    
    # Initialize start_time if not set
    if "start_time" not in _request_metrics:
        _request_metrics["start_time"] = current_time
    
    response = await call_next(request)
    
    if response.status_code >= 400:
        _request_metrics["error_requests"] = _request_metrics.get("error_requests", 0) + 1
    
    # Track request timestamp for rate calculation
    if "requests_per_minute" not in _request_metrics:
        _request_metrics["requests_per_minute"] = []
    _request_metrics["requests_per_minute"].append(current_time)
    
    return response

