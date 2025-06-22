import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest

from app.config import settings
from app.schemas.models import RawLogRecord
from app.services.log_parser_service import LogParserService, log_parser_service
from app.utils.logger import setup_logger

logger = setup_logger("model_service")


class ModelService:
    """
    Manages the machine learning model, including training, prediction, and persistence.
    """

    def __init__(self, log_parser: LogParserService):
        self.model_path = settings.model_path
        self._model_instance: Optional[IsolationForest] = None
        self._model_lock = threading.Lock()
        self.log_parser = log_parser

        self.prediction_count = 0
        self.feedback_received = 0
        self.metrics = {
            "prediction_count": 0,
            "anomaly_count": 0,
            "feedback_received": 0,
            "last_trained": None,
        }
        self.feature_names_internal = settings.feature_names.copy()

        # Ensure models directory exists
        Path(self.model_path).parent.mkdir(parents=True, exist_ok=True)

        self._model_instance = self._load_model()
        if not self._model_instance:
            self._train_initial_model()

    @property
    def feature_names(self) -> List[str]:
        """Returns the list of feature names used by the model."""
        return self.feature_names_internal

    @property
    def model(self):
        """Lazy-loads the model on first access to ensure it's not loaded on import."""
        if self._model_instance is None:
            with self._model_lock:
                # Double-check locking to prevent re-initialization
                if self._model_instance is None:
                    self._load_or_initialize_model()
        return self._model_instance

    def _load_or_initialize_model(self):
        """Loads the model from disk or creates a new one if it doesn't exist."""
        os.makedirs(os.path.dirname(settings.model_path), exist_ok=True)
        try:
            # Also catch EOFError in case the file is corrupted/empty
            self._model_instance = joblib.load(settings.model_path)
            logger.info(f"Loaded existing model from {settings.model_path}")
        except (FileNotFoundError, EOFError):
            logger.info("No valid model found. Initializing and training a dummy model.")
            dummy_features = np.random.rand(100, settings.default_feature_dim) * 100
            model = IsolationForest(contamination=settings.model_contamination, random_state=settings.model_random_state)
            model.fit(dummy_features)
            self._model_instance = model
            self.save_model(self._model_instance)

    def _save_model(self):
        """Save the current model to disk."""
        try:
            joblib.dump(self.model, settings.model_path)
            logger.info(f"Model saved to {settings.model_path}")
        except Exception as e:
            logger.error(f"Failed to save model: {e}")

    def extract_features(self, logs: List[Dict[str, Any]]) -> np.ndarray:
        """Extract features from log data."""
        features = []
        for log in logs:
            feature_vector = []
            for column in settings.feature_columns:
                value = log.get(column, 0)
                try:
                    feature_vector.append(float(value))
                except (ValueError, TypeError):
                    feature_vector.append(0.0)
            features.append(feature_vector)
        return np.array(features)

    def predict(self, logs: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """
        Predicts anomalies using the loaded Isolation Forest model.
        Returns both the predictions (-1 for anomaly, 1 for normal) and the raw scores.
        """
        if self.model is None:
            raise RuntimeError("Model is not loaded. Train a model before predicting.")

        if logs.size == 0:
            return np.array([]), np.array([])

        try:
            scores = self.model.decision_function(logs)
            predictions = self.model.predict(logs)

        except Exception as e:
            logger.error(f"An error occurred during prediction: {e}", exc_info=True)
            return np.array([]), np.array([])

        # Update metrics
        self.metrics["prediction_count"] += len(predictions)
        self.metrics["anomaly_count"] += np.sum(predictions == -1)

        return predictions, scores

    def train(self, logs: List[Dict[str, Any]]) -> bool:
        """Train the model on new data."""
        if not logs or len(logs) < 10:
            logger.warning("Insufficient data for training (need at least 10 records)")
            return False

        features = self.extract_features(logs)

        with self._model_lock:
            self.model = IsolationForest(contamination=settings.model_contamination, random_state=settings.model_random_state)
            self.model.fit(features)
            self.metrics["last_trained"] = datetime.utcnow()

        self._save_model()
        logger.info(f"Model retrained on {len(logs)} records")
        return True

    def get_metrics(self) -> Dict[str, Any]:
        """Get model metrics."""
        return {
            "prediction_count": int(self.metrics["prediction_count"]),
            "anomaly_count": int(self.metrics["anomaly_count"]),
            "last_trained": self.metrics["last_trained"].isoformat() if self.metrics["last_trained"] else None,
            "feedback_received": int(self.metrics["feedback_received"]),
            "model_path": settings.model_path,
            "contamination": float(settings.model_contamination),
        }

    def is_healthy(self) -> bool:
        """Check if the model instance is loaded."""
        try:
            return self.model is not None
        except Exception:
            return False

    def _load_model(self):
        """Load the model from disk."""
        try:
            model = joblib.load(settings.model_path)
            logger.info(f"Loaded model from {settings.model_path}")
            return model
        except FileNotFoundError:
            logger.warning(f"Model file not found at {settings.model_path}. An initial model will be trained.")
            return None
        except Exception as e:
            logger.error(f"Error loading model: {e}", exc_info=True)
            return None

    def _train_initial_model(self):
        """Trains and saves an initial dummy model if none exists."""
        logger.info("Training initial dummy model...")
        with self._model_lock:
            # Create a dummy model
            dummy_features = np.random.rand(100, 3)  # Example: 100 samples, 3 features
            self._model_instance = IsolationForest(
                n_estimators=settings.iforest_n_estimators,
                contamination=settings.iforest_contamination,
                random_state=settings.random_state,
            )
            self._model_instance.fit(dummy_features)
            self._save_model()
            logger.info(f"Initial dummy model trained and saved to {self.model_path}")

    def retrain_model(self, logs: List[RawLogRecord]):
        """
        Asynchronously retrains the model with new data.
        It uses the log_parser instance provided during its own initialization.
        """
        logger.info(f"Starting model retraining with {len(logs)} log records.")
        try:
            # 1. Parse logs
            parsed_logs = self.log_parser.parse_logs(logs)
            if not parsed_logs:
                logger.warning("No logs could be parsed. Aborting training.")
                return

            # 2. Extract features
            features = self.log_parser.get_feature_vectors(parsed_logs, self.feature_names)

            if features.size == 0:
                logger.warning("No features could be extracted from parsed logs. Aborting training.")
                return

            if features.shape[0] < settings.min_train_samples:
                logger.warning(
                    f"Not enough samples ({features.shape[0]}) to retrain. Minimum is {settings.min_train_samples}."
                )
                return

            # 3. Retrain the model in a background thread to avoid blocking
            with self._model_lock:
                logger.info("Training new Isolation Forest model...")
                new_model = IsolationForest(
                    contamination=settings.model_contamination,
                    random_state=settings.model_random_state,
                )
                new_model.fit(features)
                self._model_instance = new_model

            self._save_model()
            logger.info("Model retraining complete.")

        except Exception as e:
            logger.error(f"An error occurred during model retraining: {e}", exc_info=True)

    def save_model(self, model):
        """Save the model to disk."""
        try:
            joblib.dump(model, settings.model_path)
            logger.info(f"Model saved to {settings.model_path}")
        except Exception as e:
            logger.error(f"Failed to save model: {e}")


# A "private" global instance to be managed by the dependency injector
_model_service_instance: Optional[ModelService] = None
_model_service_lock = threading.Lock()


def get_model_service() -> ModelService:
    """
    Dependency injector for the ModelService.

    Ensures that a single instance of the service is created and reused.
    """
    global _model_service_instance
    if _model_service_instance is None:
        with _model_service_lock:
            if _model_service_instance is None:
                _model_service_instance = ModelService(log_parser=log_parser_service)
    return _model_service_instance
