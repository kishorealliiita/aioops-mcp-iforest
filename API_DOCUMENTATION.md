# AIOps Anomaly Detection API Documentation

## Overview

The AIOps Anomaly Detection Service provides real-time anomaly detection for multi-source log data using machine learning (Isolation Forest) and rule-based detection methods.

**Base URL**: `http://localhost:8000/api/v1`

## Authentication

Currently, the API does not require authentication. All endpoints are publicly accessible.

## Endpoints

### 1. Health Check

**GET** `/`

Check if the service is running.

#### Response
```json
{
  "message": "AIOps Anomaly Detection Service is active."
}
```

#### Example
```bash
curl -X GET "http://localhost:8000/api/v1/"
```

---

### 2. Get Service Metrics

**GET** `/metrics`

Retrieve high-level service and model metrics.

#### Response
```json
{
  "prediction_count": 1250,
  "anomaly_count": 45,
  "last_trained": "2024-01-15T10:30:00Z",
  "feedback_received": 12,
  "model_accuracy": 0.92
}
```

#### Example
```bash
curl -X GET "http://localhost:8000/api/v1/metrics"
```

---

### 3. Stream Multi-Source Logs

**POST** `/stream/multi-source`

Process a stream of logs from multiple sources, detect anomalies, and return results in real-time.

#### Request Body
```json
{
  "logs": [
    {
      "raw_log": "{\"timestamp\": \"2024-01-15T10:00:00Z\", \"level\": \"INFO\", \"response_time\": 150, \"message\": \"Request processed\"}",
      "service": "web_server",
      "source": "nginx",
      "format_type": "json"
    },
    {
      "raw_log": "2024-01-15T10:00:01Z ERROR query_time=5000ms connection_count=100 error_rate=0.15",
      "service": "database",
      "source": "postgresql",
      "format_type": "key_value"
    },
    {
      "raw_log": "2024-01-15T10:00:02Z [ERROR] Memory usage: 85% CPU usage: 95% Thread count: 200",
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
  ],
  "tags": {
    "environment": "production",
    "region": "us-west-1"
  }
}
```

#### Response
```json
[
  {
    "score": 0.15,
    "is_anomaly": 0
  },
  {
    "score": -0.85,
    "is_anomaly": 1
  },
  {
    "score": -0.92,
    "is_anomaly": 1
  }
]
```

#### Example
```bash
curl -X POST "http://localhost:8000/api/v1/stream/multi-source" \
  -H "Content-Type: application/json" \
  -d @app/payloads/train_payload.json
```

#### Supported Log Formats

1. **JSON Format**
   ```json
   {
     "raw_log": "{\"timestamp\": \"2024-01-15T10:00:00Z\", \"level\": \"INFO\", \"response_time\": 150}",
     "service": "web_server",
     "source": "nginx",
     "format_type": "json"
   }
   ```

2. **Key-Value Format**
   ```json
   {
     "raw_log": "2024-01-15T10:00:00Z INFO response_time=150ms bytes_out=1024 error_rate=0.02",
     "service": "database",
     "source": "postgresql",
     "format_type": "key_value"
   }
   ```

3. **Regex Format**
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

---

### 4. Get Recent Anomalies

**GET** `/anomalies`

Retrieve the most recent anomaly records from the global history.

#### Query Parameters
- `limit` (optional): Number of anomalies to return (default: 100, max: 1000)

#### Response
```json
[
  {
    "timestamp": "2024-01-15T10:00:01Z",
    "service": "database",
    "source": "postgresql",
    "log_level": "ERROR",
    "message": "Rule violation: query_time (5000) > 2000",
    "anomaly_score": 1.0,
    "rule_violation": true,
    "features": {
      "query_time": 5000,
      "connection_count": 100,
      "error_rate": 0.15
    },
    "raw_log": "2024-01-15T10:00:01Z ERROR query_time=5000ms connection_count=100 error_rate=0.15",
    "metadata": {
      "violated_rule": "query_time",
      "threshold": 2000,
      "actual_value": 5000
    },
    "context": {}
  }
]
```

#### Example
```bash
# Get last 50 anomalies
curl -X GET "http://localhost:8000/api/v1/anomalies?limit=50"

# Get default (100) anomalies
curl -X GET "http://localhost:8000/api/v1/anomalies"
```

---

### 5. Clear All Anomalies

**DELETE** `/anomalies`

Clear all stored anomaly records.

#### Response
```json
{
  "message": "All anomaly records have been cleared."
}
```

#### Example
```bash
curl -X DELETE "http://localhost:8000/api/v1/anomalies"
```

---

### 6. Train Model

**POST** `/train`

Asynchronously train the model with provided log data.

