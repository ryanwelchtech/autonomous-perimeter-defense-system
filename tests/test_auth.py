"""
Tests for authentication service.
"""

import pytest
import sys
import os

# Add services to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services', 'auth'))

from main import app, create_token, verify_token
from fastapi.testclient import TestClient

client = TestClient(app)


def test_health_check():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code in [200, 503]  # May be unhealthy if Redis not available


def test_login_success():
    """Test successful login."""
    response = client.post("/login", json={
        "username": "admin",
        "password": "admin123"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_failure():
    """Test failed login."""
    response = client.post("/login", json={
        "username": "admin",
        "password": "wrong_password"
    })
    assert response.status_code == 401


def test_token_creation():
    """Test token creation."""
    token = create_token("test_user", "viewer", ["read"], False)
    assert token is not None
    assert isinstance(token, str)


def test_token_verification():
    """Test token verification."""
    token = create_token("test_user", "viewer", ["read"], False)
    payload = verify_token(token)
    assert payload["sub"] == "test_user"
    assert payload["role"] == "viewer"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

