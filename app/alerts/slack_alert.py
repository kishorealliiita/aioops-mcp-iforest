import requests
import json
from typing import Dict, Any, Optional

class SlackAlertPlugin:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send_alert(self, message: str, details: Dict[str, Any], alert_type: Optional[str] = None):
        """Sends an alert to Slack with formatted details."""
        
        if alert_type == "high_anomaly_rate":
            header_text = f"🔥 *High Anomaly Rate Detected* 🔥"
            title = f"Service: *{details.get('service', 'N/A')}*"
            fields = [
                {"title": "Time Window", "value": f"{details.get('time_window_seconds')}s", "short": True},
                {"title": "Anomaly Count", "value": str(details.get('anomaly_count_in_window')), "short": True}
            ]
        else:
            header_text = f"🚨 *Anomaly Detected* 🚨"
            title = f"Service: *{details.get('service', 'N/A')}* | Source: *{details.get('source', 'N/A')}*"
            fields = [
                {"title": "Score", "value": f"{details.get('anomaly_score', 0):.4f}", "short": True},
                {"title": "Timestamp", "value": details.get('timestamp', 'N/A'), "short": True}
            ]

        payload = {
            "attachments": [
                {
                    "color": "#FF0000",
                    "blocks": [
                        {"type": "header", "text": {"type": "plain_text", "text": header_text}},
                        {"type": "divider"},
                        {"type": "section", "text": {"type": "mrkdwn", "text": title}},
                        {"type": "section", "fields": [{"type": "mrkdwn", "text": f"*{f['title']}*\n{f['value']}"} for f in fields]},
                        {
                            "type": "section", 
                            "text": {
                                "type": "mrkdwn", 
                                "text": f"*Message*: {message}\n*Details*:\n```{json.dumps(details, indent=2)}```"
                            }
                        }
                    ]
                }
            ]
        }
        
        try:
            requests.post(self.webhook_url, json=payload, timeout=5)
        except requests.exceptions.RequestException as e:
            print(f"Error sending Slack alert: {e}")
