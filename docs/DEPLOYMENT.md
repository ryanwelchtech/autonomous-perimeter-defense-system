# APDS Deployment Guide

## Prerequisites

### Required Software
- Docker 20.10+
- Docker Compose 2.0+
- Python 3.11+ (for scripts)
- Git

### System Requirements
- **CPU**: 4+ cores recommended
- **RAM**: 8GB+ recommended (16GB for production)
- **Storage**: 20GB+ free space
- **Network**: Internet access for model downloads

## Quick Start (Docker Compose)

### 1. Clone Repository
```bash
git clone https://github.com/ryanwelchtech/autonomous-perimeter-defense-system.git
cd autonomous-perimeter-defense-system
```

### 2. Configure Environment
```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings
# Key variables:
# - JWT_SECRET: Strong random secret
# - POSTGRES_PASSWORD: Secure database password
```

### 3. Download Models (Optional)
```bash
# Download YOLOv8 model (optional, service will use mock mode if not available)
python scripts/setup_models.py
```

### 4. Start Services
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check service status
docker-compose ps
```

### 5. Verify Deployment
```bash
# Check API Gateway health
curl http://localhost:8000/health

# Check individual services
curl http://localhost:8001/health  # Auth
curl http://localhost:8002/health  # CV Detection
curl http://localhost:8003/health  # ML Classification
curl http://localhost:8004/health  # Alert Service
```

### 6. Access Dashboard
- Open http://localhost:3000
- Login with demo credentials:
  - Admin: `admin` / `admin123`
  - Operator: `operator` / `operator123`
  - Viewer: `viewer` / `viewer123`

## Production Deployment (Kubernetes)

### 1. Prerequisites
- Kubernetes cluster (1.24+)
- kubectl configured
- Helm 3.8+ (optional)

### 2. Create Namespace
```bash
kubectl create namespace apds
```

### 3. Create Secrets
```bash
# Create JWT secret
kubectl create secret generic apds-secrets \
  --from-literal=jwt-secret=$(openssl rand -hex 32) \
  --from-literal=postgres-password=$(openssl rand -hex 16) \
  -n apds
```

### 4. Deploy PostgreSQL
```bash
# Deploy PostgreSQL with persistent volume
kubectl apply -f deploy/k8s/postgres.yaml -n apds
```

### 5. Deploy Redis
```bash
kubectl apply -f deploy/k8s/redis.yaml -n apds
```

### 6. Deploy Services
```bash
# Deploy all microservices
kubectl apply -f deploy/k8s/services/ -n apds

# Wait for services to be ready
kubectl wait --for=condition=ready pod -l app=apds-auth -n apds --timeout=300s
```

### 7. Deploy API Gateway
```bash
kubectl apply -f deploy/k8s/api-gateway.yaml -n apds
```

### 8. Deploy Dashboard
```bash
kubectl apply -f deploy/k8s/dashboard.yaml -n apds
```

### 9. Configure Ingress
```bash
# Apply ingress configuration
kubectl apply -f deploy/k8s/ingress.yaml -n apds

# Get ingress IP
kubectl get ingress -n apds
```

## Environment Variables

### Auth Service
- `JWT_SECRET`: Secret key for JWT signing
- `JWT_ALGORITHM`: JWT algorithm (default: HS256)
- `JWT_EXPIRATION`: Token expiration in seconds (default: 3600)
- `REDIS_HOST`: Redis hostname
- `REDIS_PORT`: Redis port (default: 6379)

### CV Detection Service
- `REDIS_HOST`: Redis hostname
- `REDIS_PORT`: Redis port
- `AUTH_SERVICE_URL`: Auth service URL
- `MODEL_PATH`: Path to YOLOv8 model
- `CONFIDENCE_THRESHOLD`: Detection confidence threshold (0.0-1.0)
- `DETECTION_INTERVAL`: Detection interval in seconds

### ML Classification Service
- `REDIS_HOST`: Redis hostname
- `POSTGRES_HOST`: PostgreSQL hostname
- `POSTGRES_PORT`: PostgreSQL port (default: 5432)
- `POSTGRES_DB`: Database name (default: apds)
- `POSTGRES_USER`: Database user
- `POSTGRES_PASSWORD`: Database password
- `AUTH_SERVICE_URL`: Auth service URL
- `MODEL_PATH`: Path to ML model

### Alert Service
- `REDIS_HOST`: Redis hostname
- `POSTGRES_HOST`: PostgreSQL hostname
- `POSTGRES_PORT`: PostgreSQL port
- `POSTGRES_DB`: Database name
- `POSTGRES_USER`: Database user
- `POSTGRES_PASSWORD`: Database password
- `AUTH_SERVICE_URL`: Auth service URL
- `ALERT_THRESHOLD`: Threat score threshold for alerts (0.0-1.0)

### API Gateway
- `AUTH_SERVICE_URL`: Auth service URL
- `CV_DETECTION_SERVICE_URL`: CV service URL
- `ML_CLASSIFICATION_SERVICE_URL`: ML service URL
- `ALERT_SERVICE_URL`: Alert service URL
- `REDIS_HOST`: Redis hostname

## Database Initialization

### PostgreSQL Setup
```bash
# Initialize database schema
python scripts/init_db.py

