#!/bin/bash

# AIOps Anomaly Detection API Test Script
# Usage: ./scripts/test-curl.sh [endpoint]
# Endpoints: health, train, stream, anomalies, feedback, metrics, clear, all

BASE_URL="http://localhost:8000/api/v1"
PAYLOAD_DIR="../app/payloads"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to test health endpoint
test_health() {
    print_status "Testing health endpoint..."
    curl -s -X GET "$BASE_URL/" | jq .
    echo
}

# Function to test metrics endpoint
test_metrics() {
    print_status "Testing metrics endpoint..."
    curl -s -X GET "$BASE_URL/metrics" | jq .
    echo
}

# Function to test training endpoint
test_train() {
    print_status "Testing model training..."
    if [ -f "$PAYLOAD_DIR/train_payload.json" ]; then
        curl -s -X POST "$BASE_URL/train" \
            -H "Content-Type: application/json" \
            -d @"$PAYLOAD_DIR/train_payload.json" | jq .
    else
        print_warning "Training payload file not found, using inline data..."
        curl -s -X POST "$BASE_URL/train" \
            -H "Content-Type: application/json" \
            -d '{
                "logs": [
                    {
                        "raw_log": "{\"timestamp\": \"2024-01-01T10:00:00Z\", \"level\": \"INFO\", \"response_time\": 120, \"message\": \"Request processed\"}",
                        "service": "web_server",
                        "source": "nginx",
                        "format_type": "json"
                    },
                    {
                        "raw_log": "2024-01-01T10:00:01Z INFO query_time=80ms connection_count=15 error_rate=0.01",
                        "service": "database",
                        "source": "postgresql",
                        "format_type": "key_value"
                    }
                ]
            }' | jq .
    fi
    echo
}

# Function to test streaming endpoint
test_stream() {
    print_status "Testing log streaming with anomaly detection..."
    if [ -f "$PAYLOAD_DIR/train_payload.json" ]; then
        curl -s -X POST "$BASE_URL/stream/multi-source" \
            -H "Content-Type: application/json" \
            -d @"$PAYLOAD_DIR/train_payload.json" | jq .
    else
        print_warning "Training payload file not found, using inline data..."
        curl -s -X POST "$BASE_URL/stream/multi-source" \
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
                    },
                    {
                        "raw_log": "2024-01-01T10:06:00Z [ERROR] Memory usage: 95% CPU usage: 98% Thread count: 500",
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
            }' | jq .
    fi
    echo
}

# Function to test anomalies endpoint
test_anomalies() {
    print_status "Testing anomalies retrieval..."
    curl -s -X GET "$BASE_URL/anomalies?limit=5" | jq .
    echo
}

# Function to test feedback endpoint
test_feedback() {
    print_status "Testing feedback submission..."
    if [ -f "$PAYLOAD_DIR/feedback_payload.json" ]; then
        curl -s -X POST "$BASE_URL/feedback" \
            -H "Content-Type: application/json" \
            -d @"$PAYLOAD_DIR/feedback_payload.json" | jq .
    else
        print_warning "Feedback payload file not found, using inline data..."
        curl -s -X POST "$BASE_URL/feedback" \
            -H "Content-Type: application/json" \
            -d '{
                "feedback": [
                    {
                        "log": {
                            "raw_log": "2024-01-01T10:05:00Z ERROR query_time=15000ms connection_count=900 error_rate=0.9",
                            "service": "database",
                            "source": "postgresql",
                            "format_type": "key_value"
                        },
                        "is_anomaly": 1
                    },
                    {
                        "log": {
                            "raw_log": "{\"timestamp\": \"2024-01-01T10:06:00Z\", \"level\": \"INFO\", \"response_time\": 200}",
                            "service": "web_server",
                            "source": "nginx",
                            "format_type": "json"
                        },
                        "is_anomaly": 0
                    }
                ]
            }' | jq .
    fi
    echo
}

# Function to test clear anomalies endpoint
test_clear() {
    print_status "Testing anomalies clearing..."
    curl -s -X DELETE "$BASE_URL/anomalies" | jq .
    echo
}

# Function to run all tests
test_all() {
    print_status "Running comprehensive API test suite..."
    echo "=========================================="
    
    test_health
    test_metrics
    test_train
    test_stream
    test_anomalies
    test_feedback
    test_clear
    
    print_success "All tests completed!"
}

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    print_warning "jq is not installed. Installing jq for better JSON formatting..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew install jq
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo apt-get update && sudo apt-get install -y jq
    else
        print_error "Please install jq manually for better output formatting"
    fi
fi

# Main script logic
case "${1:-all}" in
    "health")
        test_health
        ;;
    "train")
        test_train
        ;;
    "stream")
        test_stream
        ;;
    "anomalies")
        test_anomalies
        ;;
    "feedback")
        test_feedback
        ;;
    "metrics")
        test_metrics
        ;;
    "clear")
        test_clear
        ;;
    "all")
        test_all
        ;;
    *)
        print_error "Unknown endpoint: $1"
        echo "Available endpoints: health, train, stream, anomalies, feedback, metrics, clear, all"
        exit 1
        ;;
esac
