import json
from typing import Any, Dict, List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings

from app.utils.logger import setup_logger

logger = setup_logger("config")


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # API Settings
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_workers: int = Field(default=1, env="API_WORKERS")

    # Model Settings
    model_path: str = Field(default="models/isolation_forest_model.pkl", env="MODEL_PATH")
    model_contamination: float = Field(default=0.05, env="MODEL_CONTAMINATION")
    model_random_state: int = Field(default=42, env="MODEL_RANDOM_STATE")
    min_train_samples: int = Field(default=50, env="MIN_TRAIN_SAMPLES")
    default_feature_dim: int = Field(default=3, description="Default number of features for the dummy model.")
    iforest_n_estimators: int = Field(default=100, env="IFOREST_N_ESTIMATORS")
    iforest_contamination: float = Field(default=0.05, env="IFOREST_CONTAMINATION")
    random_state: int = Field(default=42, env="RANDOM_STATE")
    feature_names: List[str] = Field(default=["resp_time", "bytes_out", "error_rate"], env="FEATURE_NAMES")

    # Alert Settings
    alert_conditions: Optional[str] = Field(default=None, env="ALERT_CONDITIONS")
    slack_webhook_url: Optional[str] = Field(default=None, env="SLACK_WEBHOOK_URL")
    pagerduty_routing_key: Optional[str] = Field(default=None, env="PAGERDUTY_ROUTING_KEY")
    generic_webhook_url: Optional[str] = Field(default=None, env="GENERIC_WEBHOOK_URL")

    # Logging Settings
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Feature Extraction Settings
    feature_columns: list = Field(default=["resp_time", "bytes_out", "error_rate"])

    # Anomaly Storage Settings
    max_recent_anomalies: int = Field(default=500, env="MAX_RECENT_ANOMALIES")
    anomaly_threshold: float = Field(default=0.75, description="Score threshold to classify a log as an anomaly.")

    # Feedback settings
    feedback_store_path: str = Field(default="feedback/labeled_data.json", env="FEEDBACK_STORE_PATH")

    # Complex Alert Rules
    complex_alert_rules: Optional[str] = Field(default=None, env="COMPLEX_ALERT_RULES")

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_alert_conditions() -> Dict[str, Any]:
    """Safely parse the ALERT_CONDITIONS JSON string with sensible defaults."""
    default_conditions = {
        "web_server": {"response_time": 2000, "error_rate": 0.1},
        "database": {"query_time": 5000, "connection_count": 500, "error_rate": 0.05},
        "application": {"cpu_usage": 90, "memory_usage": 85, "thread_count": 300},
        "__default__": {"cpu_usage": 95, "memory_usage": 90, "error_rate": 0.2},
    }

    if not settings.alert_conditions:
        logger.info("No ALERT_CONDITIONS set, using default alert conditions")
        return default_conditions

    try:
        user_conditions = json.loads(settings.alert_conditions)
        # Merge user conditions with defaults, allowing user to override
        merged_conditions = default_conditions.copy()
        for service, rules in user_conditions.items():
            if service in merged_conditions:
                merged_conditions[service].update(rules)
            else:
                merged_conditions[service] = rules
        return merged_conditions
    except json.JSONDecodeError:
        logger.error("Failed to parse ALERT_CONDITIONS JSON string, using defaults.", exc_info=True)
        return default_conditions


def get_complex_alert_rules() -> Dict[str, Any]:
    """Safely parse the COMPLEX_ALERT_RULES JSON string with sensible defaults."""
    default_rules = {
        "web_server": {"count": 3, "window_seconds": 60},
        "database": {"count": 5, "window_seconds": 120},
        "application": {"count": 8, "window_seconds": 180},
        "__default__": {"count": 10, "window_seconds": 300},
    }

    if not settings.complex_alert_rules:
        logger.info("No COMPLEX_ALERT_RULES set, using default complex alert rules")
        return default_rules

    try:
        user_rules = json.loads(settings.complex_alert_rules)
        # Merge user rules with defaults, allowing user to override
        merged_rules = default_rules.copy()
        for service, rule in user_rules.items():
            merged_rules[service] = rule
        return merged_rules
    except json.JSONDecodeError:
        logger.error("Failed to parse COMPLEX_ALERT_RULES JSON string, using defaults.", exc_info=True)
        return default_rules
