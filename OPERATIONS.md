# Color Transfer Framework v2.0 - Operations Guide

Production operations, monitoring, and maintenance guide.

## Table of Contents

1. [Operations Overview](#operations-overview)
2. [Monitoring](#monitoring)
3. [Logging](#logging)
4. [Performance Tuning](#performance-tuning)
5. [Incident Response](#incident-response)
6. [Maintenance](#maintenance)
7. [Runbooks](#runbooks)

---

## Operations Overview

### Service Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Load Balancer                        │
└─────────────────────────────────────────────────────────┘
                            │
                ┌───────────┴───────────┐
                │                       │
┌───────────────▼─────┐    ┌───────────▼─────────────┐
│   API Service (x3)   │    │   Web UI Service (x2)   │
└───────────────┬─────┘    └───────────┬─────────────┘
                │                       │
                └───────────┬───────────┘
                            │
                ┌───────────▼───────────┐
                │   Redis (Cache/Queue) │
                └───────────┬───────────┘
                            │
                ┌───────────▼───────────┐
                │   Celery Workers (x4) │
                └───────────────────────┘
```

### Key Metrics

| Metric | Target | Warning | Critical |
|--------|--------|---------|----------|
| API Response Time (p95) | < 500ms | > 1s | > 2s |
| Error Rate | < 0.1% | > 1% | > 5% |
| CPU Usage | < 70% | > 80% | > 90% |
| Memory Usage | < 75% | > 85% | > 95% |
| Redis Memory | < 400MB | > 450MB | > 500MB |
| Queue Length | < 100 | > 500 | > 1000 |

---

## Monitoring

### Health Check Endpoints

```bash
# Liveness - Is the service alive?
curl http://localhost:8000/health/live
# Response: {"status": "healthy"}

# Readiness - Is the service ready to handle traffic?
curl http://localhost:8000/health/ready
# Response: {"status": "ready", "checks": {...}}

# Full health check
curl http://localhost:8000/health/full
# Response: Detailed status of all components
```

### Prometheus Metrics

The framework exposes Prometheus-compatible metrics at `/metrics`:

```bash
curl http://localhost:8000/metrics
```

**Key Metrics Exposed:**

```
# Request metrics
http_requests_total
http_request_duration_seconds

# Application metrics
color_transfer_operations_total
color_transfer_operation_duration_seconds
color_transfer_errors_total

# System metrics
process_cpu_seconds_total
process_resident_memory_bytes
process_open_fds

# Cache metrics
redis_cache_hits_total
redis_cache_misses_total
redis_connections_active
```

### Grafana Dashboards

**Recommended Dashboard Panels:**

1. **Request Rate**
   - Query: `rate(http_requests_total[5m])`
   - Type: Graph

2. **Response Time (p95)**
   - Query: `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))`
   - Type: Graph

3. **Error Rate**
   - Query: `rate(http_requests_total{status=~"5.."}[5m])`
   - Type: Graph

4. **CPU Usage**
   - Query: `rate(process_cpu_seconds_total[5m]) * 100`
   - Type: Gauge

5. **Memory Usage**
   - Query: `process_resident_memory_bytes`
   - Type: Gauge

### Alerting Rules

**Example Prometheus Alert Rules:**

```yaml
groups:
  - name: color_transfer_alerts
    rules:
      # High Error Rate
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} (> 5%)"

      # Slow Response Time
      - alert: SlowResponseTime
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Slow response time detected"
          description: "P95 response time is {{ $value }}s (> 2s)"

      # High Memory Usage
      - alert: HighMemoryUsage
        expr: (process_resident_memory_bytes / 1024 / 1024 / 1024) > 1.8
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage"
          description: "Memory usage is {{ $value }}GB (> 1.8GB)"

      # Service Down
      - alert: ServiceDown
        expr: up{job="color-transfer-api"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Service is down"
          description: "{{ $labels.instance }} is down"

      # High Queue Length
      - alert: HighQueueLength
        expr: celery_queue_length > 1000
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High queue length"
          description: "Queue length is {{ $value }} (> 1000)"
```

---

## Logging

### Log Levels

| Level | Usage | Example |
|-------|-------|---------|
| DEBUG | Development only | Variable values, detailed flow |
| INFO | Normal operations | Request received, operation completed |
| WARNING | Potential issues | High latency, approaching limits |
| ERROR | Operation failures | Failed to process image, database error |
| CRITICAL | System failures | Service crashed, data corruption |

### Log Format

**Structured JSON logging (recommended):**

```json
{
  "timestamp": "2025-11-08T13:00:00Z",
  "level": "INFO",
  "service": "color-transfer-api",
  "instance": "api-01",
  "message": "Color transfer completed",
  "context": {
    "algorithm": "reinhard_lab",
    "duration_ms": 145,
    "source_size": [1920, 1080],
    "target_size": [1920, 1080]
  },
  "trace_id": "abc123"
}
```

### Log Aggregation

**With Docker:**

```bash
# View all logs
docker-compose logs -f

# Filter by service
docker-compose logs -f api

# Filter by level
docker-compose logs api | grep ERROR

# Last 100 lines
docker-compose logs --tail=100 api
```

**Centralized Logging (ELK Stack):**

```yaml
# docker-compose.logging.yml
version: '3.8'

services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    ports:
      - "9200:9200"

  logstash:
    image: docker.elastic.co/logstash/logstash:8.11.0
    volumes:
      - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf

  kibana:
    image: docker.elastic.co/kibana/kibana:8.11.0
    ports:
      - "5601:5601"
    depends_on:
      - elasticsearch
```

---

## Performance Tuning

### Worker Configuration

**Optimal workers calculation:**

```
workers = (2 × CPU cores) + 1
```

Example configurations:

| CPU Cores | Recommended Workers | Max Memory |
|-----------|---------------------|------------|
| 2 | 5 | 2GB |
| 4 | 9 | 4GB |
| 8 | 17 | 8GB |

**Set in environment:**

```bash
export WORKERS=9
docker-compose up -d
```

### Redis Optimization

```bash
# Connect to Redis
docker-compose exec redis redis-cli

# Check memory usage
INFO memory

# Check hit rate
INFO stats

# Eviction policy (already configured in docker-compose.yml)
CONFIG SET maxmemory-policy allkeys-lru

# Persistence (if needed)
CONFIG SET save "900 1 300 10 60 10000"
```

### Celery Optimization

```yaml
# In docker-compose.yml
celery_worker:
  command: >
    celery -A color_transfer_framework.performance.distributed_processing worker
    --loglevel=info
    --concurrency=4              # Number of concurrent workers
    --max-tasks-per-child=100    # Recycle workers (prevent memory leaks)
    --pool=prefork               # Use prefork pool (CPU-bound tasks)
    --time-limit=300             # Hard time limit per task
    --soft-time-limit=240        # Soft time limit per task
```

### Database Connection Pooling

If using a database:

```python
# Example for SQLAlchemy
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,           # Number of connections to keep
    max_overflow=20,        # Max connections beyond pool_size
    pool_timeout=30,        # Timeout for getting connection
    pool_recycle=3600       # Recycle connections after 1 hour
)
```

---

## Incident Response

### Incident Severity Levels

| Severity | Response Time | Examples |
|----------|---------------|----------|
| P0 - Critical | < 15 minutes | Service down, data loss |
| P1 - High | < 1 hour | High error rate, major feature broken |
| P2 - Medium | < 4 hours | Performance degradation, minor feature issues |
| P3 - Low | < 1 day | Cosmetic issues, enhancement requests |

### Incident Response Checklist

**When an incident occurs:**

1. **Acknowledge**: Confirm incident and notify team
2. **Assess**: Determine severity and impact
3. **Mitigate**: Take immediate action to reduce impact
4. **Investigate**: Identify root cause
5. **Resolve**: Fix the underlying issue
6. **Document**: Write post-mortem
7. **Follow-up**: Implement preventive measures

### Common Issues & Solutions

#### High CPU Usage

**Symptoms:**
- Slow response times
- High system load
- Container throttling

**Diagnosis:**
```bash
# Check CPU usage
docker stats

# Check top processes
docker-compose exec api top

# Profile application
docker-compose exec api python -m cProfile
```

**Solutions:**
- Scale horizontally (add more instances)
- Optimize algorithms
- Enable caching
- Reduce concurrent requests

#### High Memory Usage

**Symptoms:**
- OOM (Out of Memory) errors
- Container restarts
- Slow garbage collection

**Diagnosis:**
```bash
# Check memory
docker stats

# Memory profiler
pip install memory-profiler
python -m memory_profiler your_script.py
```

**Solutions:**
- Increase container memory limits
- Reduce worker count
- Implement pagination
- Clear caches regularly
- Fix memory leaks

#### Redis Connection Issues

**Symptoms:**
- Connection timeouts
- Cache miss rate increase
- Slow response times

**Diagnosis:**
```bash
# Check Redis status
docker-compose exec redis redis-cli PING

# Check connections
docker-compose exec redis redis-cli INFO clients

# Check memory
docker-compose exec redis redis-cli INFO memory
```

**Solutions:**
- Restart Redis: `docker-compose restart redis`
- Check network connectivity
- Increase connection pool size
- Check Redis memory limits

#### Queue Buildup

**Symptoms:**
- Increasing queue length
- Delayed processing
- Worker saturation

**Diagnosis:**
```bash
# Check queue length
docker-compose exec redis redis-cli LLEN celery

# Check worker status
docker-compose exec celery_worker celery -A app inspect active
```

**Solutions:**
- Scale workers: `docker-compose up -d --scale celery_worker=8`
- Increase worker concurrency
- Optimize task execution time
- Implement task prioritization

---

## Maintenance

### Regular Maintenance Tasks

**Daily:**
- [ ] Check error logs
- [ ] Review metrics dashboards
- [ ] Verify backup completion

**Weekly:**
- [ ] Review performance trends
- [ ] Check disk space usage
- [ ] Update security patches
- [ ] Review and rotate logs

**Monthly:**
- [ ] Review and update dependencies
- [ ] Capacity planning review
- [ ] Security audit
- [ ] Test backup restoration
- [ ] Review and update documentation

### Dependency Updates

```bash
# Check outdated packages
pip list --outdated

# Update specific package
pip install --upgrade package-name

# Update all packages (use with caution)
pip install --upgrade -r requirements.txt

# Test after updates
make test-full
```

### Log Rotation

```bash
# Configure logrotate
cat > /etc/logrotate.d/color-transfer <<EOF
/app/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 appuser appuser
    sharedscripts
    postrotate
        docker-compose exec api kill -USR1 1
    endscript
}
EOF
```

### Database Maintenance

```bash
# Vacuum (if using PostgreSQL)
docker-compose exec db psql -U user -d dbname -c "VACUUM ANALYZE;"

# Backup
docker-compose exec db pg_dump -U user dbname > backup-$(date +%Y%m%d).sql

# Restore
docker-compose exec -T db psql -U user dbname < backup-20240101.sql
```

---

## Runbooks

### Runbook: Service Restart

**When to use:** Service is unresponsive or behaving abnormally

```bash
# 1. Check current status
docker-compose ps

# 2. Check logs for errors
docker-compose logs --tail=50 api

# 3. Graceful restart
docker-compose restart api

# 4. If graceful restart fails, force restart
docker-compose stop api
docker-compose start api

# 5. Verify service is healthy
curl http://localhost:8000/health/full

# 6. Monitor logs
docker-compose logs -f api
```

### Runbook: Scale Up

**When to use:** High traffic, slow response times

```bash
# 1. Check current resource usage
docker stats

# 2. Scale API instances
docker-compose up -d --scale api=5

# 3. Scale Celery workers
docker-compose up -d --scale celery_worker=8

# 4. Verify new instances are healthy
docker-compose ps

# 5. Monitor metrics
watch -n 5 "curl -s http://localhost:8000/metrics | grep http_requests"
```

### Runbook: Emergency Rollback

**When to use:** Critical issue after deployment

```bash
# 1. Identify last known good version
git log --oneline

# 2. Pull previous image or rebuild
docker pull color-transfer:previous-tag
# OR
git checkout <previous-commit>
docker-compose build

# 3. Stop current version
docker-compose down

# 4. Start previous version
docker-compose up -d

# 5. Verify rollback successful
curl http://localhost:8000/health/full

# 6. Notify team and investigate issue
```

### Runbook: Cache Clear

**When to use:** Stale cache data, Redis memory full

```bash
# 1. Connect to Redis
docker-compose exec redis redis-cli

# 2. Check memory usage
INFO memory

# 3. Clear all caches (CAUTION: clears all data)
FLUSHALL

# 4. Or clear specific database
SELECT 0
FLUSHDB

# 5. Verify memory cleared
INFO memory

# 6. Exit Redis CLI
EXIT
```

---

## Best Practices

### Graham's Operations Rules

1. **Automate everything** - Manual operations are error-prone
2. **Monitor proactively** - Find issues before users do
3. **Document as you go** - Future you will thank present you
4. **Test in production-like environments** - Staging should mirror prod
5. **Have a rollback plan** - Always have an escape hatch
6. **Keep it simple** - Complex systems are hard to operate
7. **Measure everything** - You can't improve what you don't measure
8. **Build for failure** - Assume things will break
9. **Security first** - Never compromise on security
10. **Communicate clearly** - Keep stakeholders informed

### Knuth's Performance Philosophy

> "Premature optimization is the root of all evil, yet we should not pass up our opportunities in that critical 3%."

**Focus on:**
1. Measure first, optimize second
2. Optimize the bottlenecks, not everything
3. Profile before and after optimization
4. Document performance characteristics
5. Establish performance budgets

---

## Additional Resources

- [Deployment Guide](./DEPLOYMENT.md)
- [Architecture Overview](./ARCHITECTURE.md)
- [Testing Guide](./tests/TESTING_GUIDE.md)
- [GitHub Repository](https://github.com/mgdavisxvs/ColorTransfer)

---

*Color Transfer Framework v2.0 - Production Operations Guide*
