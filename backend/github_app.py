import base64
import json
import os
import time
from dataclasses import dataclass
from typing import Optional

import httpx
import jwt


class GitHubContentError(Exception):
    """Raised when GitHub content API calls fail."""


@dataclass
class GitHubAppClient:
    app_id: str
    installation_id: str
    private_key: str
    api_base: str = "https://api.github.com"

    @classmethod
    def from_env(cls) -> "GitHubAppClient":
        app_id = os.getenv("GITHUB_APP_ID")
        installation_id = os.getenv("GITHUB_INSTALLATION_ID")
        private_key = os.getenv("GITHUB_PRIVATE_KEY")
        if not all([app_id, installation_id, private_key]):
            raise GitHubContentError(
                "Missing GitHub App configuration (GITHUB_APP_ID, "
                "GITHUB_INSTALLATION_ID, GITHUB_PRIVATE_KEY)"
            )
        return cls(app_id=app_id, installation_id=installation_id, private_key=private_key)

    def _app_jwt(self) -> str:
        now = int(time.time())
        payload = {
            "iat": now - 60,
            "exp": now + (10 * 60),
            "iss": self.app_id,
        }
        return jwt.encode(payload, self.private_key, algorithm="RS256")

    def _installation_token(self) -> str:
        jwt_token = self._app_jwt()
        url = f"{self.api_base}/app/installations/{self.installation_id}/access_tokens"
        resp = httpx.post(url, headers={"Authorization": f"Bearer {jwt_token}", "Accept": "application/vnd.github+json"})
        if resp.status_code >= 300:
            raise GitHubContentError(f"Failed to create installation token: {resp.status_code} {resp.text}")
        return resp.json()["token"]

    def upsert_workflow(self, owner: str, repo: str, path: str, template_path: str, message: str) -> None:
        """
        Writes or updates a workflow file in the target repo using GitHub contents API.
        template_path is relative to backend/main.py file location (../.github/...).
        """
        token = self._installation_token()
        target_url = f"{self.api_base}/repos/{owner}/{repo}/contents/{path}"

        # resolve template content
        base_dir = os.path.dirname(os.path.abspath(__file__))
        source = os.path.join(base_dir, template_path)
        if not os.path.exists(source):
            raise GitHubContentError(f"Template not found: {template_path}")
        with open(source, "rb") as f:
            content_bytes = f.read()
        content_b64 = base64.b64encode(content_bytes).decode()

        # fetch current sha if exists
        sha: Optional[str] = None
        get_resp = httpx.get(
            target_url,
            headers={"Authorization": f"token {token}", "Accept": "application/vnd.github+json"},
        )
        if get_resp.status_code == 200:
            sha = get_resp.json().get("sha")
        elif get_resp.status_code not in (404,):
            raise GitHubContentError(f"Failed to read target path: {get_resp.status_code} {get_resp.text}")

        payload = {
            "message": message,
            "content": content_b64,
            "branch": "main",
        }
        if sha:
            payload["sha"] = sha

        put_resp = httpx.put(
            target_url,
            headers={"Authorization": f"token {token}", "Accept": "application/vnd.github+json"},
            content=json.dumps(payload),
        )
        if put_resp.status_code >= 300:
            raise GitHubContentError(f"Failed to write workflow: {put_resp.status_code} {put_resp.text}")

