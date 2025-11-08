# Color Transfer Framework v2.0 - Deployment Guide

Complete guide for deploying the Color Transfer Framework in various environments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development](#local-development)
3. [Docker Deployment](#docker-deployment)
4. [Production Deployment](#production-deployment)
5. [Cloud Deployment](#cloud-deployment)
6. [Monitoring & Operations](#monitoring--operations)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements

- **CPU**: 2+ cores recommended
- **Memory**: 4GB minimum, 8GB recommended
- **Storage**: 10GB minimum
- **OS**: Linux, macOS, or Windows with WSL2

### Software Requirements

- Python 3.9+ (3.11 recommended)
- Docker 20.10+ and Docker Compose 2.0+ (for containerized deployment)
- Git
- Make (optional, for convenience commands)

---

## Local Development

### Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/mgdavisxvs/ColorTransfer.git
cd ColorTransfer

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Setup environment
cp .env.example .env

# 5. Run the application
# Option A: FastAPI (Recommended)
uvicorn color_transfer_framework.interface_layer.api:app --reload --port 8000

# Option B: Flask Web UI
python -m color_transfer_framework.interface_layer.web

# Option C: CLI
python -m color_transfer_framework.interface_layer.cli --help
```

### Using Makefile (Recommended)

```bash
# Setup development environment
make setup-dev

# Run tests
make test-quick

# Start with Docker
make docker-up

# Check health
make check-health
```

---

## Docker Deployment

### Build Docker Images

```bash
# Build API image
docker build -t color-transfer:api --build-arg INTERFACE=api .

# Build Web UI image
docker build -t color-transfer:web --build-arg INTERFACE=web .

# Build all images
make docker-build-all
```

### Run with Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Cleanup (including volumes)
docker-compose down -v
```

### Available Services

| Service | Port | Description |
|---------|------|-------------|
| API | 8000 | FastAPI REST API |
| Web | 5000 | Flask Web UI |
| Web Enhanced | 5001 | Enhanced Flask Web UI |
| Redis | 6379 | Cache & Message Broker |
| Celery Worker | - | Async Task Processing |

### Environment Variables

Key environment variables (see `.env.example` for complete list):

```bash
# Application
INTERFACE=api                    # api, web, web_enhanced, tui, cli
WORKERS=4                        # Number of worker processes
TIMEOUT=60                       # Request timeout (seconds)

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# Celery
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

# Security
ALLOWED_ORIGINS=*               # CORS origins (comma-separated)
API_KEY_REQUIRED=false          # Enable API key authentication
```

---

## Production Deployment

### Production Checklist

- [ ] Use specific Docker image tags (not `latest`)
- [ ] Configure resource limits (CPU, memory)
- [ ] Enable HTTPS/TLS
- [ ] Set up monitoring and logging
- [ ] Configure backups
- [ ] Review security settings
- [ ] Set up health checks
- [ ] Configure secrets management
- [ ] Enable rate limiting
- [ ] Set up CI/CD pipeline

### Docker Production Configuration

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  api:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3

    environment:
      - WORKERS=8
      - LOG_LEVEL=warning
      - ENABLE_METRICS=true
      - RATE_LIMIT_PER_MINUTE=100

    healthcheck:
      interval: 15s
      timeout: 5s
      retries: 3
      start_period: 30s
```

Deploy with:

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Nginx Reverse Proxy

Example Nginx configuration:

```nginx
upstream color_transfer_api {
    server localhost:8000;
}

server {
    listen 80;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://color_transfer_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Increase timeout for long-running transfers
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;

        # File upload size limit
        client_max_body_size 10M;
    }

    location /health {
        proxy_pass http://color_transfer_api/health/live;
        access_log off;
    }
}
```

---

## Cloud Deployment

### AWS ECS (Elastic Container Service)

```bash
# 1. Build and tag image
docker build -t color-transfer:api .
docker tag color-transfer:api 123456789.dkr.ecr.us-east-1.amazonaws.com/color-transfer:latest

# 2. Push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 123456789.dkr.ecr.us-east-1.amazonaws.com
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/color-transfer:latest

# 3. Create ECS task definition and service (use AWS Console or CLI)
```

### Google Cloud Run

```bash
# 1. Build and push image
gcloud builds submit --tag gcr.io/PROJECT-ID/color-transfer:api

# 2. Deploy to Cloud Run
gcloud run deploy color-transfer-api \
  --image gcr.io/PROJECT-ID/color-transfer:api \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --max-instances 10 \
  --set-env-vars INTERFACE=api,WORKERS=4
```

### Azure Container Apps

```bash
# 1. Build and push image
az acr build --registry myregistry --image color-transfer:api .

# 2. Create container app
az containerapp create \
  --name color-transfer-api \
  --resource-group myResourceGroup \
  --environment myEnvironment \
  --image myregistry.azurecr.io/color-transfer:api \
  --target-port 8000 \
  --ingress external \
  --cpu 2 \
  --memory 4Gi \
  --env-vars INTERFACE=api WORKERS=4
```

### Kubernetes (K8s) - Basic Example

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: color-transfer-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: color-transfer-api
  template:
    metadata:
      labels:
        app: color-transfer-api
    spec:
      containers:
      - name: api
        image: color-transfer:api
        ports:
        - containerPort: 8000
        env:
        - name: INTERFACE
          value: "api"
        - name: WORKERS
          value: "4"
        resources:
          requests:
            memory: "1Gi"
            cpu: "1"
          limits:
            memory: "2Gi"
            cpu: "2"
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: color-transfer-api
spec:
  selector:
    app: color-transfer-api
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

Deploy:

```bash
kubectl apply -f deployment.yaml
kubectl get pods
kubectl get services
```

---

## Monitoring & Operations

### Health Checks

```bash
# Liveness (is the service alive?)
curl http://localhost:8000/health/live

# Readiness (is the service ready to accept traffic?)
curl http://localhost:8000/health/ready

# Full health check
curl http://localhost:8000/health/full
```

### Metrics

```bash
# Prometheus metrics
curl http://localhost:8000/metrics

# JSON metrics
curl http://localhost:8000/api/v1/metrics
```

### Logs

```bash
# Docker logs
docker-compose logs -f api
docker-compose logs --tail=100 api

# Live logs (if using file logging)
tail -f logs/color_transfer.log

# Filter errors only
docker-compose logs api | grep ERROR
```

### Performance Monitoring

```bash
# Resource usage
docker stats

# API performance
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/

# Load testing
make test-load

# Or with Locust directly
locust -f tests/load/locustfile.py --headless -u 50 -r 10 -t 2m --host http://localhost:8000
```

---

## Troubleshooting

### Common Issues

#### Port Already in Use

```bash
# Find process using port 8000
lsof -i :8000
# or
netstat -tuln | grep 8000

# Kill process
kill -9 <PID>
```

#### Container Won't Start

```bash
# Check logs
docker-compose logs api

# Check container status
docker-compose ps

# Inspect container
docker inspect <container_id>

# Enter container for debugging
docker-compose exec api bash
```

#### Redis Connection Issues

```bash
# Check Redis is running
docker-compose ps redis

# Test Redis connection
docker-compose exec redis redis-cli ping

# Check Redis logs
docker-compose logs redis
```

#### Memory Issues

```bash
# Check container memory
docker stats

# Increase Docker memory limit (Docker Desktop)
# Settings -> Resources -> Memory

# Reduce workers
export WORKERS=2
docker-compose up -d
```

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=debug
docker-compose up

# Or in .env file
LOG_LEVEL=debug
```

### Performance Issues

```bash
# Check resource usage
docker stats

# Profile application
python -m cProfile -o profile.stats your_script.py

# Analyze profile
python -m pstats profile.stats

# Monitor with htop
htop
```

---

## Scaling

### Horizontal Scaling

```bash
# Scale Celery workers
docker-compose up -d --scale celery_worker=4

# Scale API instances (with load balancer)
docker-compose up -d --scale api=3
```

### Vertical Scaling

Update resource limits in `docker-compose.yml`:

```yaml
deploy:
  resources:
    limits:
      cpus: '4.0'
      memory: 4G
```

---

## Backup & Recovery

### Backup Data

```bash
# Backup Redis data
docker-compose exec redis redis-cli BGSAVE
docker cp color-transfer-redis:/data/dump.rdb ./backup/redis-$(date +%Y%m%d).rdb

# Backup application data
tar -czf backup-$(date +%Y%m%d).tar.gz data/ logs/
```

### Restore Data

```bash
# Restore Redis
docker cp ./backup/redis-20240101.rdb color-transfer-redis:/data/dump.rdb
docker-compose restart redis

# Restore application data
tar -xzf backup-20240101.tar.gz
```

---

## Security Best Practices

1. **Never commit secrets** - Use environment variables or secrets management
2. **Use HTTPS** - Always use TLS in production
3. **Enable authentication** - Set `API_KEY_REQUIRED=true`
4. **Rate limiting** - Configure appropriate limits
5. **Update regularly** - Keep dependencies and base images updated
6. **Scan for vulnerabilities** - Use `make security-scan`
7. **Least privilege** - Run containers as non-root user (already configured)
8. **Network isolation** - Use Docker networks
9. **Monitor logs** - Set up centralized logging
10. **Regular backups** - Automate backup procedures

---

## Additional Resources

- [GitHub Repository](https://github.com/mgdavisxvs/ColorTransfer)
- [API Documentation](./INTERFACE_README.md)
- [Architecture Overview](./ARCHITECTURE.md)
- [Operations Guide](./OPERATIONS.md)
- [Testing Guide](./tests/TESTING_GUIDE.md)

---

## Support

For issues or questions:
1. Check this documentation
2. Review GitHub Issues
3. Check application logs
4. Enable debug mode for detailed information

---

**Knuth's Deployment Philosophy**: "Premature optimization is the root of all evil. Get it working, then make it fast."

**Graham's Practical Approach**: "Deploy early, deploy often, and monitor everything."

---

*Color Transfer Framework v2.0 - Production-Ready Deployment*
