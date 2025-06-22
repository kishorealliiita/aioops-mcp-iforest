import requests
import random
import time
import os
from datetime import datetime

API_URL = os.getenv("MODEL_SERVER_URL", "http://localhost:8000/api/v1/stream/multi-source")

def generate_web_log():
    timestamp = datetime.utcnow().isoformat()
    return {
        "raw_log": f'{{"timestamp": "{timestamp}", "level": "INFO", "response_time": {random.randint(40, 2000)}}}',
        "service": "web_server",
        "source": "nginx",
        "format_type": "json"
    }

def generate_db_log():
    timestamp = datetime.utcnow().isoformat()
    return {
        "raw_log": f"{timestamp} ERROR query_time={random.randint(10, 6000)}ms connection_count={random.randint(1, 200)} error_rate={random.uniform(0, 1):.2f}",
        "service": "database",
        "source": "postgresql",
        "format_type": "key_value"
    }

def generate_app_log():
    timestamp = datetime.utcnow().isoformat()
    return {
        "raw_log": f"{timestamp} [ERROR] Memory usage: {random.randint(30, 95)}% CPU usage: {random.randint(10, 99)}% Thread count: {random.randint(10, 200)}",
        "service": "application",
        "source": "java_app",
        "format_type": "regex",
        "custom_config": {
            "pattern": r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)\s+\[(\w+)\]\s+Memory usage: (\d+)%\s+CPU usage: (\d+)%\s+Thread count: (\d+)",
            "field_mapping": {
                "0": "timestamp",
                "1": "level",
                "2": "memory_usage",
                "3": "cpu_usage",
                "4": "thread_count"
            }
        }
    }

def generate_anomalous_web_log():
    """Generate an anomalous web log for testing."""
    timestamp = datetime.utcnow().isoformat()
    return {
        "raw_log": f'{{"timestamp": "{timestamp}", "level": "ERROR", "response_time": {random.randint(3000, 10000)}, "status_code": 500}}',
        "service": "web_server",
        "source": "nginx",
        "format_type": "json"
    }

def generate_anomalous_db_log():
    """Generate an anomalous database log for testing."""
    timestamp = datetime.utcnow().isoformat()
    return {
        "raw_log": f"{timestamp} ERROR query_time={random.randint(8000, 15000)}ms connection_count={random.randint(500, 1000)} error_rate={random.uniform(0.8, 1.0):.2f}",
        "service": "database",
        "source": "postgresql",
        "format_type": "key_value"
    }

def main():
    print("🚀 Starting Multi-Source Log Simulator")
    print(f"📍 API URL: {API_URL}")
    print("📊 Simulating logs from: web_server, database, application")
    print("=" * 60)
    
    cycle = 0
    while True:
        cycle += 1
        print(f"\n🔄 Cycle {cycle}")
        
        # Generate normal logs
        logs = [
            generate_web_log(),
            generate_db_log(),
            generate_app_log()
        ]
        
        # Occasionally add anomalous logs for testing
        if cycle % 5 == 0:  # Every 5th cycle
            print("🚨 Adding anomalous logs for testing...")
            logs.extend([
                generate_anomalous_web_log(),
                generate_anomalous_db_log()
            ])
        
        random.shuffle(logs)
        payload = {"logs": logs}
        
        print(f"📤 Sending {len(logs)} logs to {API_URL}")
        
        try:
            print("⏳ Making request...")
            resp = requests.post(API_URL, json=payload, timeout=10)
            print(f"📥 Response received: {resp.status_code}")
            
            if resp.status_code == 200:
                result = resp.json()
                anomaly_count = len([r for r in result if r.get('is_anomaly', 0) == 1])
                print(f"✅ Sent {len(logs)} logs, detected {anomaly_count} anomalies")
                
                # Show anomaly details if any
                if anomaly_count > 0:
                    print("🚨 Anomalies detected:")
                    for i, result_item in enumerate(result):
                        if result_item.get('is_anomaly', 0) == 1:
                            service = logs[i]['service']
                            source = logs[i]['source']
                            score = result_item.get('score', 0)
                            print(f"   - {service}/{source}: score={score:.4f}")
            else:
                print(f"❌ Error {resp.status_code}: {resp.text}")
                
        except requests.exceptions.Timeout:
            print("⏰ Request timeout")
        except requests.exceptions.ConnectionError:
            print("🔌 Connection error - is the service running?")
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        
        print(f"😴 Sleeping for 2 seconds...")
        time.sleep(2)

if __name__ == "__main__":
    main()
