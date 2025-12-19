import os
import subprocess
import json
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Tuple


class ClusterError(Exception):
    """Raised when cluster operations fail."""


@dataclass
class ClusterManager:

    kubeconfig: Optional[str] = None
    namespace_prefix: str = "pr-"

    @classmethod
    def from_env(cls) -> "ClusterManager":
        kubeconfig = os.getenv("KUBE_CONFIG")
        return cls(kubeconfig=kubeconfig)

    def _run_kubectl(self, cmd: List[str]) -> Tuple[bool, str]:
        env = os.environ.copy()
        if self.kubeconfig:
            # Write kubeconfig to temp file or use KUBECONFIG env
            env["KUBECONFIG"] = self.kubeconfig
        
        try:
            result = subprocess.run(
                ["kubectl"] + cmd,
                capture_output=True,
                text=True,
                env=env,
                timeout=30,
            )
            return result.returncode == 0, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return False, "kubectl command timed out"
        except FileNotFoundError:
            return False, "kubectl not found"
        except Exception as e:
            return False, str(e)

    def create_preview_namespace(self, pr_number: int) -> bool:
        """Create a namespace for a preview environment."""
        namespace = f"{self.namespace_prefix}{pr_number}"
        success, output = self._run_kubectl(["create", "namespace", namespace, "--dry-run=client", "-o", "yaml"])
        if not success:
            # Try without dry-run
            success, _ = self._run_kubectl(["create", "namespace", namespace])
        return success

    def delete_preview_namespace(self, pr_number: int) -> bool:
        """Delete a preview environment namespace."""
        namespace = f"{self.namespace_prefix}{pr_number}"
        success, _ = self._run_kubectl(["delete", "namespace", namespace, "--ignore-not-found=true"])
        return success

    def deploy_preview(
        self, pr_number: int, image: str, host: str, release_name: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Deploy a preview environment using Helm.
        Returns (success, message).
        """
        namespace = f"{self.namespace_prefix}{pr_number}"
        if not release_name:
            release_name = f"preview-{pr_number}"
        
        # Ensure namespace exists
        self.create_preview_namespace(pr_number)
        
        # Run helm upgrade --install
        helm_cmd = [
            "helm", "upgrade", "--install", release_name,
            "infra/helm/devplatform",
            "--namespace", namespace,
            "--create-namespace",
            "--set", f"namespace={namespace}",
            "--set", f"image.repository={image.split(':')[0]}",
            "--set", f"image.tag={image.split(':')[1] if ':' in image else 'latest'}",
            "--set", f"ingress.host={host}",
        ]
        
        env = os.environ.copy()
        if self.kubeconfig:
            env["KUBECONFIG"] = self.kubeconfig
        
        try:
            result = subprocess.run(
                helm_cmd,
                capture_output=True,
                text=True,
                env=env,
                timeout=60,
            )
            if result.returncode == 0:
                return True, result.stdout
            return False, result.stderr
        except Exception as e:
            return False, str(e)

    def get_preview_status(self, pr_number: int) -> Dict[str, Any]:
        """Get status of a preview environment."""
        namespace = f"{self.namespace_prefix}{pr_number}"
        success, output = self._run_kubectl(["get", "namespace", namespace, "-o", "json"])
        if not success:
            return {"exists": False, "status": "not_found"}
        
        try:
            ns_data = json.loads(output)
            return {
                "exists": True,
                "status": ns_data.get("status", {}).get("phase", "unknown"),
            }
        except json.JSONDecodeError:
            return {"exists": True, "status": "unknown"}

