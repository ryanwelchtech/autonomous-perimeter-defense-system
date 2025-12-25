"""
Authentication Service - Zero Trust JWT-based Authentication
Provides JWT token generation, validation, and RBAC for APDS microservices.
"""

import os
import time
import jwt
import redis
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="APDS Authentication Service", version="1.0.0")
security = HTTPBearer()

# Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "changeme_in_production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION = int(os.getenv("JWT_EXPIRATION", "3600"))
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

# Redis client
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

# Role-based permissions
ROLE_PERMISSIONS = {
    "admin": ["read", "write", "delete", "manage"],
    "operator": ["read", "write"],
    "viewer": ["read"],
    "service": ["read", "write"]  # For service-to-service auth
}

# User database (in production, use PostgreSQL)
USERS_DB = {
    "admin": {
        "password": "admin123",  # In production, use hashed passwords
        "role": "admin",
        "permissions": ROLE_PERMISSIONS["admin"]
    },
    "operator": {
        "password": "operator123",
        "role": "operator",
        "permissions": ROLE_PERMISSIONS["operator"]
    },
    "viewer": {
        "password": "viewer123",
        "role": "viewer",
        "permissions": ROLE_PERMISSIONS["viewer"]
    }
}

# Service accounts for inter-service communication
SERVICE_ACCOUNTS = {
    "cv-detection-service": {
        "role": "service",
        "permissions": ROLE_PERMISSIONS["service"]
    },
    "ml-classification-service": {
        "role": "service",
        "permissions": ROLE_PERMISSIONS["service"]
    },
    "alert-service": {
        "role": "service",
        "permissions": ROLE_PERMISSIONS["service"]
    },
    "api-gateway": {
        "role": "service",
        "permissions": ROLE_PERMISSIONS["service"]
    }
}


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    role: str
    permissions: List[str]


class TokenValidation(BaseModel):
    valid: bool
    username: Optional[str] = None
    role: Optional[str] = None
    permissions: Optional[List[str]] = None
    expires_at: Optional[datetime] = None


def create_token(username: str, role: str, permissions: List[str], service_account: bool = False) -> str:
    """Create JWT token with user/service claims."""
    expiration = datetime.utcnow() + timedelta(seconds=JWT_EXPIRATION)
    payload = {
        "sub": username,
        "role": role,
        "permissions": permissions,
        "service_account": service_account,
        "iat": datetime.utcnow(),
        "exp": expiration
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    # Store token in Redis for revocation checking
    redis_client.setex(f"token:{username}:{token}", JWT_EXPIRATION, "valid")
    
    return token


def verify_token(token: str) -> Dict:
    """Verify JWT token and return claims."""
    try:
        # Check if token is revoked
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username = payload.get("sub")
        
        # Check Redis for revocation
        if redis_client.exists(f"token:{username}:{token}") == 0:
            raise HTTPException(status_code=401, detail="Token revoked or expired")
        
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def check_permission(required_permission: str):
    """Dependency to check user permissions."""
    async def permission_checker(credentials: HTTPAuthorizationCredentials = Depends(security)):
        token = credentials.credentials
        payload = verify_token(token)
        permissions = payload.get("permissions", [])
        
        if required_permission not in permissions:
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions. Required: {required_permission}"
            )
        
        return payload
    
    return permission_checker


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        redis_client.ping()
        return {
            "status": "healthy",
            "service": "auth-service",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "auth-service",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@app.post("/login", response_model=TokenResponse)
async def login(login_request: LoginRequest):
    """Authenticate user and return JWT token."""
    user = USERS_DB.get(login_request.username)
    
    if not user or user["password"] != login_request.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_token(
        login_request.username,
        user["role"],
        user["permissions"],
        service_account=False
    )
    
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=JWT_EXPIRATION,
        role=user["role"],
        permissions=user["permissions"]
    )


@app.post("/service-token")
async def get_service_token(service_name: str = Header(..., alias="X-Service-Name")):
    """Generate service account token for inter-service authentication."""
    service = SERVICE_ACCOUNTS.get(service_name)
    
    if not service:
        raise HTTPException(status_code=403, detail="Invalid service name")
    
    token = create_token(
        service_name,
        service["role"],
        service["permissions"],
        service_account=True
    )
    
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=JWT_EXPIRATION,
        role=service["role"],
        permissions=service["permissions"]
    )


@app.post("/validate", response_model=TokenValidation)
async def validate_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Validate JWT token and return claims."""
    token = credentials.credentials
    
    try:
        payload = verify_token(token)
        exp_timestamp = payload.get("exp")
        expires_at = datetime.utcnow() + timedelta(seconds=exp_timestamp - int(time.time()))
        
        return TokenValidation(
            valid=True,
            username=payload.get("sub"),
            role=payload.get("role"),
            permissions=payload.get("permissions", []),
            expires_at=expires_at
        )
    except HTTPException as e:
        return TokenValidation(valid=False)


@app.post("/revoke")
async def revoke_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Revoke JWT token."""
    token = credentials.credentials
    
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username = payload.get("sub")
        
        # Remove from Redis
        redis_client.delete(f"token:{username}:{token}")
        
        return {"message": "Token revoked successfully"}
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


@app.get("/permissions")
async def get_permissions(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user permissions."""
    token = credentials.credentials
    payload = verify_token(token)
    
    return {
        "username": payload.get("sub"),
        "role": payload.get("role"),
        "permissions": payload.get("permissions", []),
        "service_account": payload.get("service_account", False)
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

