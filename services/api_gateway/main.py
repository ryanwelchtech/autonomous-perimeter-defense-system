"""
API Gateway - Zero Trust Service Mesh Gateway
Routes requests to backend services with authentication and authorization.
"""

import os
import requests
import redis
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends, Request, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI(title="APDS API Gateway", version="1.0.0")
security = HTTPBearer()

# Configuration
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8000")
CV_DETECTION_SERVICE_URL = os.getenv("CV_DETECTION_SERVICE_URL", "http://cv-detection-service:8000")
ML_CLASSIFICATION_SERVICE_URL = os.getenv("ML_CLASSIFICATION_SERVICE_URL", "http://ml-classification-service:8000")
ALERT_SERVICE_URL = os.getenv("ALERT_SERVICE_URL", "http://alert-service:8000")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

# Redis client for caching
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service routing map
SERVICE_ROUTES = {
    "/auth": AUTH_SERVICE_URL,
    "/cv": CV_DETECTION_SERVICE_URL,
    "/ml": ML_CLASSIFICATION_SERVICE_URL,
    "/alerts": ALERT_SERVICE_URL,
}


def verify_token(token: str) -> dict:
    """Verify JWT token with auth service."""
    try:
        response = requests.post(
            f"{AUTH_SERVICE_URL}/validate",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5
        )
        if response.status_code == 200:
            result = response.json()
            if result.get("valid"):
                return result
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    except requests.RequestException:
        raise HTTPException(status_code=503, detail="Authentication service unavailable")


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Get current user from token."""
    token = credentials.credentials
    return verify_token(token)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    service_health = {}
    
    # Check all services
    for service_name, service_url in SERVICE_ROUTES.items():
        try:
            response = requests.get(f"{service_url}/health", timeout=2)
            service_health[service_name] = {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "response_time_ms": response.elapsed.total_seconds() * 1000
            }
        except Exception as e:
            service_health[service_name] = {
                "status": "unhealthy",
                "error": str(e)
            }
    
    # Check Redis
    try:
        redis_client.ping()
        redis_status = "healthy"
    except Exception:
        redis_status = "unhealthy"
    
    all_healthy = all(
        s.get("status") == "healthy" 
        for s in service_health.values()
    ) and redis_status == "healthy"
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "services": service_health,
        "redis": redis_status
    }


@app.post("/auth/login")
async def login(request: Request):
    """Proxy login request to auth service."""
    body = await request.json()
    try:
        response = requests.post(
            f"{AUTH_SERVICE_URL}/login",
            json=body,
            timeout=5
        )
        return JSONResponse(
            content=response.json(),
            status_code=response.status_code
        )
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Auth service error: {str(e)}")


@app.get("/auth/permissions")
async def get_permissions(current_user: dict = Depends(get_current_user)):
    """Get current user permissions."""
    return current_user


@app.post("/cv/detect")
async def detect_objects(request: Request, current_user: dict = Depends(get_current_user)):
    """Proxy detection request to CV service."""
    body = await request.json()
    try:
        # Get service token
        service_token_response = requests.post(
            f"{AUTH_SERVICE_URL}/service-token",
            headers={"X-Service-Name": "api-gateway"},
            timeout=5
        )
        if service_token_response.status_code != 200:
            raise HTTPException(status_code=503, detail="Failed to get service token")
        
        service_token = service_token_response.json()["access_token"]
        
        response = requests.post(
            f"{CV_DETECTION_SERVICE_URL}/detect",
            json=body,
            headers={"Authorization": f"Bearer {service_token}"},
            timeout=30
        )
        return JSONResponse(
            content=response.json(),
            status_code=response.status_code
        )
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail=f"CV service error: {str(e)}")


@app.get("/cv/stats")
async def get_cv_stats(current_user: dict = Depends(get_current_user)):
    """Get CV detection statistics."""
    try:
        service_token_response = requests.post(
            f"{AUTH_SERVICE_URL}/service-token",
            headers={"X-Service-Name": "api-gateway"},
            timeout=5
        )
        service_token = service_token_response.json()["access_token"]
        
        response = requests.get(
            f"{CV_DETECTION_SERVICE_URL}/stats",
            headers={"Authorization": f"Bearer {service_token}"},
            timeout=5
        )
        return JSONResponse(
            content=response.json(),
            status_code=response.status_code
        )
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail=f"CV service error: {str(e)}")


@app.get("/ml/stats")
async def get_ml_stats(current_user: dict = Depends(get_current_user)):
    """Get ML classification statistics."""
    try:
        service_token_response = requests.post(
            f"{AUTH_SERVICE_URL}/service-token",
            headers={"X-Service-Name": "api-gateway"},
            timeout=5
        )
        service_token = service_token_response.json()["access_token"]
        
        response = requests.get(
            f"{ML_CLASSIFICATION_SERVICE_URL}/stats",
            headers={"Authorization": f"Bearer {service_token}"},
            timeout=5
        )
        return JSONResponse(
            content=response.json(),
            status_code=response.status_code
        )
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail=f"ML service error: {str(e)}")


@app.get("/alerts")
async def get_alerts(
    limit: int = 100,
    acknowledged: Optional[bool] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get alerts."""
    try:
        service_token_response = requests.post(
            f"{AUTH_SERVICE_URL}/service-token",
            headers={"X-Service-Name": "api-gateway"},
            timeout=5
        )
        service_token = service_token_response.json()["access_token"]
        
        params = {"limit": limit}
        if acknowledged is not None:
            params["acknowledged"] = acknowledged
        
        response = requests.get(
            f"{ALERT_SERVICE_URL}/alerts",
            params=params,
            headers={"Authorization": f"Bearer {service_token}"},
            timeout=5
        )
        return JSONResponse(
            content=response.json(),
            status_code=response.status_code
        )
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Alert service error: {str(e)}")


