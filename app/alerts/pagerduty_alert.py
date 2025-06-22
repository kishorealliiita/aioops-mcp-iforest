import requests
from typing import Dict, Any, Optional
import json

class PagerDutyAlertPlugin:
    def __init__(self, routing_key: str):
        if not routing_key:
            raise ValueError("PagerDuty routing key is required.")
        self.routing_key = routing_key
        self.api_url = "https://events.pagerduty.com/v2/enqueue"

    def send_alert(self, message: str, details: Dict[str, Any], alert_type: Optional[str] = None):
        """Sends a custom event to PagerDuty."""
        payload = {
            "routing_key": self.routing_key,
            "event_action": "trigger",
            "payload": {
                "summary": message,
                "source": details.get("service", "AIOps-Service"),
                "severity": "critical",
                "custom_details": details
            }
        }
        
        try:
            response = requests.post(self.api_url, data=json.dumps(payload), headers={'Content-Type': 'application/json'}, timeout=5)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Error sending PagerDuty alert: {e}")
