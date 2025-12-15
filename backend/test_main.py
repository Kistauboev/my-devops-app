"""
Basic tests for DevPlatform API endpoints.
Run with: pytest backend/test_main.py
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import os

# Import after setting up mocks
from main import app

client = TestClient(app)


def test_health_endpoint():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok" or data["status"] == "degraded"
    assert "timestamp" in data


def test_onboard_endpoint_missing_env():
    """Test onboard endpoint without GitHub App credentials."""
    # Clear environment and test that it raises an error
    with patch.dict(os.environ, {}, clear=True):
        response = client.post(
            "/onboard",
            json={"repo_url": "https://github.com/test/repo", "branch": "main"},
        )
        # Should fail without GitHub App credentials (raises GitHubContentError which becomes 500)
        assert response.status_code == 500
        assert "Missing GitHub App configuration" in response.json()["detail"]


def test_approve_endpoint_invalid_token():
    """Test approve endpoint with invalid token."""
    os.environ["APPROVAL_TOKEN"] = "secret123"
    response = client.post(
        "/approve",
        json={"run_id": "123", "approval_token": "wrong_token"},
    )
    assert response.status_code == 403


def test_approve_endpoint_valid_token():
    """Test approve endpoint with valid token."""
    os.environ["APPROVAL_TOKEN"] = "secret123"
    with patch("main.GitHubAppClient") as mock_gh:
        mock_instance = MagicMock()
        mock_instance._installation_token.return_value = "fake_token"
        mock_gh.from_env.return_value = mock_instance
        
        with patch("httpx.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.text = "OK"
            
            response = client.post(
                "/approve",
                json={"run_id": "123", "approval_token": "secret123"},
            )
            # Should succeed or return queued status
            assert response.status_code in (200, 201)


def test_webhook_endpoint():
    """Test webhook endpoint."""
    response = client.post(
        "/webhook/github",
        json={"action": "opened", "pull_request": {"number": 1, "state": "open"}},
    )
    assert response.status_code == 200
    assert "received" in response.json()


def test_logs_endpoint():
    """Test logs endpoint."""
    with patch("main.ClusterManager") as mock_cluster:
        mock_instance = MagicMock()
        mock_instance._run_kubectl.return_value = (True, "test logs")
        mock_cluster.from_env.return_value = mock_instance
        
        response = client.get("/logs?namespace=default")
        assert response.status_code == 200
        assert "logs" in response.json()


def test_metrics_endpoint():
    """Test metrics endpoint."""
    with patch("main.ClusterManager") as mock_cluster:
        mock_instance = MagicMock()
        mock_instance._run_kubectl.return_value = (True, "pod1 100m 200Mi")
        mock_cluster.from_env.return_value = mock_instance
        
        response = client.get("/metrics?namespace=default")
        assert response.status_code == 200
        assert "namespace" in response.json()