@app.get("/alerts/recent")
async def get_recent_alerts(
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """Get recent alerts."""
    try:
        service_token_response = requests.post(
            f"{AUTH_SERVICE_URL}/service-token",
            headers={"X-Service-Name": "api-gateway"},
            timeout=5
        )
        service_token = service_token_response.json()["access_token"]
        
        response = requests.get(
            f"{ALERT_SERVICE_URL}/alerts/recent",
            params={"limit": limit},
            headers={"Authorization": f"Bearer {service_token}"},
            timeout=5
        )
        return JSONResponse(
            content=response.json(),
            status_code=response.status_code
        )
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Alert service error: {str(e)}")


@app.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    username: str,
    current_user: dict = Depends(get_current_user)
):
    """Acknowledge an alert."""
    try:
        service_token_response = requests.post(
            f"{AUTH_SERVICE_URL}/service-token",
            headers={"X-Service-Name": "api-gateway"},
            timeout=5
        )
        service_token = service_token_response.json()["access_token"]
        
        response = requests.post(
            f"{ALERT_SERVICE_URL}/alerts/{alert_id}/acknowledge",
            params={"username": username},
            headers={"Authorization": f"Bearer {service_token}"},
            timeout=5
        )
        return JSONResponse(
            content=response.json(),
            status_code=response.status_code
        )
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Alert service error: {str(e)}")


@app.get("/alerts/stats")
async def get_alert_stats(current_user: dict = Depends(get_current_user)):
    """Get alert statistics."""
    try:
        service_token_response = requests.post(
            f"{AUTH_SERVICE_URL}/service-token",
            headers={"X-Service-Name": "api-gateway"},
            timeout=5
        )
        service_token = service_token_response.json()["access_token"]
        
        response = requests.get(
            f"{ALERT_SERVICE_URL}/stats",
            headers={"Authorization": f"Bearer {service_token}"},
            timeout=5
        )
        return JSONResponse(
            content=response.json(),
            status_code=response.status_code
        )
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Alert service error: {str(e)}")


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": "APDS API Gateway",
        "version": "1.0.0",
        "endpoints": {
            "auth": "/auth/login",
            "cv": "/cv/detect",
            "ml": "/ml/stats",
            "alerts": "/alerts",
            "health": "/health"
        },
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

