# AIOps MCP Isolation Forest

A lightweight, real-time AIOps anomaly detection system for logs, using an Isolation Forest model. This service is designed to be deployed on Kubernetes and can stream logs from multiple sources, detect anomalies based on learned patterns, and send alerts through various channels.

## Features

- **Real-time Anomaly Detection**: Uses an Isolation Forest model to score incoming logs for anomalies.
- **Multi-Source Log Ingestion**: Accepts logs from different services and sources in various formats (JSON, Key-Value).
- **Extensible Alerting**: Sends alerts via Slack, PagerDuty, or a generic webhook.
- **Model Retraining**: Supports online model retraining through a dedicated API endpoint.
- **Feedback Loop**: Allows users to submit feedback on predictions to improve the model over time.
- **Containerized & Deployable**: Ready for deployment on Kubernetes with an included Helm chart.

## Project Structure

```
.
├── app/                  # Main application source code
│   ├── api/              # API routes (endpoints)
│   ├── alerts/           # Alerting plugins (Slack, PagerDuty, etc.)
│   ├── services/         # Core business logic (anomaly detection, model service)
│   ├── schemas/          # Pydantic data models
│   ├── simulator/        # Log generator for testing
│   ├── main.py           # FastAPI application entrypoint
│   └── config.py         # Application settings management
├── helm/                 # Helm chart for Kubernetes deployment
├── tests/                # Pytest unit and integration tests
├── Dockerfile            # Dockerfile for the main application
├── Dockerfile.log-generator # Dockerfile for the log simulator
├── requirements.txt      # Python dependencies
└── README.md
```

---

## Local Development Setup

### Prerequisites

- Python 3.11+
- `venv` for virtual environment management
- `curl` for testing the API

### 1. Clone the Repository

```bash
git clone <repository-url>
cd aioops-mcp-iforest
```

### 2. Set Up Virtual Environment

Create and activate a virtual environment to isolate project dependencies.

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

Install all the required Python packages.

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

The application uses a `.env` file for configuration. Copy the example file and fill in your specific values, especially for alerting.

```bash
cp env.example .env
```

Edit the `.env` file with your details:
```
# .env
APP_NAME="AIOps Anomaly Detection Service"
...
# --- Alerting ---
SLACK_WEBHOOK_URL="your-slack-webhook-url"
PAGERDUTY_ROUTING_KEY="your-pagerduty-routing-key"
GENERIC_WEBHOOK_URL="your-generic-webhook-url"
```

### 5. Run the Application

Launch the FastAPI service using Uvicorn. The `--reload` flag will automatically restart the server on code changes.

```bash
uvicorn app.main:app --reload
```
The service will be available at `http://localhost:8000`.

### 6. Run the Log Simulator (Optional)

To generate test logs and send them to the service, run the log simulator in a separate terminal.

```bash
python app/simulator/log_simulator.py
```

---

## Testing

### Running Unit Tests

To run the full suite of unit tests, use `pytest`:

```bash
pytest
```

### Manual API Testing with cURL

You can use the provided `test-curl.sh` script or run the commands individually.

**Health Check:**
```bash
curl -X GET http://localhost:8000/health
```

**Stream Logs:**
```bash
curl -X POST http://localhost:8000/api/v1/stream/multi-source \
-H "Content-Type: application/json" \
-d '{
  "logs": [
    {
      "raw_log": "{\"timestamp\": \"2024-01-01T10:00:00Z\", \"level\": \"INFO\", \"response_time\": 150}",
      "service": "web_server",
      "source": "nginx",
      "format_type": "json"
    }
  ]
}'
```

---

## Configuring Alerting Logic

The service provides a flexible, two-layered system for identifying anomalies and triggering alerts. This is configured in your `.env` file (or `values.yaml` for Helm deployments).

### Layer 1: Anomaly Identification

An individual log is flagged as an "anomaly" if it meets **either** of the following criteria:

#### 1. Simple Rule-Based Conditions (`ALERT_CONDITIONS`)

These are fast, deterministic rules that check if a numeric feature in a log exceeds a defined threshold. This is useful for setting hard limits on critical metrics. Rules can be defined per-service, with a `__default__` fallback.

**Example `env.example`:**
```ini
ALERT_CONDITIONS='{
  "web_server": {
    "response_time": 1500,
    "error_rate": 0.1
  },
  "database": {
    "query_time_ms": 3000
  },
  "__default__": {
    "cpu_usage_percent": 95
  }
}'
```
- A log from `web_server` with `response_time` of `1600` is an anomaly.
- A log from `database` with `query_time_ms` of `4000` is an anomaly.
- A log from any other service with `cpu_usage_percent` of `98` is an anomaly.

