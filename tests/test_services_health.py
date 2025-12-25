"""
Test cases to verify services start and respond to health checks.
These tests require Docker Compose to be running.
"""

import pytest
import requests
import time
import os


def wait_for_service(url, timeout=60, interval=2):
    """Wait for a service to become available."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return True
        except requests.RequestException:
            pass
        time.sleep(interval)
    return False


@pytest.mark.integration
def test_auth_service_health():
    """Test auth service health endpoint."""
    if not wait_for_service("http://localhost:8001/health"):
        pytest.skip("Auth service not available")
    
    response = requests.get("http://localhost:8001/health", timeout=5)
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "auth-service"


@pytest.mark.integration
def test_cv_detection_service_health():
    """Test CV detection service health endpoint."""
    if not wait_for_service("http://localhost:8002/health"):
        pytest.skip("CV detection service not available")
    
    response = requests.get("http://localhost:8002/health", timeout=5)
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "cv-detection-service"


@pytest.mark.integration
def test_ml_classification_service_health():
    """Test ML classification service health endpoint."""
    if not wait_for_service("http://localhost:8003/health"):
        pytest.skip("ML classification service not available")
    
    response = requests.get("http://localhost:8003/health", timeout=5)
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "ml-classification-service"


@pytest.mark.integration
def test_alert_service_health():
    """Test alert service health endpoint."""
    if not wait_for_service("http://localhost:8004/health"):
        pytest.skip("Alert service not available")
    
    response = requests.get("http://localhost:8004/health", timeout=5)
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "alert-service"


@pytest.mark.integration
def test_api_gateway_health():
    """Test API gateway health endpoint."""
    if not wait_for_service("http://localhost:8000/health"):
        pytest.skip("API gateway not available")
    
    response = requests.get("http://localhost:8000/health", timeout=5)
    assert response.status_code == 200
    data = response.json()
    assert "services" in data


@pytest.mark.integration
def test_auth_login():
    """Test authentication login endpoint."""
    if not wait_for_service("http://localhost:8000/auth/login"):
        pytest.skip("API gateway not available")
    
    response = requests.post(
        "http://localhost:8000/auth/login",
        json={"username": "admin", "password": "admin123"},
        timeout=5
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])

