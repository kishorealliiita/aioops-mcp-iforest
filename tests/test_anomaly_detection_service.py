from datetime import datetime, timezone
from typing import List
from unittest.mock import Mock, PropertyMock, patch

import numpy as np
import pytest

from app.alerts.alert_manager import AlertManager
from app.schemas.models import ParsedLogRecord
from app.services.anomaly_detection_service import AnomalyDetectionService
from app.services.log_parser_service import LogParserService
from app.services.model_service import ModelService


@pytest.fixture
def mock_model_service():
    """Mocks the ModelService with a feature_names property."""
    service = Mock(spec=ModelService)
    type(service).feature_names = PropertyMock(return_value=["feature1", "feature2"])
    return service


@pytest.fixture
def mock_log_parser():
    """Mocks the LogParserService and its feature extraction method."""
    parser = Mock(spec=LogParserService)
    # This method must be mocked to return features for the model service to predict on.
    parser.get_feature_vectors.return_value = np.array([[10, 20], [100, 200]])
    return parser


@pytest.fixture
def mock_alert_manager():
    """Mocks the AlertManager."""
    manager = Mock(spec=AlertManager)
    manager.send_alert = Mock()
    return manager


@pytest.fixture
def mock_get_alert_conditions():
    """Mocks the get_alert_conditions function to return an empty dict."""
    with patch("app.services.anomaly_detection_service.get_alert_conditions") as mock:
        mock.return_value = {}
        yield mock


@pytest.fixture
def anomaly_detection_service(mock_model_service, mock_log_parser, mock_alert_manager, mock_get_alert_conditions):
    """Provides a fully mocked AnomalyDetectionService instance."""
    return AnomalyDetectionService(
        model_service=mock_model_service, log_parser=mock_log_parser, alert_manager=mock_alert_manager
    )


@pytest.fixture
def sample_parsed_logs() -> List[ParsedLogRecord]:
    """Provides sample parsed log data."""
    return [
        ParsedLogRecord(
            raw_log="log1", service="s1", source="src1", timestamp=datetime.now(), features={"feature1": 10, "feature2": 20}
        ),
        ParsedLogRecord(
            raw_log="log2", service="s2", source="src2", timestamp=datetime.now(), features={"feature1": 100, "feature2": 200}
        ),
    ]


def test_detect_no_anomalies(anomaly_detection_service, sample_parsed_logs):
    """Test that no anomalies are returned when model predictions are normal."""
    model_service = anomaly_detection_service.model_service
    model_service.predict.return_value = (np.array([1, 1]), np.array([0.1, 0.1]))  # Normal

    results = anomaly_detection_service.detect_and_store_anomalies(sample_parsed_logs)

    model_service.predict.assert_called_once()
    assert len(results) == 0


def test_detect_and_alert_on_model_anomaly(anomaly_detection_service, sample_parsed_logs):
    """Test that anomalies are detected via the ML model."""
    model_service = anomaly_detection_service.model_service
    model_service.predict.return_value = (np.array([-1, 1]), np.array([-0.6, 0.1]))  # Anomaly

    results = anomaly_detection_service.detect_and_store_anomalies(sample_parsed_logs)

    assert len(results) == 1
    assert not results[0].rule_violation
    # Individual alerts are no longer sent, only rate-based ones.


def test_detect_service_specific_rule_anomaly(
    mock_model_service, mock_log_parser, mock_alert_manager, mock_get_alert_conditions
):
    """Test that a service-specific rule is triggered correctly."""
    # Arrange
    mock_get_alert_conditions.return_value = {"web_server": {"response_time": 500}, "__default__": {"response_time": 2000}}
    service = AnomalyDetectionService(mock_model_service, mock_log_parser, mock_alert_manager)

    # This log should violate the 'web_server' specific rule
    violating_log = ParsedLogRecord(
        raw_log="web_server_log",
        service="web_server",
        source="nginx",
        timestamp=datetime.now(),
        features={"response_time": 600},
    )

    # Act
    results = service.detect_and_store_anomalies([violating_log])

    # Assert
    assert len(results) == 1
    assert results[0].rule_violation is True
    assert results[0].service == "web_server"
    assert "response_time" in results[0].message
    mock_model_service.predict.assert_not_called()
    # No individual alert is sent
    mock_alert_manager.send_alert.assert_not_called()


