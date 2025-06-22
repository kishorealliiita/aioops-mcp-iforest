#!/bin/bash

# AIOps Alert Testing Script
# This script tests various alert scenarios to ensure the alerting system is working

BASE_URL="http://localhost:8000/api/v1"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Test 1: Rule-based alert for web_server (response_time violation)
test_web_server_rule_alert() {
    print_status "Testing web_server rule-based alert (response_time > 2000ms)..."
    curl -s -X POST "$BASE_URL/stream/multi-source" \
        -H "Content-Type: application/json" \
        -d '{
            "logs": [
                {
                    "raw_log": "{\"timestamp\": \"2024-01-15T10:00:00Z\", \"level\": \"INFO\", \"response_time\": 2500, \"error_rate\": 0.05}",
                    "service": "web_server",
                    "source": "nginx",
                    "format_type": "json"
                }
            ]
        }' | jq .
    echo
}

# Test 2: Rule-based alert for database (query_time violation)
test_database_rule_alert() {
    print_status "Testing database rule-based alert (query_time > 5000ms)..."
    curl -s -X POST "$BASE_URL/stream/multi-source" \
        -H "Content-Type: application/json" \
        -d '{
            "logs": [
                {
                    "raw_log": "2024-01-15T10:00:01Z ERROR query_time=8000ms connection_count=100 error_rate=0.02",
                    "service": "database",
                    "source": "postgresql",
                    "format_type": "key_value"
                }
            ]
        }' | jq .
    echo
}

# Test 3: Rule-based alert for application (CPU usage violation)
test_application_rule_alert() {
    print_status "Testing application rule-based alert (CPU usage > 90%)..."
    curl -s -X POST "$BASE_URL/stream/multi-source" \
        -H "Content-Type: application/json" \
        -d '{
            "logs": [
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
            ]
        }' | jq .
    echo
}

# Test 4: Multiple anomalies to trigger rate-based alert
test_rate_based_alert() {
    print_status "Testing rate-based alert (multiple anomalies in short time)..."
    
    # Send multiple anomalies for web_server to trigger rate-based alert
    for i in {1..5}; do
        print_status "Sending anomaly $i/5 for web_server..."
        curl -s -X POST "$BASE_URL/stream/multi-source" \
            -H "Content-Type: application/json" \
            -d "{
                \"logs\": [
                    {
                        \"raw_log\": \"{\\\"timestamp\\\": \\\"2024-01-15T10:00:0${i}Z\\\", \\\"level\\\": \\\"ERROR\\\", \\\"response_time\\\": 3000, \\\"error_rate\\\": 0.15}\",
                        \"service\": \"web_server\",
                        \"source\": \"nginx\",
                        \"format_type\": \"json\"
                    }
                ]
            }" > /dev/null
        sleep 1
    done
    
    print_success "Sent 5 anomalies for web_server - should trigger rate-based alert"
    echo
}

# Test 5: Check anomalies
test_check_anomalies() {
    print_status "Checking stored anomalies..."
    curl -s -X GET "$BASE_URL/anomalies?limit=10" | jq .
    echo
}

# Test 6: Check metrics
test_check_metrics() {
    print_status "Checking service metrics..."
    curl -s -X GET "$BASE_URL/metrics" | jq .
    echo
}

# Test 7: Normal logs (should not trigger alerts)
test_normal_logs() {
    print_status "Testing normal logs (should not trigger alerts)..."
    curl -s -X POST "$BASE_URL/stream/multi-source" \
        -H "Content-Type: application/json" \
        -d '{
            "logs": [
                {
                    "raw_log": "{\"timestamp\": \"2024-01-15T10:00:00Z\", \"level\": \"INFO\", \"response_time\": 150, \"error_rate\": 0.01}",
                    "service": "web_server",
                    "source": "nginx",
                    "format_type": "json"
                },
                {
                    "raw_log": "2024-01-15T10:00:01Z INFO query_time=100ms connection_count=50 error_rate=0.001",
                    "service": "database",
                    "source": "postgresql",
                    "format_type": "key_value"
                }
            ]
        }' | jq .
    echo
}

# Main test function
run_all_tests() {
    print_status "Starting comprehensive alert testing..."
    echo "=========================================="
    
    test_normal_logs
    test_web_server_rule_alert
    test_database_rule_alert
    test_application_rule_alert
    test_rate_based_alert
    test_check_anomalies
    test_check_metrics
    
    print_success "Alert testing completed!"
    print_status "Check the console output above for alert messages (🚨 ALERT TRIGGERED 🚨)"
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
    "web_server")
        test_web_server_rule_alert
        ;;
    "database")
        test_database_rule_alert
        ;;
    "application")
        test_application_rule_alert
        ;;
    "rate")
        test_rate_based_alert
        ;;
    "normal")
        test_normal_logs
        ;;
    "anomalies")
        test_check_anomalies
        ;;
    "metrics")
        test_check_metrics
        ;;
    "all")
        run_all_tests
        ;;
    *)
        print_error "Unknown test: $1"
        echo "Available tests: web_server, database, application, rate, normal, anomalies, metrics, all"
        exit 1
        ;;
esac 