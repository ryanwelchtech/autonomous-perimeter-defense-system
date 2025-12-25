# APDS Architecture Documentation

## System Overview

The Autonomous Perimeter Defense System (APDS) is a microservices-based platform designed for real-time threat detection and classification using Computer Vision and Machine Learning.

## Architecture Principles

1. **Zero Trust**: Every service interaction requires authentication
2. **Microservices**: Loosely coupled, independently deployable services
3. **Event-Driven**: Asynchronous processing via message queues
4. **Resilient**: Health checks, graceful degradation, fail-safe operation
5. **Observable**: Comprehensive logging, metrics, and monitoring

## Component Architecture

### 1. Authentication Service

**Purpose**: Zero Trust JWT-based authentication and authorization

**Responsibilities**:
- User authentication (username/password)
- JWT token generation and validation
- Service account token management
- Token revocation
- Role-based access control (RBAC)

**Technology Stack**:
- FastAPI
- PyJWT
- Redis (token storage)

**Endpoints**:
- `POST /login` - User authentication
- `POST /service-token` - Service account token generation
- `POST /validate` - Token validation
- `POST /revoke` - Token revocation
- `GET /permissions` - Get user permissions

### 2. Computer Vision Detection Service

**Purpose**: Real-time object detection using YOLOv8

**Responsibilities**:
- Image processing and object detection
- Person and vehicle detection
- Threat level assessment (low, medium, high, critical)
- Detection statistics tracking
- Queue detection results for ML processing

**Technology Stack**:
- FastAPI
- Ultralytics YOLOv8
- OpenCV
- Redis (message queue)

**Endpoints**:
- `POST /detect` - Process image and detect objects
- `GET /stats` - Get detection statistics

**Performance**:
- Detection latency: <100ms
- Throughput: 200+ detections/minute
- Confidence threshold: 0.5 (configurable)

### 3. ML Classification Service

**Purpose**: Threat classification with explainable AI

**Responsibilities**:
- Feature extraction from detections
- ML-based threat scoring
- Rule-based fallback classification
- Threat category assignment
- Database persistence

**Technology Stack**:
- FastAPI
- scikit-learn (ML models)
- PostgreSQL
- Redis (message queue)

**Endpoints**:
- `POST /classify` - Classify threat from detection
- `GET /stats` - Get classification statistics
- `GET /classifications/{detection_id}` - Get classification by ID

**Threat Categories**:
- `benign`: Low threat score (<0.4)
- `suspicious`: Moderate threat (0.4-0.6)
- `high_threat`: High threat (0.6-0.8)
- `critical`: Critical threat (>0.8)

### 4. Alert Service

**Purpose**: Alert generation and management

**Responsibilities**:
- Process high-threat classifications
- Generate alerts
- Alert acknowledgment workflow
- Alert statistics
- Real-time alert distribution

**Technology Stack**:
- FastAPI
- PostgreSQL
- Redis (alert queue)

**Endpoints**:
- `GET /alerts` - Get alerts (with filters)
- `GET /alerts/{alert_id}` - Get specific alert
- `POST /alerts/{alert_id}/acknowledge` - Acknowledge alert
- `GET /stats` - Get alert statistics
- `GET /alerts/recent` - Get recent alerts from Redis

### 5. API Gateway

**Purpose**: Single entry point with Zero Trust routing

**Responsibilities**:
- Request routing to backend services
- Authentication verification
- Service token management
- CORS handling
- Health check aggregation

**Technology Stack**:
- FastAPI
- HTTP client (requests)
- Redis (caching)

**Endpoints**:
- `POST /auth/login` - Proxy to auth service
- `POST /cv/detect` - Proxy to CV service
- `GET /cv/stats` - Proxy to CV stats
- `GET /ml/stats` - Proxy to ML stats
- `GET /alerts` - Proxy to alert service
- `GET /health` - Aggregated health check

### 6. Dashboard Frontend

**Purpose**: Real-time threat monitoring interface

**Responsibilities**:
- User authentication UI
- Real-time statistics display
- Alert management interface
- System health visualization