# Or manually via psql
psql -h localhost -U apds_user -d apds -f scripts/schema.sql
```

## Health Checks

### Service Health Endpoints
All services expose `/health` endpoints:
- `GET /health` - Returns service health status

### Docker Health Checks
Docker Compose includes health checks for all services. Check status:
```bash
docker-compose ps
```

### Kubernetes Health Checks
Kubernetes deployments include:
- Liveness probes: `/health`
- Readiness probes: `/health`

Check pod health:
```bash
kubectl get pods -n apds
kubectl describe pod <pod-name> -n apds
```

## Scaling

### Horizontal Scaling (Kubernetes)
```bash
# Scale CV detection service
kubectl scale deployment apds-cv-detection --replicas=3 -n apds

# Scale ML classification service
kubectl scale deployment apds-ml-classification --replicas=2 -n apds
```

### Resource Limits
Configure in `deploy/k8s/services/*.yaml`:
```yaml
resources:
  requests:
    memory: "512Mi"
    cpu: "500m"
  limits:
    memory: "2Gi"
    cpu: "2000m"
```

## Monitoring

### Logs
```bash
# Docker Compose
docker-compose logs -f <service-name>

# Kubernetes
kubectl logs -f deployment/<service-name> -n apds
```

### Metrics (Future)
- Prometheus endpoints: `/metrics` (to be implemented)
- Grafana dashboards (to be created)

## Troubleshooting

### Services Not Starting
1. Check Docker logs: `docker-compose logs <service>`
2. Verify environment variables
3. Check port conflicts: `netstat -tulpn | grep <port>`
4. Verify dependencies (Redis, PostgreSQL)

### Database Connection Issues
1. Verify PostgreSQL is running: `docker-compose ps postgres`
2. Check connection string in environment variables
3. Verify database exists: `docker-compose exec postgres psql -U apds_user -d apds -c "\dt"`

### Authentication Failures
1. Verify JWT_SECRET is set
2. Check Auth Service logs
3. Verify Redis connectivity
4. Check token expiration

### CV Detection Not Working
1. Verify YOLOv8 model is downloaded
2. Check model path in environment variables
3. Review CV service logs for errors
4. Service will use mock mode if model unavailable

## Backup and Recovery

### PostgreSQL Backup
```bash
# Backup database
docker-compose exec postgres pg_dump -U apds_user apds > backup.sql

# Restore database
docker-compose exec -T postgres psql -U apds_user apds < backup.sql
```

### Kubernetes Backup
```bash
# Backup PostgreSQL PVC
kubectl exec -n apds <postgres-pod> -- pg_dump -U apds_user apds > backup.sql
```

## Security Hardening

### Production Checklist
- [ ] Change all default passwords
- [ ] Use strong JWT_SECRET (32+ characters)
- [ ] Enable TLS/SSL for all services
- [ ] Configure firewall rules
- [ ] Enable audit logging
- [ ] Regular security updates
- [ ] Container image scanning
- [ ] Network policies (Kubernetes)

## Rollback

### Docker Compose
```bash
# Stop services
docker-compose down

# Restore previous version
git checkout <previous-commit>
docker-compose up -d
```

### Kubernetes
```bash
# Rollback deployment
kubectl rollout undo deployment/<service-name> -n apds

# Check rollout history
kubectl rollout history deployment/<service-name> -n apds
```

## Support

For issues and questions:
- GitHub Issues: https://github.com/ryanwelchtech/autonomous-perimeter-defense-system/issues
- Documentation: See `docs/` directory

