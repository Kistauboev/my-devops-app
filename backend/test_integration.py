import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, Mock
import os
import json
from main import app

client = TestClient(app)


class TestOnboardingWorkflow:
    """Test repository onboarding workflow."""
    
    @patch("main.GitHubAppClient")
    @patch("main.SecretsManager")
    def test_onboard_repository_success(self, mock_secrets, mock_gh):
        """Test successful repository onboarding."""
        # Setup mocks
        mock_gh_instance = MagicMock()
        mock_gh.from_env.return_value = mock_gh_instance
        
        mock_secrets_instance = MagicMock()
        mock_secrets_instance.ensure_secrets_for_repo.return_value = {
            "REGISTRY_USERNAME": True,
            "REGISTRY_PASSWORD": True,
            "KUBE_CONFIG": True,
        }
        mock_secrets.from_env.return_value = mock_secrets_instance
        
        # Test request
        response = client.post(
            "/onboard",
            json={
                "repo_url": "https://github.com/test-org/test-repo",
                "branch": "main",
                "install_workflows": True,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "workflow_path" in data
        assert mock_gh_instance.upsert_workflow.call_count == 3  # ci, preview, prod
    
    def test_onboard_invalid_url(self):
        """Test onboarding with invalid repository URL."""
        response = client.post(
            "/onboard",
            json={
                "repo_url": "not-a-url",
                "branch": "main",
            },
        )
        assert response.status_code == 422  
    
    def test_onboard_missing_github_app(self):
        """Test onboarding without GitHub App configuration."""
        with patch.dict(os.environ, {}, clear=True):
            response = client.post(
                "/onboard",
                json={
                    "repo_url": "https://github.com/test/repo",
                    "branch": "main",
                },
            )
            assert response.status_code == 500


class TestPreviewEnvironmentWorkflow:

    
    @patch("main.ClusterManager")
    def test_webhook_pr_opened(self, mock_cluster):
        """Test webhook handling for PR opened event."""
        mock_instance = MagicMock()
        mock_instance.deploy_preview.return_value = (True, "Deployed successfully")
        mock_cluster.from_env.return_value = mock_instance
        
        webhook_payload = {
            "action": "opened",
            "pull_request": {
                "number": 42,
                "state": "open",
            },
            "repository": {
                "owner": {"login": "test-org"},
                "name": "test-repo",
            },
        }
        
        response = client.post("/webhook/github", json=webhook_payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["received"] is True
        assert data["preview_deployed"] is True
        assert data["pr_number"] == 42
    
    @patch("main.ClusterManager")
    def test_webhook_pr_closed(self, mock_cluster):
        """Test webhook handling for PR closed event."""
        mock_instance = MagicMock()
        mock_instance.delete_preview_namespace.return_value = True
        mock_cluster.from_env.return_value = mock_instance
        
        webhook_payload = {
            "action": "closed",
            "pull_request": {
                "number": 42,
                "state": "closed",
            },
            "repository": {
                "owner": {"login": "test-org"},
                "name": "test-repo",
            },
        }
        
        response = client.post("/webhook/github", json=webhook_payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["received"] is True
        assert data["preview_deleted"] is True


class TestLogsWorkflow:
    
    @patch("main.ClusterManager")
    def test_fetch_logs(self, mock_cluster):
        """Test fetching logs from Kubernetes."""
        mock_instance = MagicMock()
        mock_instance._run_kubectl.return_value = (True, "test log line 1\ntest log line 2")
        mock_cluster.from_env.return_value = mock_instance
        
        response = client.get("/logs?namespace=default&lines=100")
        
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data
        assert "test log line 1" in data["logs"]
    
    @patch("main.ClusterManager")
    def test_stream_logs_sse(self, mock_cluster):
        """Test streaming logs via Server-Sent Events."""
        mock_instance = MagicMock()
        mock_instance._run_kubectl.return_value = (True, "log line 1\nlog line 2")
        mock_cluster.from_env.return_value = mock_instance
        
        response = client.get("/logs/stream?namespace=default")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"


class TestMetricsWorkflow:

    
    @patch("main.ClusterManager")
    def test_fetch_metrics(self, mock_cluster):
        """Test fetching metrics from Kubernetes."""
        mock_instance = MagicMock()
        mock_instance._run_kubectl.return_value = (
            True,
            "pod1 100m 256Mi\npod2 200m 512Mi"
        )
        mock_cluster.from_env.return_value = mock_instance
        
        response = client.get("/metrics?namespace=default")
        
        assert response.status_code == 200
        data = response.json()
        assert "namespace" in data
        assert "pods" in data
        assert "http_metrics" in data
        assert len(data["pods"]) >= 0


class TestProductionDeploymentWorkflow:
    """Test production deployment approval workflow."""
    
    @patch("main.GitHubAppClient")
    @patch("httpx.post")
    def test_approve_deployment_success(self, mock_post, mock_gh):
        """Test successful production deployment approval."""
        os.environ["APPROVAL_TOKEN"] = "test-token-123"
        
        mock_gh_instance = MagicMock()
        mock_gh_instance._installation_token.return_value = "github-token"
        mock_gh.from_env.return_value = mock_gh_instance
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        mock_post.return_value = mock_response
        
        response = client.post(
            "/approve",
            json={
                "run_id": "123456",
                "approval_token": "test-token-123",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("approved", "queued")
    
    def test_approve_deployment_invalid_token(self):
        """Test approval with invalid token."""
        os.environ["APPROVAL_TOKEN"] = "correct-token"
        
        response = client.post(
            "/approve",
            json={
                "run_id": "123456",
                "approval_token": "wrong-token",
            },
        )
        
        assert response.status_code == 403
    
    @patch("main.ClusterManager")
    def test_verify_zero_downtime(self, mock_cluster):
        """Test zero-downtime deployment verification."""
        mock_instance = MagicMock()
        
        # Mock deployment JSON
        deployment_json = {
            "items": [{
                "metadata": {"name": "test-deployment"},
                "status": {"readyReplicas": 2, "replicas": 2},
            }]
        }
        
        # Mock pods JSON
        pods_json = {
            "items": [
                {
                    "status": {
                        "conditions": [
                            {"type": "Ready", "status": "True"}
                        ]
                    }
                },
                {
                    "status": {
                        "conditions": [
                            {"type": "Ready", "status": "True"}
                        ]
                    }
                }
            ]
        }
        
        mock_instance._run_kubectl.side_effect = [
            (True, json.dumps(deployment_json)),
            (True, json.dumps(pods_json)),
        ]
        mock_cluster.from_env.return_value = mock_instance
        
        response = client.get("/deployment/verify?namespace=prod")
        
        assert response.status_code == 200
        data = response.json()
        assert "zero_downtime" in data
        assert data["ready_pods"] == 2
        assert data["total_pods"] == 2


class TestHealthMonitoring:
    """Test health check and monitoring."""
    
    def test_health_check_basic(self):
        """Test basic health check."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "services" in data
    
    @patch("main.ClusterManager")
    @patch("main.GitHubAppClient")
    def test_health_check_with_services(self, mock_gh, mock_cluster):
        """Test health check with service status."""
        mock_cluster_instance = MagicMock()
        mock_cluster_instance._run_kubectl.return_value = (True, "version info")
        mock_cluster.from_env.return_value = mock_cluster_instance
        
        mock_gh_instance = MagicMock()
        mock_gh_instance._installation_token.return_value = "token"
        mock_gh.from_env.return_value = mock_gh_instance
        
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["services"]["cluster"] == "connected"
        assert data["services"]["github_app"] == "connected"
        assert "availability" in data


class TestErrorHandling:
    """Test error handling and resilience."""
    
    @patch("main.ClusterManager")
    def test_logs_endpoint_error_handling(self, mock_cluster):
        """Test logs endpoint handles errors gracefully."""
        mock_instance = MagicMock()
        mock_instance._run_kubectl.return_value = (False, "kubectl error")
        mock_cluster.from_env.return_value = mock_instance
        
        response = client.get("/logs?namespace=default")
        
        # Should return 200 with error in response
        assert response.status_code == 200
        data = response.json()
        assert "error" in data or "logs" in data
    
    @patch("main.ClusterManager")
    def test_metrics_endpoint_error_handling(self, mock_cluster):
        """Test metrics endpoint handles errors gracefully."""
        mock_instance = MagicMock()
        mock_instance._run_kubectl.side_effect = Exception("Connection error")
        mock_cluster.from_env.return_value = mock_instance
        
        response = client.get("/metrics?namespace=default")
        
        # Should return 200 with error or mock data
        assert response.status_code == 200
        data = response.json()
        # Should have pods (mock data) or error
        assert "pods" in data or "error" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])












