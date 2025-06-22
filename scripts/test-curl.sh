curl -X GET http://localhost:8000/health
curl -X GET http://localhost:8000/api/v1/
curl -X POST http://localhost:8000/api/v1/stream/multi-source \
-H "Content-Type: application/json" \
-d '{
  "logs": [
    {
      "raw_log": "{\"timestamp\": \"2024-01-01T10:00:00Z\", \"level\": \"INFO\", \"message\": \"Request processed successfully\", \"response_time\": 150}",
      "service": "web_server",
      "source": "nginx",
      "format_type": "json"
    },
    {
      "raw_log": "2024-01-01T10:05:00Z ERROR query_time=15000ms connection_count=900 error_rate=0.9",
      "service": "database",
      "source": "postgresql",
      "format_type": "key_value"
    }
  ]
}'
curl -X GET http://localhost:8000/api/v1/anomalies?limit=10
curl -X DELETE http://localhost:8000/api/v1/anomalies
curl -X POST http://localhost:8000/api/v1/train \
-H "Content-Type: application/json" \
-d '{
  "logs": [
    {
      "raw_log": "{\"response_time\": 110, \"bytes_out\": 1024, \"error_rate\": 0.01}",
      "service": "web_server",
      "source": "nginx",
      "format_type": "json"
    },
    {
      "raw_log": "{\"response_time\": 150, \"bytes_out\": 2048, \"error_rate\": 0.02}",
      "service": "web_server",
      "source": "nginx",
      "format_type": "json"
    }
  ]
}'
curl -X POST http://localhost:8000/api/v1/feedback \
-H "Content-Type: application/json" \
-d '{
  "feedback": [
    {
      "log": {
        "raw_log": "2024-01-01T10:05:00Z ERROR query_time=15000ms",
        "service": "database",
        "source": "postgresql",
        "format_type": "key_value"
      },
      "is_anomaly": 1
    },
    {
      "log": {
        "raw_log": "{\"response_time\": 200}",
        "service": "web_server",
        "source": "nginx",
        "format_type": "json"
      },
      "is_anomaly": 0
    }
  ]
}'
