from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from typing import Any, Dict, Optional
import os
from urllib.parse import urlparse

from github_app import GitHubAppClient, GitHubContentError
from secrets_manager import SecretsManager

app = FastAPI(title="DevPlatform API", version="0.1.0")

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


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


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

    # TODO: Wire SecretsManager to provision required secrets (registry, kubeconfig) via Vault/ESO
    SecretsManager.from_env()  # currently no-op placeholder

    return OnboardResponse(
        message="Onboarding queued. Workflows added if not present.",
        workflow_path=".github/workflows/ci.yaml",
        note=f"Target repo: {owner}/{repo}, branch: {payload.branch}",
    )


@app.post("/approve", response_model=ApproveResponse)
def approve_deploy(payload: ApproveRequest) -> ApproveResponse:
    """
    Intended flow: call GitHub Actions to continue a paused prod deploy job.
    """
    expected = os.getenv("APPROVAL_TOKEN")
    if expected and payload.approval_token != expected:
        raise HTTPException(status_code=403, detail="Invalid approval token")

    # TODO: invoke GitHub Actions workflow_run to resume production job
    return ApproveResponse(
        status="queued",
        message=f"Approval accepted for run {payload.run_id}. Implement GH Actions resume call.",
    )


@app.post("/webhook/github")
def github_webhook(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Placeholder webhook receiver for GitHub events (push/PR).
    """
    event_type = payload.get("action") or "unknown"
    # TODO: route to preview deploy/destroy based on PR events
    return {"received": True, "event_action": event_type}

