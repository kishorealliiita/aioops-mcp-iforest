import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta, timezone
from collections import defaultdict, deque
from dataclasses import dataclass
import json
from pathlib import Path
from fastapi.encoders import jsonable_encoder
import threading
from pydantic import ValidationError

from app.services.model_service import ModelService, get_model_service
from app.services.log_parser_service import ParsedLog, log_parser_service, LogParserService
from app.utils.logger import setup_logger
from app.alerts.alert_manager import alert_manager
from app.config import settings, get_alert_conditions, get_complex_alert_rules
from app.schemas.models import AnomalyResult, AnomalyContext, ParsedLogRecord

logger = setup_logger("anomaly_detection_service")


@dataclass
class AnomalyContext:
    """Context information for anomaly detection."""
    service: str
    source: str
    time_window: timedelta
    baseline_metrics: Dict[str, float]
    thresholds: Dict[str, float]
    recent_logs: deque


class AnomalyDetectionService:
    """
    Primary service for anomaly detection, context management, and alerting.
    Consolidates all anomaly-related logic.
    """
    
    def __init__(self, model_service: ModelService, log_parser: LogParserService, alert_manager):
        self.model_service = model_service
        self.log_parser = log_parser
        self.alert_manager = alert_manager
        self.alert_conditions = get_alert_conditions()
        self.complex_alert_rules = get_complex_alert_rules()
        
        logger.info(f"Initialized with complex alert rules: {self.complex_alert_rules}")
        
        # Per-service anomaly context and history
        self.service_contexts: Dict[str, AnomalyContext] = {}
        self.anomaly_history: deque = deque(maxlen=settings.max_recent_anomalies)
        self.service_anomaly_timestamps: Dict[str, deque] = defaultdict(deque)
        
        self.service_configs = {} # Placeholder for dynamic configs
        self._storage_path = Path("feedback/anomalies.json")
        self._storage_lock = threading.Lock()
        
        self._load_persisted_anomalies()
    
    def _load_persisted_anomalies(self):
        """Loads anomaly history from a JSON file at startup."""
        with self._storage_lock:
            if not self._storage_path.exists():
                return
            try:
                with open(self._storage_path, 'r') as f:
                    anomalies_data = json.load(f)
                    # Use Pydantic to parse and validate, ensuring data integrity
                    self.anomaly_history.extend([AnomalyResult.model_validate(item) for item in anomalies_data])
                    logger.info(f"Loaded {len(self.anomaly_history)} persisted anomalies from {self._storage_path}")
            except (IOError, json.JSONDecodeError, ValidationError) as e:
                logger.error(f"Failed to load or parse persisted anomalies: {e}", exc_info=True)
                # If loading fails, start with a clean slate to prevent crashes
                self.anomaly_history.clear()

    def _persist_anomalies(self):
        """Persists the current anomaly history to a JSON file."""
        with self._storage_lock:
            try:
                self._storage_path.parent.mkdir(exist_ok=True)
                # Use jsonable_encoder to handle complex types like datetime
                data_to_persist = jsonable_encoder(list(self.anomaly_history))
                with open(self._storage_path, 'w') as f:
                    json.dump(data_to_persist, f, indent=4)
            except IOError as e:
                logger.error(f"Failed to persist anomalies to {self._storage_path}: {e}", exc_info=True)

    def detect_and_store_anomalies(self, parsed_logs: List[ParsedLogRecord]) -> List[AnomalyResult]:
        """
        Detects anomalies, manages history, triggers alerts, and returns detailed results.
        """
        if not parsed_logs:
            return []

        # --- Rule-Based Anomaly Detection ---
        anomalies: Dict[str, AnomalyResult] = {}
        logs_for_model_check: List[ParsedLogRecord] = []

        for log in parsed_logs:
            is_rule_anomaly = False
            # Check for service-specific rules first, then fall back to default
            service_rules = self.alert_conditions.get(log.service, {})
            default_rules = self.alert_conditions.get("__default__", {})
            
            # Combine service and default rules, with service rules taking precedence
            effective_rules = {**default_rules, **service_rules}

            for key, threshold in effective_rules.items():
                log_value = log.features.get(key)
                if log_value is not None and isinstance(log_value, (int, float)) and log_value > threshold:
                    anomaly = AnomalyResult(
                        timestamp=log.timestamp,
                        service=log.service,
                        source=log.source,
                        log_level=log.log_level or "unknown",
                        message=f"Rule violation: {key} ({log_value}) > {threshold}",
                        anomaly_score=1.0,  # Max score for rule violations
                        rule_violation=True,
                        features={},
                        raw_log=log.raw_log,
                        metadata={"violated_rule": key, "threshold": threshold, "actual_value": log_value},
                        context={},
                    )
                    anomalies[log.raw_log] = anomaly
                    is_rule_anomaly = True
                    break  # Move to the next log once a rule is violated
            
            if not is_rule_anomaly:
                logs_for_model_check.append(log)

        # --- Model-Based Anomaly Detection ---
        if logs_for_model_check:
            log_features = self.log_parser.get_feature_vectors(
                logs_for_model_check, self.model_service.feature_names
            )

            if log_features.size > 0:
                predictions, scores = self.model_service.predict(log_features)

                for i, (prediction, score) in enumerate(zip(predictions, scores)):
                    # Anomaly if prediction is -1 AND score is below the configured threshold
                    if prediction == -1 and score < getattr(self, 'anomaly_threshold', settings.anomaly_threshold):
                        log = logs_for_model_check[i]
                        current_log_features = log_features[i]
                        anomaly = AnomalyResult(
                            timestamp=log.timestamp,
                            service=log.service,
                            source=log.source,
                            log_level=log.log_level or "unknown",
                            message=log.message or "",
                            anomaly_score=score,
                            rule_violation=False,
                            features=dict(zip(self.model_service.feature_names, current_log_features)),
                            raw_log=log.raw_log,
                            metadata={},
                            context={},
                        )
                        anomalies[log.raw_log] = anomaly

        # --- Finalize and Alert ---
        final_anomalies = list(anomalies.values())
        if final_anomalies:
            self.anomaly_history.extend(final_anomalies)
            self._persist_anomalies()
            
            # Only trigger complex, rate-based alerts to reduce noise.
            # Individual alerts are detected and stored but will not be sent.
            self._check_rate_based_alerts(final_anomalies)

            logger.info(f"Detected and stored {len(final_anomalies)} new anomalies.")

        return final_anomalies

    def _check_rate_based_alerts(self, new_anomalies: List[AnomalyResult]) -> set:
        """
        Checks for and triggers alerts based on anomaly frequency.
        Returns a set of service names for which a high-rate alert was triggered.
        """
        if not self.complex_alert_rules:
            return set()

        triggered_services = set()
        for anomaly in new_anomalies:
            service = anomaly.service
            
            # Get the rule for the current service, falling back to default
            rule = self.complex_alert_rules.get(service, self.complex_alert_rules.get("__default__"))
            if not rule:
                continue

            # Ensure the anomaly timestamp is timezone-aware for correct comparisons
            anomaly_ts = anomaly.timestamp
            if anomaly_ts.tzinfo is None:
                anomaly_ts = anomaly_ts.replace(tzinfo=timezone.utc)

            # Add current anomaly's timestamp to the service's history
            timestamps = self.service_anomaly_timestamps[service]
            timestamps.append(anomaly_ts)

            # Remove timestamps that are outside the rule's time window
            window_start = anomaly_ts - timedelta(seconds=rule["window_seconds"])
            while timestamps and timestamps[0] < window_start:
                timestamps.popleft()
            
            logger.debug(f"Service '{service}' anomaly count: {len(timestamps)} within window. Rule requires: {rule.get('count')}.")

            # Check if the number of anomalies in the window exceeds the count
            if len(timestamps) >= rule["count"]:
                self.alert_manager.send_alert(
                    message=f"High Anomaly Rate Detected for service: {service}",
                    details={
                        "service": service,
                        "rule_violated": rule,
                        "anomaly_count_in_window": len(timestamps),
                        "time_window_seconds": rule["window_seconds"],
                        "last_anomaly_timestamp": anomaly.timestamp.isoformat()
                    },
                    alert_type="high_anomaly_rate" # Custom type for routing
                )
                # Clear the history for this service to prevent immediate re-alerting
                self.service_anomaly_timestamps[service].clear()
                triggered_services.add(service)
                logger.warning(f"High anomaly rate alert triggered for service '{service}'. "
                               f"Count: {len(timestamps)} in {rule['window_seconds']}s.")
        return triggered_services

    def get_recent_anomalies(self, limit: int = 100) -> List[AnomalyResult]:
        """
        Returns a list of the most recent anomalies from the global history,
        sorted by anomaly score (most anomalous first).
        """
        # Take a snapshot of the deque for safe sorting
        anomalies_snapshot = list(self.anomaly_history)
        # Sort by score (ascending, since lower is more anomalous) and then by timestamp
        sorted_anomalies = sorted(anomalies_snapshot, key=lambda r: (r.anomaly_score, r.timestamp), reverse=False)
        return sorted_anomalies[:limit]

    def get_anomaly_stats(self) -> Dict[str, Any]:
        """Computes statistics over the global anomaly history."""
        if not self.anomaly_history:
            return {"total": 0, "avg_score": 0.0}
        
        scores = [anomaly.anomaly_score for anomaly in self.anomaly_history]
        return {
            "total": len(scores),
            "avg_score": sum(scores) / len(scores),
        }

    def clear_anomalies(self):
        """Clears all anomaly history and deletes the persisted file."""
        with self._storage_lock:
            self.anomaly_history.clear()
            if self._storage_path.exists():
                self._storage_path.unlink()
            logger.info("Cleared all anomaly records and persistence file.")

    def is_healthy(self) -> bool:
        """Check if the model is loaded."""
        return self.model_service.is_healthy()


# --- Dependency Injection ---

_ad_service_instance: Optional[AnomalyDetectionService] = None
_ad_service_lock = threading.Lock()

def get_anomaly_detection_service() -> AnomalyDetectionService:
    """Dependency injector for the anomaly detection service."""
    global _ad_service_instance
    if _ad_service_instance is None:
        with _ad_service_lock:
            if _ad_service_instance is None:
                # Manually get dependencies; in a larger app, FastAPI could inject these too
                model_serv = get_model_service()
                log_parser = log_parser_service
                alert_man = alert_manager
                _ad_service_instance = AnomalyDetectionService(model_serv, log_parser, alert_man)
    return _ad_service_instance 