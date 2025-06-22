# AIOps API Quick Reference

## Base URL
```
http://localhost:8000/api/v1
```

## Common Operations

### 1. Health Check
```bash
curl -X GET "http://localhost:8000/api/v1/"
```

### 2. Train Model
```bash
curl -X POST "http://localhost:8000/api/v1/train" \
  -H "Content-Type: application/json" \
  -d @app/payloads/train_payload.json
```

### 3. Stream Logs for Anomaly Detection
```bash
curl -X POST "http://localhost:8000/api/v1/stream/multi-source" \
  -H "Content-Type: application/json" \
  -d @app/payloads/train_payload.json
```

### 4. Get Recent Anomalies
```bash
curl -X GET "http://localhost:8000/api/v1/anomalies?limit=50"
```

### 5. Get Service Metrics
```bash
curl -X GET "http://localhost:8000/api/v1/metrics"
```

### 6. Submit Feedback
```bash
curl -X POST "http://localhost:8000/api/v1/feedback" \
  -H "Content-Type: application/json" \
  -d @app/payloads/feedback_payload.json
```

### 7. Clear Anomalies
```bash
curl -X DELETE "http://localhost:8000/api/v1/anomalies"
```

## Log Format Examples

### JSON Format
```json
{
  "raw_log": "{\"timestamp\": \"2024-01-15T10:00:00Z\", \"level\": \"INFO\", \"response_time\": 150}",
  "service": "web_server",
  "source": "nginx",
  "format_type": "json"
}
```

### Key-Value Format
```json
{
  "raw_log": "2024-01-15T10:00:00Z INFO response_time=150ms bytes_out=1024 error_rate=0.02",
  "service": "database",
  "source": "postgresql",
  "format_type": "key_value"
}
```

### Regex Format
```json
{
  "raw_log": "2024-01-15T10:00:00Z [INFO] Memory usage: 45% CPU usage: 25% Thread count: 50",
  "service": "application",
  "source": "java_app",
  "format_type": "regex",
  "custom_config": {
    "pattern": "(\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(?:\\.\\d+)?(?:Z|[+-]\\d{2}:?\\d{2})?)\\s+\\[(\\w+)\\]\\s+Memory usage: (\\d+)%\\s+CPU usage: (\\d+)%\\s+Thread count: (\\d+)",
    "field_mapping": {
      "0": "timestamp",
      "1": "level",
      "2": "memory_usage",
      "3": "cpu_usage",
      "4": "thread_count"
    }
  }
}
```

## Response Examples

### Stream Response
```json
[
  {"score": 0.15, "is_anomaly": 0},
  {"score": -0.85, "is_anomaly": 1}
]
```

### Anomaly Record
```json
{
  "timestamp": "2024-01-15T10:00:01Z",
  "service": "database",
  "source": "postgresql",
  "log_level": "ERROR",
  "message": "Rule violation: query_time (5000) > 2000",
  "anomaly_score": 1.0,
  "rule_violation": true,
  "features": {"query_time": 5000, "connection_count": 100, "error_rate": 0.15},
  "raw_log": "2024-01-15T10:00:01Z ERROR query_time=5000ms connection_count=100 error_rate=0.15",
  "metadata": {"violated_rule": "query_time", "threshold": 2000, "actual_value": 5000},
  "context": {}
}
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `API_HOST` | `0.0.0.0` | API server host |
| `API_PORT` | `8000` | API server port |
| `MODEL_CONTAMINATION` | `0.05` | Expected proportion of anomalies |
| `ANOMALY_THRESHOLD` | `0.75` | Score threshold for anomalies |

## Test Scripts

### Test Training
```bash
./scripts/test-curl.sh train
```

### Test Streaming
```bash
./scripts/test-curl.sh stream
```

### Test Feedback
```bash
./scripts/test-curl.sh feedback
```

## Common Issues

1. **Model not trained**: Train with historical data first
2. **Invalid log format**: Check format_type and raw_log structure
3. **No anomalies detected**: Adjust thresholds or provide more training data
4. **Service not responding**: Check if uvicorn server is running

## Support

- Full documentation: `API_DOCUMENTATION.md`
- Test payloads: `app/payloads/`
- Test scripts: `scripts/test-curl.sh` 