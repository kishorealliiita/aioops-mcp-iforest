import json
from datetime import datetime
from typing import Any, Dict, Optional

from app.alerts.alert_manager import AlertPlugin
from app.utils.logger import setup_logger

logger = setup_logger("console_alert")


class ConsoleAlertPlugin(AlertPlugin):
    """Console alert plugin that prints alerts to stdout for debugging and testing."""

    def __init__(self, include_timestamp: bool = True):
        self.include_timestamp = include_timestamp

    def send_alert(self, message: str, details: Dict[str, Any], alert_type: Optional[str] = None) -> None:
        """Print alert to console with formatted output."""
        timestamp = datetime.now().isoformat() if self.include_timestamp else ""

        # Print to console with clear formatting
        print("\n" + "=" * 80)
        print("🚨 ALERT TRIGGERED 🚨")
        print("=" * 80)
        print(f"Time: {timestamp}")
        print(f"Type: {alert_type or 'general'}")
        print(f"Message: {message}")
        print("\nDetails:")
        print(json.dumps(details, indent=2, default=str))
        print("=" * 80 + "\n")

        # Also log to the application logger
        logger.warning(f"Alert triggered: {message} - {json.dumps(details, default=str)}")