def test_detect_default_rule_anomaly(mock_model_service, mock_log_parser, mock_alert_manager, mock_get_alert_conditions):
    """Test that a default rule is triggered when no service-specific rule matches."""
    # Arrange
    mock_get_alert_conditions.return_value = {"web_server": {"response_time": 1000}, "__default__": {"cpu_usage": 90}}
    service = AnomalyDetectionService(mock_model_service, mock_log_parser, mock_alert_manager)

    # This log from 'database' has no specific rule, so it should use the default.
    violating_log = ParsedLogRecord(
        raw_log="db_log",
        service="database",
        source="postgres",
        timestamp=datetime.now(),
        features={"cpu_usage": 95, "response_time": 200},
    )

    # Act
    results = service.detect_and_store_anomalies([violating_log])

    # Assert
    assert len(results) == 1
    assert results[0].rule_violation is True
    assert results[0].service == "database"
    assert "cpu_usage" in results[0].message
    mock_model_service.predict.assert_not_called()
    # No individual alert is sent
    mock_alert_manager.send_alert.assert_not_called()


def test_no_rule_violation(mock_model_service, mock_log_parser, mock_alert_manager, mock_get_alert_conditions):
    """Test that no rule is triggered when values are within thresholds."""
    # Arrange
    mock_get_alert_conditions.return_value = {"web_server": {"response_time": 500}, "__default__": {"cpu_usage": 90}}
    service = AnomalyDetectionService(mock_model_service, mock_log_parser, mock_alert_manager)

    # This log is within all defined thresholds
    normal_log = ParsedLogRecord(
        raw_log="normal_log",
        service="web_server",
        source="nginx",
        timestamp=datetime.now(),
        features={"response_time": 450, "cpu_usage": 80},
    )

    # Model should predict this as normal
    mock_model_service.predict.return_value = (np.array([1]), np.array([0.2]))
    mock_log_parser.get_feature_vectors.return_value = np.array([[450, 80]])

    # Act
    results = service.detect_and_store_anomalies([normal_log])

    # Assert
    assert len(results) == 0
    mock_model_service.predict.assert_called_once()


def test_rate_based_alerts_are_checked(mock_model_service, mock_log_parser, mock_alert_manager, mock_get_alert_conditions):
    """Test that the rate-based alert checker is called when anomalies are detected."""
    # Arrange
    mock_get_alert_conditions.return_value = {}
    service = AnomalyDetectionService(mock_model_service, mock_log_parser, mock_alert_manager)

    logs_to_process = [
        ParsedLogRecord(
            service="web_server", source="nginx", timestamp=datetime.now(timezone.utc), raw_log="1", features={"f1": 1}
        ),
    ]

    mock_model_service.predict.return_value = (np.array([-1]), np.array([-0.6]))
    mock_log_parser.get_feature_vectors.return_value = np.array([[1]])

    service._check_rate_based_alerts = Mock()

    # Act
    service.detect_and_store_anomalies(logs_to_process)

    # Assert
    service._check_rate_based_alerts.assert_called_once()
    mock_alert_manager.send_alert.assert_not_called()


def test_empty_log_list(anomaly_detection_service):
    """Test that the service handles an empty list of logs gracefully."""
    results = anomaly_detection_service.detect_and_store_anomalies([])
    assert len(results) == 0
    anomaly_detection_service.model_service.predict.assert_not_called()


def test_anomaly_storage_and_retrieval(
    anomaly_detection_service: AnomalyDetectionService, sample_parsed_logs: List[ParsedLogRecord]
):
    """Test that anomalies are stored and can be retrieved."""
    # Arrange
    anomaly_detection_service.clear_anomalies()  # Ensure a clean state
    model_service = anomaly_detection_service.model_service
    model_service.predict.return_value = (np.array([-1, -1]), np.array([-0.7, -0.8]))

    # Act
    anomaly_detection_service.detect_and_store_anomalies(sample_parsed_logs)

    # Assert
    stored_anomalies = anomaly_detection_service.get_recent_anomalies(10)
    assert len(stored_anomalies) == 2
    assert stored_anomalies[0].anomaly_score == -0.8  # Check order (most anomalous first)
    assert stored_anomalies[1].anomaly_score == -0.7

    # Test clearing
    anomaly_detection_service.clear_anomalies()
    assert len(anomaly_detection_service.get_recent_anomalies(10)) == 0


def test_threshold_logic(anomaly_detection_service: AnomalyDetectionService, sample_parsed_logs: List[ParsedLogRecord]):
    """Test that the anomaly threshold is respected."""
    # Arrange
    anomaly_detection_service.clear_anomalies()  # Ensure a clean state
    model_service = anomaly_detection_service.model_service
    anomaly_detection_service.anomaly_threshold = -0.75  # Make it harder to be an anomaly

    # Mock model to return scores where one is below the new threshold
    model_service.predict.return_value = (
        np.array([-1, -1]),
        np.array([-0.7, -0.8]),
    )  # Only the second one is a "true" anomaly now

    # Act
    results = anomaly_detection_service.detect_and_store_anomalies(sample_parsed_logs)

    # Assert
    assert len(results) == 1
    assert results[0].raw_log == "log2"
    assert results[0].anomaly_score == -0.8
