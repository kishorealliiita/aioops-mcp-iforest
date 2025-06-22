import os
from typing import Dict, Any, Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
import json
import logging
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
    """Safely parse the ALERT_CONDITIONS JSON string."""
    if not settings.alert_conditions:
        return {}
    try:
        return json.loads(settings.alert_conditions)
    except json.JSONDecodeError:
        logger.error("Failed to parse ALERT_CONDITIONS JSON string.", exc_info=True)
        return {}

def get_complex_alert_rules() -> Dict[str, Any]:
    """Safely parse the COMPLEX_ALERT_RULES JSON string."""
    if not settings.complex_alert_rules:
        return {}
    try:
        return json.loads(settings.complex_alert_rules)
    except json.JSONDecodeError:
        logger.error("Failed to parse COMPLEX_ALERT_RULES JSON string.", exc_info=True)
        return {} 