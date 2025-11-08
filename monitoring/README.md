# Color Transfer Framework - Monitoring Stack

Complete monitoring infrastructure with Prometheus and Grafana.

## Quick Start

```bash
# Start monitoring services
docker-compose up -d prometheus grafana

# Or use Makefile
make monitoring-up

# Access services
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3000 (admin/admin)
```

## Directory Structure

```
monitoring/
├── prometheus/
│   └── prometheus.yml          # Prometheus scrape configuration
├── grafana/
│   ├── dashboards/
│   │   ├── dashboard-config.yml              # Dashboard provisioning config
│   │   └── color-transfer-overview.json      # Main dashboard
│   └── datasources/
│       └── prometheus.yml                    # Prometheus datasource config
└── README.md                   # This file
```

## Prometheus Configuration

**Configuration file**: `prometheus/prometheus.yml`

**Scrape targets**:
- `color-transfer-api:8000/metrics` - FastAPI REST API
- `color-transfer-web:5000/metrics` - Flask Web UI
- `color-transfer-web-enhanced:5000/metrics` - Enhanced Web UI

**Scrape interval**: 10-15 seconds

**Key metrics collected**:
- HTTP request metrics (rate, duration, status)
- Color transfer operation metrics
- System metrics (CPU, memory, file descriptors)
- Redis cache metrics
- Celery queue metrics

## Grafana Dashboards

### Color Transfer Framework - Overview

**UID**: `color-transfer-overview`

**Sections**:
1. **System Overview** - CPU, memory, request rate
2. **API Performance** - Response times, error rates, throughput
3. **Application Metrics** - Operations by algorithm, durations, errors
4. **Infrastructure** - Redis connections, Celery queue length

**Auto-provisioned**: Yes (automatically loaded on Grafana startup)

**Refresh rate**: 10 seconds

**Time range**: Last 1 hour (customizable)

### Creating Custom Dashboards

1. Access Grafana: http://localhost:3000
2. Click "Create" → "Dashboard"
3. Add panel with PromQL queries
4. Save dashboard

**Useful PromQL queries**:

```promql
# Request rate
rate(http_requests_total[5m])

# Response time (p95)
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Error rate
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])

# CPU usage
rate(process_cpu_seconds_total[5m]) * 100

# Memory usage
process_resident_memory_bytes

# Operations by algorithm
rate(color_transfer_operations_total[5m])

# Cache hit rate
redis_cache_hits_total / (redis_cache_hits_total + redis_cache_misses_total)
```

## Configuration Files

### Prometheus Scrape Config

Edit `prometheus/prometheus.yml` to add new scrape targets:

```yaml
scrape_configs:
  - job_name: 'my-service'
    static_configs:
      - targets: ['my-service:port']
        labels:
          service: 'my-service-name'
```

Reload Prometheus configuration:
```bash
# Prometheus supports hot reload
curl -X POST http://localhost:9090/-/reload

# Or restart container
docker-compose restart prometheus
```

### Grafana Datasource

The Prometheus datasource is automatically configured via `grafana/datasources/prometheus.yml`.

**Default settings**:
- URL: http://prometheus:9090
- Scrape interval: 15s
- Query timeout: 60s
- Default datasource: Yes

### Dashboard Provisioning

Dashboards are automatically loaded from `grafana/dashboards/`.

To add a new dashboard:
1. Create dashboard JSON file in `grafana/dashboards/`
2. Restart Grafana: `docker-compose restart grafana`
3. Dashboard will appear in Grafana UI

## Alerting (Optional)

To enable alerting, create alert rules:

1. Create `prometheus/alerts/rules.yml`:

```yaml
groups:
  - name: color_transfer_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }}"
```

2. Update `prometheus/prometheus.yml`:

```yaml
rule_files:
  - "alerts/*.yml"
```

3. Restart Prometheus

## Troubleshooting

### Prometheus not scraping metrics

```bash
# Check Prometheus targets
open http://localhost:9090/targets

# Check service is exposing metrics
curl http://localhost:8000/metrics

# View Prometheus logs
docker-compose logs prometheus
```

### Grafana not showing dashboards

```bash
# Check dashboard provisioning
docker-compose logs grafana | grep provisioning

# Verify dashboard files exist
ls -la monitoring/grafana/dashboards/

# Restart Grafana
docker-compose restart grafana
```

### Grafana not connecting to Prometheus

```bash
# Test Prometheus from Grafana container
docker-compose exec grafana wget -O- http://prometheus:9090/api/v1/status/config

# Check datasource in Grafana
# Configuration → Data Sources → Prometheus → Test
```

### Metrics not appearing in graphs

```bash
# Check if metrics exist in Prometheus
# Open Prometheus → Graph → Execute query
# Example: http_requests_total

# Verify time range in Grafana
# Dashboard → Time picker → Last 1 hour

# Check metric names match
curl http://localhost:8000/metrics | grep metric_name
```

## Performance Tuning

### Prometheus

```yaml
# In prometheus.yml
global:
  scrape_interval: 15s      # How often to scrape
  scrape_timeout: 10s       # Timeout for scraping
  evaluation_interval: 15s  # How often to evaluate rules
```

**Storage**:
- Default retention: 15 days
- Storage location: `/prometheus` (Docker volume)
- Increase retention: Add `--storage.tsdb.retention.time=30d` to command

### Grafana

**Performance tips**:
- Use shorter time ranges for faster queries
- Reduce refresh rate for less load (30s instead of 5s)
- Use query caching
- Limit number of series in graphs

## Backup & Restore

### Backup Prometheus Data

```bash
# Stop Prometheus
docker-compose stop prometheus

# Backup data volume
docker run --rm -v color-transfer-prometheus-data:/data \
  -v $(pwd):/backup alpine \
  tar czf /backup/prometheus-backup.tar.gz /data

# Start Prometheus
docker-compose start prometheus
```

### Backup Grafana Dashboards

```bash
# Export dashboard JSON from Grafana UI
# Dashboard → Settings → JSON Model → Copy

# Or backup Grafana data volume
docker run --rm -v color-transfer-grafana-data:/data \
  -v $(pwd):/backup alpine \
  tar czf /backup/grafana-backup.tar.gz /data
```

### Restore

```bash
# Restore Prometheus
docker run --rm -v color-transfer-prometheus-data:/data \
  -v $(pwd):/backup alpine \
  tar xzf /backup/prometheus-backup.tar.gz -C /

# Restore Grafana
docker run --rm -v color-transfer-grafana-data:/data \
  -v $(pwd):/backup alpine \
  tar xzf /backup/grafana-backup.tar.gz -C /
```

## Security

**Default credentials**:
- Grafana: admin / admin (change immediately in production)

**Recommendations**:
1. Change Grafana admin password
2. Enable authentication for Prometheus (use reverse proxy)
3. Use HTTPS in production
4. Restrict access with firewall rules
5. Regularly update Prometheus and Grafana images

## Additional Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [PromQL Basics](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Grafana Dashboard Best Practices](https://grafana.com/docs/grafana/latest/best-practices/)

---

**Knuth's Monitoring Philosophy**: "Measure everything, optimize the critical 3%"

**Graham's Practical Monitoring**: "Start simple, add complexity as needed, automate everything"
