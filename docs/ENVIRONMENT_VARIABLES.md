# Environment Variables Guide

This document describes all environment variables used in the APDS system and which ones you need to update for production deployment.

## Required Environment Variables

### Production Deployment (MUST CHANGE)

These variables **must** be changed from defaults for any production deployment:

#### JWT_SECRET
- **Default**: `changeme_in_production`
- **Description**: Secret key used for signing JWT tokens
- **How to generate**: Use a strong random string (32+ characters)
  ```bash
  openssl rand -hex 32
  ```
- **Where used**: Auth service, API Gateway
- **Security**: Critical - compromise allows token forgery

#### POSTGRES_PASSWORD
- **Default**: `changeme_in_production`
- **Description**: PostgreSQL database password
- **How to generate**: Use a strong random password (16+ characters)
  ```bash
  openssl rand -base64 24
  ```
- **Where used**: PostgreSQL, ML Classification Service, Alert Service
- **Security**: Critical - protects database access

### Optional Configuration Variables

These can be customized but have reasonable defaults:

#### JWT Configuration
- **JWT_ALGORITHM**: Algorithm for JWT signing (default: `HS256`)
- **JWT_EXPIRATION**: Token expiration in seconds (default: `3600` = 1 hour)

#### Database Configuration
- **POSTGRES_HOST**: Database hostname (default: `postgres` for Docker, `localhost` for local)
- **POSTGRES_PORT**: Database port (default: `5432`)
- **POSTGRES_DB**: Database name (default: `apds`)
- **POSTGRES_USER**: Database user (default: `apds_user`)

#### Redis Configuration
- **REDIS_HOST**: Redis hostname (default: `redis` for Docker, `localhost` for local)
- **REDIS_PORT**: Redis port (default: `6379`)

#### Service URLs (for inter-service communication)
These are typically set automatically by Docker Compose but can be overridden:
- **AUTH_SERVICE_URL**: Auth service URL (default: `http://auth-service:8000`)
- **CV_DETECTION_SERVICE_URL**: CV service URL (default: `http://cv-detection-service:8000`)
- **ML_CLASSIFICATION_SERVICE_URL**: ML service URL (default: `http://ml-classification-service:8000`)
- **ALERT_SERVICE_URL**: Alert service URL (default: `http://alert-service:8000`)

#### CV Detection Configuration
- **MODEL_PATH**: Path to YOLOv8 model file (default: `/app/models/yolov8n.pt`)
- **CONFIDENCE_THRESHOLD**: Detection confidence threshold 0.0-1.0 (default: `0.5`)
- **DETECTION_INTERVAL**: Detection interval in seconds (default: `0.1`)

#### ML Classification Configuration
- **MODEL_PATH**: Path to ML model file (default: `/app/models/threat_classifier.pkl`)

#### Alert Configuration
- **ALERT_THRESHOLD**: Threat score threshold for alerts 0.0-1.0 (default: `0.7`)

#### Dashboard Configuration
- **REACT_APP_API_URL**: API Gateway URL for frontend (default: `http://localhost:8000`)

## Setting Environment Variables

### Docker Compose (Development)

Create a `.env` file in the project root:

```bash
# Copy example file
cp .env.example .env

# Edit .env file with your values
nano .env  # or use your preferred editor
```

Example `.env` file:

```bash
# REQUIRED: Change these for production
JWT_SECRET=your_strong_random_secret_here_32_chars_minimum
POSTGRES_PASSWORD=your_strong_database_password_here

# Optional: Customize as needed
CONFIDENCE_THRESHOLD=0.6
ALERT_THRESHOLD=0.75
JWT_EXPIRATION=7200
```

Docker Compose will automatically load variables from `.env` file.

### Kubernetes (Production)

Use Kubernetes Secrets:

```bash
# Create secrets
kubectl create secret generic apds-secrets \
  --from-literal=jwt-secret=$(openssl rand -hex 32) \
  --from-literal=postgres-password=$(openssl rand -base64 24) \
  -n apds

# Reference in deployment YAML
env:
  - name: JWT_SECRET
    valueFrom:
      secretKeyRef:
        name: apds-secrets
        key: jwt-secret
  - name: POSTGRES_PASSWORD
    valueFrom:
      secretKeyRef:
        name: apds-secrets
        key: postgres-password
```

### Local Development

Set environment variables in your shell:

```bash
# Linux/Mac
export JWT_SECRET=your_secret_here
export POSTGRES_PASSWORD=your_password_here

# Windows PowerShell
$env:JWT_SECRET="your_secret_here"
$env:POSTGRES_PASSWORD="your_password_here"
```

## Security Best Practices

1. **Never commit secrets to Git**: Use `.env` file (already in `.gitignore`)
2. **Use strong random secrets**: Minimum 32 characters for JWT_SECRET
3. **Rotate secrets regularly**: Especially after security incidents
4. **Use different secrets per environment**: Dev, Staging, Production
5. **Limit secret access**: Use least privilege principle
6. **Monitor secret usage**: Log access to sensitive operations

## Environment-Specific Recommendations

### Development
- Use simple passwords for easy testing
- Enable debug logging
- Use shorter token expiration (e.g., 1 hour)

### Staging
- Use production-like secrets
- Enable audit logging
- Use standard token expiration

### Production
- Use strong, randomly generated secrets
- Enable all security features
- Use longer token expiration (e.g., 8 hours) with refresh tokens
- Enable rate limiting
- Use TLS/SSL for all connections
- Enable database encryption at rest

## Verification

After setting environment variables, verify they're loaded correctly:

```bash
# Check Docker Compose services
docker-compose config

# Check individual service environment
docker-compose exec auth-service env | grep JWT_SECRET

# Test authentication (should work with your JWT_SECRET)
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

## Troubleshooting

### Services can't connect to database
- Verify `POSTGRES_PASSWORD` matches in all services
- Check `POSTGRES_HOST` is correct (use service name in Docker Compose)
- Verify database is running: `docker-compose ps postgres`

### Authentication fails
- Verify `JWT_SECRET` is set and consistent across services
- Check token expiration: `JWT_EXPIRATION` might be too short
- Review auth service logs: `docker-compose logs auth-service`

### Services can't communicate
- Verify service URLs use correct service names (not localhost) in Docker Compose
- Check network connectivity: `docker-compose exec auth-service ping cv-detection-service`
- Review service logs for connection errors

