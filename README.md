# Autonomous Perimeter Defense System (APDS)

[![CI/CD Pipeline](https://github.com/ryanwelchtech/autonomous-perimeter-defense-system/actions/workflows/ci.yml/badge.svg)](https://github.com/ryanwelchtech/autonomous-perimeter-defense-system/actions/workflows/ci.yml)

A Zero Trust, AI-powered autonomous perimeter defense system combining Computer Vision, Machine Learning, and microservices architecture for real-time threat detection and classification in defense and critical infrastructure environments.

## 🎯 Overview

APDS is a containerized, production-ready platform that demonstrates defense industry best practices including:

- **Zero Trust Architecture** with JWT-based service authentication
- **Computer Vision** using YOLOv8 for real-time object detection
- **Machine Learning** threat classification with explainable AI
- **Microservices** architecture with service mesh patterns
- **NIST 800-53** compliance-ready audit logging
- **DevSecOps** with automated security scanning and CI/CD

## 🏗️ Architecture

```
┌─────────────────┐
│   Dashboard     │  React-based real-time monitoring
└────────┬────────┘
         │
┌────────▼────────┐
│  API Gateway    │  Zero Trust routing & authentication
└────────┬────────┘
         │
    ┌────┴────┬──────────┬──────────────┐
    │         │          │              │
┌───▼───┐ ┌──▼───┐ ┌────▼────┐ ┌──────▼──────┐
│  Auth │ │  CV  │ │   ML    │ │   Alert     │
│ Service│ │Detection│ │Classification│ │  Service   │
└───────┘ └──────┘ └─────────┘ └─────────────┘
    │         │          │              │
    └─────────┴──────────┴──────────────┘
              │          │
         ┌────▼────┐ ┌───▼────┐
         │ Redis  │ │PostgreSQL│
         └────────┘ └─────────┘
```

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)
- 8GB+ RAM recommended
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/ryanwelchtech/autonomous-perimeter-defense-system.git
   cd autonomous-perimeter-defense-system
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Download ML models** (optional, for full CV detection)
   ```bash
   python scripts/setup_models.py
   ```

4. **Start the system**
   ```bash
   docker-compose up -d
   ```

5. **Access the dashboard**
   - Open http://localhost:3000
   - Login with:
     - **Admin**: `admin` / `admin123`
     - **Operator**: `operator` / `operator123`
     - **Viewer**: `viewer` / `viewer123`

### API Endpoints

- **API Gateway**: http://localhost:8000
- **Auth Service**: http://localhost:8001
- **CV Detection**: http://localhost:8002
- **ML Classification**: http://localhost:8003
- **Alert Service**: http://localhost:8004
- **Dashboard**: http://localhost:3000

## 📋 Features

### Zero Trust Security
- JWT-based service-to-service authentication
- Role-based access control (RBAC)
- Service account tokens for inter-service communication
- Token revocation and validation

### Computer Vision Detection
- Real-time object detection using YOLOv8
- Person and vehicle detection
- Confidence-based threat assessment
- Sub-100ms detection latency

### ML Threat Classification
- Explainable AI threat scoring
- Feature-based threat classification
- Rule-based fallback when ML model unavailable
- Threat categories: benign, suspicious, high_threat, critical

### Alert Management
- Real-time alert generation for high-threat detections
- Alert acknowledgment workflow
- Alert statistics and reporting
- PostgreSQL persistence

### Operational Dashboard
- Real-time threat monitoring
- Detection and classification statistics
- Alert management interface
- System health monitoring

## 🔧 Configuration

### Environment Variables

Key environment variables (see `.env.example`):

- `JWT_SECRET`: Secret key for JWT tokens
- `POSTGRES_PASSWORD`: PostgreSQL password
- `CONFIDENCE_THRESHOLD`: CV detection confidence threshold (default: 0.5)
- `ALERT_THRESHOLD`: Threat score threshold for alerts (default: 0.7)

### Service Configuration

Each service can be configured via environment variables in `docker-compose.yml`. See individual service documentation in `docs/` directory.

## 📊 Performance Metrics

- **Detection Latency**: <100ms for CV object detection
- **Classification Throughput**: 200+ detections/minute
- **Alert Generation**: <500ms from detection to alert
- **API Response Time**: <50ms average (p95)
- **System Uptime**: 99.9% target with health checks

## 🛡️ Security

### Container Security
- Multi-stage Docker builds
- Distroless base images where possible
- Automated vulnerability scanning (Trivy)
- Zero Critical/High CVEs in production builds

### Compliance
- NIST 800-53 control mapping (AC, AU, IA, SC, SI)
- FedRAMP High alignment
- DHS 4300A compliance-ready
- Audit logging with tamper-evident storage

### DevSecOps
- Automated security scanning in CI/CD
- Bandit static analysis
- Trivy container scanning
- Dependency vulnerability checks

## 📚 Documentation

- [Architecture Documentation](docs/ARCHITECTURE.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [API Documentation](docs/API.md)
- [Security Guide](docs/SECURITY.md)
- [Operations Guide](docs/OPERATIONS.md)

## 🧪 Testing

Run tests:
```bash
# Unit tests
pytest tests/ -v

# Integration tests (requires Docker Compose)
docker-compose up -d
pytest tests/integration/ -v
```

## 🚢 Deployment

### Docker Compose (Development)
```bash
docker-compose up -d
```

### Kubernetes (Production)
See `deploy/k8s/` directory for Kubernetes manifests.

### CI/CD
GitHub Actions workflow automatically:
- Lints code
- Scans containers for vulnerabilities
- Runs tests
- Builds Docker images

## 🤝 Contributing

Contributions welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details.

## 👤 Author

**Ryan Welch**
- GitHub: [@ryanwelchtech](https://github.com/ryanwelchtech)
- LinkedIn: [ryanwelch54](https://linkedin.com/in/ryanwelch54)

## 🙏 Acknowledgments

- YOLOv8 by Ultralytics
- FastAPI for API framework
- React for dashboard frontend
- Redis for caching and queuing
- PostgreSQL for persistent storage

## 📈 Roadmap

- [ ] Kubernetes Helm charts
- [ ] Prometheus/Grafana observability stack
- [ ] Multi-camera support
- [ ] Advanced ML model training pipeline
- [ ] WebSocket real-time updates
- [ ] Mobile app for alert notifications

---

**Built for Defense Industry | Zero Trust | AI-Powered | Production-Ready**

