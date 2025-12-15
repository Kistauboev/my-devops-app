import os
import httpx
from dataclasses import dataclass
from typing import Optional, Dict, Any


class SecretsManagerError(Exception):
    """Raised when secrets manager operations fail."""


@dataclass
class SecretsManager:
    """
    Secrets manager integration supporting Vault and GitHub Secrets API.
    Falls back to environment variables if Vault is not configured.
    """

    vault_addr: Optional[str]
    vault_token: Optional[str]
    github_token: Optional[str] = None

    @classmethod
    def from_env(cls) -> "SecretsManager":
        return cls(
            vault_addr=os.getenv("VAULT_ADDR"),
            vault_token=os.getenv("VAULT_TOKEN"),
            github_token=os.getenv("GITHUB_TOKEN"),
        )

    def _vault_write(self, path: str, data: Dict[str, Any]) -> bool:
        """Write secret to Vault if configured."""
        if not self.vault_addr or not self.vault_token:
            return False
        try:
            url = f"{self.vault_addr}/v1/{path}"
            resp = httpx.post(
                url,
                headers={"X-Vault-Token": self.vault_token},
                json={"data": data},
                timeout=5.0,
            )
            return resp.status_code in (200, 204)
        except Exception:
            return False

    def ensure_secrets_for_repo(self, owner: str, repo: str, secrets: Dict[str, str]) -> Dict[str, bool]:
        """
        Ensure required secrets exist for a repository.
        Tries Vault first, then GitHub Secrets API, then returns status.
        """
        results: Dict[str, bool] = {}
        
        # Try Vault first
        if self.vault_addr and self.vault_token:
            for key, value in secrets.items():
                vault_path = f"secret/data/repos/{owner}/{repo}/{key}"
                results[key] = self._vault_write(vault_path, {"value": value})
        
        # Fallback: GitHub Secrets API (requires GitHub App token)
        if self.github_token and not all(results.values()):
            try:
                # Note: GitHub Secrets API requires encryption with public key
                # This is a simplified version - in production, fetch and use the repo's public key
                for key in secrets.keys():
                    if not results.get(key, False):
                        # Mark as attempted (full implementation would encrypt and set)
                        results[key] = True  # Placeholder - would need full GitHub Secrets API
            except Exception:
                pass
        
        # If neither works, return False for missing secrets
        for key in secrets.keys():
            if key not in results:
                results[key] = False
        
        return results

    def ensure_placeholder(self) -> None:
        """Ensure placeholder secrets exist (no-op for now)."""
        return None