#### 2. Model-Based Detection

If a log does not violate any simple rules, it is passed to the Isolation Forest machine learning model. The model calculates an anomaly score, and if the score is below the `ANOMALY_THRESHOLD`, the log is flagged as an anomaly. This allows the system to catch more subtle or complex patterns that simple rules would miss.

### Layer 2: Alert Triggering

To reduce noise, the system does not send an alert for every single anomaly. Instead, it only sends an alert when the *frequency* of anomalies becomes significant.

#### Complex, Rate-Based Rules (`COMPLEX_ALERT_RULES`)

This setting defines the conditions for sending a `high_anomaly_rate` alert. It tracks the number of identified anomalies (from both simple rules and the ML model) for each service over a rolling time window.

**Example `env.example`:**
```ini
COMPLEX_ALERT_RULES='{
  "web_server": { "count": 5, "window_seconds": 60 },
  "database": { "count": 10, "window_seconds": 300 },
  "__default__": { "count": 20, "window_seconds": 300 }
}'
```
- **Scenario**: If 5 anomalies (of any kind) are detected for the `web_server` within a 60-second period, a single `high_anomaly_rate` alert is sent. No individual alerts for those 5 anomalies are sent.
- If only 4 anomalies occur, no alert is sent. They are simply stored for later analysis.

This approach ensures you are only notified about sustained or high-frequency problems, not single, transient spikes.

## Deployment to Kubernetes

### Prerequisites

- A running Kubernetes cluster
- `kubectl` configured to connect to your cluster
- `helm` version 3+

### 1. Configure Helm `values.yaml`

Before deploying, you must configure the Helm chart's values, especially for environment variables like your alerting webhooks.

Edit `helm/aioops-mcp-iforest/values.yaml` and update the `env` section:

```yaml
# helm/aioops-mcp-iforest/values.yaml

# ... other values ...

# -- Environment variables for the application
env:
  API_HOST: "0.0.0.0"
  API_PORT: "8000"
  # Replace with your actual webhook URLs
  SLACK_WEBHOOK_URL: "https://hooks.slack.com/services/YOUR/SLACK/URL"
  PAGERDUTY_ROUTING_KEY: ""
  GENERIC_WEBHOOK_URL: ""
```

You can also enable the log generator job for testing purposes:

```yaml
log-generator:
  enabled: true # Set to true to deploy the log generator
```

### 2. Deploy with Helm

Install the Helm chart to deploy the application and the log generator to your cluster.

```bash
helm install aioops-mcp-iforest ./helm/aioops-mcp-iforest
```

### 3. Verify the Deployment

Check the status of your pods. You should see pods for the main service and, if enabled, the log generator.

```bash
kubectl get pods -l app.kubernetes.io/name=aioops-mcp-iforest
```

### 4. Access the Service Locally

To access the service running in your cluster from your local machine, use `kubectl port-forward`.

```bash
# Forward to the main service
kubectl port-forward svc/aioops-mcp-iforest 8000:8000
```

You can now use the `curl` commands above to interact with the service at `http://localhost:8000`.

### 5. Uninstalling the Release

To remove the deployment from your cluster, use `helm uninstall`.

```bash
helm uninstall aioops-mcp-iforest
```

### Alternative Deployment: Centralized Anomaly Detection for AI Agents

This service is designed to function as a powerful, centralized anomaly detection engine within a larger AI or AIOps ecosystem.

Instead of running anomaly detection models on individual agents, those agents can be configured to stream their collected logs to this single, robust service. This offers several advantages:
- **Centralized Model Management**: A single, more powerful model can be trained and managed, rather than maintaining separate models on each agent.
- **Consistent Anomaly Scoring**: Ensures that all logs across the entire system are evaluated using the same criteria.
- **Simplified Agent Logic**: Agents can focus on log collection and forwarding, offloading the complex task of anomaly detection.

To use it in this capacity, deploy this service and configure your fleet of AI agents to send their log data to the `/api/v1/stream/multi-source` endpoint. 

## 🤝 Contributing

Contributions, issues, and feature ideas are welcome!  
See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to get started.


## 📄 License

This project is licensed under the [MIT License](LICENSE).

## 🙋‍♂️ Author

Created and maintained by [Kishore Korathaluri](https://www.linkedin.com/in/kishore-korathaluri/).  
Built as a personal side project to explore AIOps and log anomaly detection.