**Technology Stack**:
- React
- Axios (HTTP client)
- CSS3

**Features**:
- Real-time data refresh (5-second intervals)
- Alert acknowledgment
- Statistics visualization
- Responsive design

## Data Flow

### Detection Pipeline

```
1. Image → CV Detection Service
   ↓
2. Object Detection (YOLOv8)
   ↓
3. Detection Results → Redis Queue
   ↓
4. ML Classification Service (async)
   ↓
5. Threat Classification
   ↓
6. High Threat? → Alert Service
   ↓
7. Alert Generation → Dashboard
```

### Authentication Flow

```
1. User Login → Auth Service
   ↓
2. JWT Token Generation
   ↓
3. Token Storage (Redis)
   ↓
4. API Gateway Validation
   ↓
5. Service Token Request
   ↓
6. Backend Service Access
```

## Zero Trust Implementation

### Service-to-Service Authentication

1. Each service requests a service account token from Auth Service
2. Token includes service name, role, and permissions
3. Services validate tokens before inter-service communication
4. Tokens expire after configured TTL (default: 3600s)

### User Authentication

1. User provides credentials to API Gateway
2. Gateway proxies to Auth Service
3. Auth Service validates and generates JWT
4. Token stored in Redis for revocation checking
5. Token included in subsequent requests

### Role-Based Access Control

**Roles**:
- `admin`: Full access (read, write, delete, manage)
- `operator`: Read and write access
- `viewer`: Read-only access
- `service`: Service-to-service communication

## Data Storage

### PostgreSQL

**Tables**:
- `threat_classifications`: ML classification results
- `alerts`: Alert records with acknowledgment status

**Indexes**:
- Detection ID (unique)
- Timestamp (for time-based queries)
- Threat score (for filtering)
- Acknowledged status

### Redis

**Usage**:
- Token storage and revocation
- Message queues (detections, alerts)
- Caching (recent alerts, stats)
- Real-time data distribution

## Security Considerations

### Container Security
- Multi-stage builds
- Minimal base images
- No root user execution
- Security scanning (Trivy)

### Network Security
- Service mesh isolation
- Internal service communication only
- API Gateway as single entry point
- CORS configuration

### Data Security
- JWT token encryption
- Token expiration and revocation
- Audit logging
- Tamper-evident storage

## Scalability

### Horizontal Scaling
- Stateless services enable horizontal scaling
- Redis and PostgreSQL support clustering
- Load balancer in front of API Gateway

### Performance Optimization
- Redis caching for frequently accessed data
- Async processing for ML classification
- Connection pooling for database
- Efficient image processing

## Observability

### Health Checks
- Each service exposes `/health` endpoint
- Docker health checks configured
- Kubernetes liveness/readiness probes

### Logging
- Structured logging (JSON format)
- Service-level log aggregation
- Audit logs for security events

### Metrics (Future)
- Prometheus metrics endpoints
- Grafana dashboards
- Alert thresholds and SLOs

## Deployment Architecture

### Development
- Docker Compose for local development
- Single-node deployment
- Development-friendly defaults

### Production
- Kubernetes deployment
- Multi-replica services
- Persistent volumes for PostgreSQL
- Ingress for external access
- ConfigMaps and Secrets management

## Compliance

### NIST 800-53 Controls
- **AC**: Access Control (JWT, RBAC)
- **AU**: Audit and Accountability (logging)
- **IA**: Identification and Authentication (JWT tokens)
- **SC**: System and Communications Protection (encryption)
- **SI**: System and Information Integrity (monitoring)

### FedRAMP High Alignment
- Zero Trust architecture
- Comprehensive audit logging
- Security scanning and compliance

## Future Enhancements

1. **Observability Stack**: Prometheus, Grafana, ELK
2. **Service Mesh**: Istio or Linkerd integration
3. **Advanced ML**: Custom trained models, model versioning
4. **Multi-Camera**: Support for multiple camera feeds
5. **WebSocket**: Real-time updates to dashboard
6. **Mobile App**: Alert notifications and monitoring