#### Request Body
```json
{
  "logs": [
    {
      "raw_log": "{\"timestamp\": \"2024-01-15T10:00:00Z\", \"level\": \"INFO\", \"response_time\": 120, \"message\": \"Request processed\"}",
      "service": "web_server",
      "source": "nginx",
      "format_type": "json"
    },
    {
      "raw_log": "2024-01-15T10:00:01Z INFO query_time=80ms connection_count=15 error_rate=0.01",
      "service": "database",
      "source": "postgresql",
      "format_type": "key_value"
    },
    {
      "raw_log": "2024-01-15T10:00:02Z [INFO] Memory usage: 45% CPU usage: 25% Thread count: 50",
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
  ]
}
```

#### Response
```json
{
  "message": "Model retraining started in the background."
}
```

#### Example
```bash
# Using the provided training payload
curl -X POST "http://localhost:8000/api/v1/train" \
  -H "Content-Type: application/json" \
  -d @app/payloads/train_payload.json

# Using custom data
curl -X POST "http://localhost:8000/api/v1/train" \
  -H "Content-Type: application/json" \
  -d '{
    "logs": [
      {
        "raw_log": "{\"timestamp\": \"2024-01-15T10:00:00Z\", \"level\": \"INFO\", \"response_time\": 120}",
        "service": "web_server",
        "source": "nginx",
        "format_type": "json"
      }
    ]
  }'
```

---

### 7. Submit Feedback

**POST** `/feedback`

Submit user feedback on log classifications to improve model accuracy.

#### Request Body
```json
{
  "feedback": [
    {
      "log": {
        "raw_log": "2024-01-15T10:05:00Z ERROR query_time=15000ms connection_count=900",
        "service": "database",
        "source": "postgresql",
        "format_type": "key_value"
      },
      "is_anomaly": 1
    },
    {
      "log": {
        "raw_log": "{\"timestamp\": \"2024-01-15T10:06:00Z\", \"level\": \"INFO\", \"response_time\": 200}",
        "service": "web_server",
        "source": "nginx",
        "format_type": "json"
      },
      "is_anomaly": 0
    }
  ]
}
```

#### Response
```json
{
  "message": "Feedback received for 2 records. Thank you!"
}
```

#### Example
```bash
curl -X POST "http://localhost:8000/api/v1/feedback" \
  -H "Content-Type: application/json" \
  -d @app/payloads/feedback_payload.json
```

---

## Error Responses

### 400 Bad Request
```json
{
  "detail": "No logs provided in the request."
}
```

### 500 Internal Server Error
```json
{
  "detail": "An internal error occurred during stream processing."
}
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `API_HOST` | `0.0.0.0` | API server host |
| `API_PORT` | `8000` | API server port |
| `MODEL_PATH` | `models/isolation_forest_model.pkl` | Path to save/load the model |
| `MODEL_CONTAMINATION` | `0.05` | Expected proportion of anomalies in the data |
| `ANOMALY_THRESHOLD` | `0.75` | Score threshold to classify as anomaly |
| `MAX_RECENT_ANOMALIES` | `500` | Maximum number of anomalies to store |

### Alert Configuration

Configure alert conditions via environment variables:

```bash
export ALERT_CONDITIONS='{
  "web_server": {"response_time": 2000, "error_rate": 0.1},
  "database": {"query_time": 5000, "connection_count": 500},
  "__default__": {"cpu_usage": 90, "memory_usage": 85}
}'
```

---

## Usage Examples

### 1. Real-time Monitoring Setup

```bash
# Start the service
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Train the model with historical data
curl -X POST "http://localhost:8000/api/v1/train" \
  -H "Content-Type: application/json" \
  -d @app/payloads/train_payload.json

# Stream logs for real-time anomaly detection
curl -X POST "http://localhost:8000/api/v1/stream/multi-source" \
  -H "Content-Type: application/json" \
  -d '{
    "logs": [
      {
        "raw_log": "{\"timestamp\": \"2024-01-15T10:00:00Z\", \"level\": \"ERROR\", \"response_time\": 5000}",
        "service": "web_server",
        "source": "nginx",
        "format_type": "json"
      }
    ]
  }'
```

### 2. Batch Processing

```bash
# Process multiple logs at once
curl -X POST "http://localhost:8000/api/v1/stream/multi-source" \
  -H "Content-Type: application/json" \
  -d @app/payloads/train_payload.json

# Check results
curl -X GET "http://localhost:8000/api/v1/anomalies?limit=10"
```

### 3. Model Management

```bash
# Retrain model with new data
curl -X POST "http://localhost:8000/api/v1/train" \
  -H "Content-Type: application/json" \
  -d @app/payloads/train_payload.json

# Check model metrics
curl -X GET "http://localhost:8000/api/v1/metrics"
```

---

## Rate Limits

Currently, there are no rate limits implemented. However, it's recommended to:

- Batch log processing when possible
- Use reasonable request sizes (max 1000 logs per request)
- Implement client-side rate limiting for high-volume scenarios

---

## Support

For issues and questions:
1. Check the service logs for detailed error messages
2. Verify your log format matches the expected schema
3. Ensure the model has been trained with sufficient data
4. Review the metrics endpoint for service health information 