import requests
from typing import Dict, Any, Optional
import json

class WebhookAlertPlugin:
    def __init__(self, webhook_url: str):
        if not webhook_url:
            raise ValueError("Webhook URL is required.")
        self.webhook_url = webhook_url

    def send_alert(self, message: str, details: Dict[str, Any], alert_type: Optional[str] = None):
        """Sends a generic webhook alert."""
        payload = {
            "alert_type": alert_type or "standard_anomaly",
            "message": message,
            "details": details
        }
        
        try:
            response = requests.post(self.webhook_url, json=payload, timeout=5)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Error sending webhook alert: {e}")
