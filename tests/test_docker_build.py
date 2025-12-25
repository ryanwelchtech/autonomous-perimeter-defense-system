"""
Test cases to verify Docker builds succeed.
These tests check that Dockerfiles can build successfully.
"""

import subprocess
import os
import sys
import pytest


def run_docker_build(dockerfile_path, tag, context="."):
    """Run docker build and return success status."""
    try:
        result = subprocess.run(
            ["docker", "build", "-f", dockerfile_path, "-t", tag, context],
            capture_output=True,
            text=True,
            timeout=300
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Build timed out after 5 minutes"
    except FileNotFoundError:
        pytest.skip("Docker not available")


def test_auth_service_dockerfile():
    """Test that auth service Dockerfile builds successfully."""
    success, stdout, stderr = run_docker_build(
        "services/auth/Dockerfile",
        "apds-auth:test"
    )
    if not success:
        print(f"Build failed:\n{stderr}")
    assert success, f"Auth service build failed: {stderr}"


def test_cv_detection_service_dockerfile():
    """Test that CV detection service Dockerfile builds successfully."""
    success, stdout, stderr = run_docker_build(
        "services/cv_detection/Dockerfile",
        "apds-cv:test"
    )
    if not success:
        print(f"Build failed:\n{stderr}")
    assert success, f"CV detection service build failed: {stderr}"


def test_ml_classification_service_dockerfile():
    """Test that ML classification service Dockerfile builds successfully."""
    success, stdout, stderr = run_docker_build(
        "services/ml_classification/Dockerfile",
        "apds-ml:test"
    )
    if not success:
        print(f"Build failed:\n{stderr}")
    assert success, f"ML classification service build failed: {stderr}"


def test_alert_service_dockerfile():
    """Test that alert service Dockerfile builds successfully."""
    success, stdout, stderr = run_docker_build(
        "services/alert/Dockerfile",
        "apds-alert:test"
    )
    if not success:
        print(f"Build failed:\n{stderr}")
    assert success, f"Alert service build failed: {stderr}"


def test_api_gateway_dockerfile():
    """Test that API gateway Dockerfile builds successfully."""
    success, stdout, stderr = run_docker_build(
        "services/api_gateway/Dockerfile",
        "apds-gateway:test"
    )
    if not success:
        print(f"Build failed:\n{stderr}")
    assert success, f"API gateway build failed: {stderr}"


def test_dashboard_dockerfile():
    """Test that dashboard Dockerfile builds successfully."""
    success, stdout, stderr = run_docker_build(
        "dashboard/Dockerfile",
        "apds-dashboard:test"
    )
    if not success:
        print(f"Build failed:\n{stderr}")
    assert success, f"Dashboard build failed: {stderr}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

