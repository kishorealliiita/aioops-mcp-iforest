from typing import Any, Dict, List, Optional, Protocol


class AlertPlugin(Protocol):
    def send_alert(self, message: str, details: Dict[str, Any], alert_type: Optional[str] = None) -> None: ...


class AlertManager:
    def __init__(self):
        self.plugins: List[AlertPlugin] = []

    def register(self, plugin: AlertPlugin):
        self.plugins.append(plugin)

    def send_alert(self, message: str, details: Dict[str, Any], alert_type: Optional[str] = None):
        if not self.plugins:
            print("[AlertManager] No alert plugins registered. Cannot send alert.")
            return

        for plugin in self.plugins:
            try:
                plugin.send_alert(message, details, alert_type)
            except Exception as e:
                print(f"[AlertManager] Error sending alert via {plugin.__class__.__name__}: {e}")


# Create a single, global instance to be used across the application
alert_manager = AlertManager()
