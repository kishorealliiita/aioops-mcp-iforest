from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.models import AnomalyResult, ParsedLogRecord
from app.services.anomaly_detection_service import AnomalyDetectionService, get_anomaly_detection_service
from app.services.feedback_service import FeedbackService, get_feedback_service
from app.services.model_service import ModelService, get_model_service

client = TestClient(app)


@pytest.fixture
def mock_ad_service():
    return MagicMock(spec=AnomalyDetectionService)


@pytest.fixture
def mock_model_service():
    return MagicMock(spec=ModelService)


@pytest.fixture
def mock_feedback_service():
    return MagicMock(spec=FeedbackService)


@pytest.fixture(autouse=True)
def setup_dependencies(mock_ad_service, mock_model_service, mock_feedback_service):
    """Override dependencies and reset mocks for each test."""
    mock_ad_service.reset_mock()
    mock_model_service.reset_mock()
    mock_feedback_service.reset_mock()

    app.dependency_overrides[get_anomaly_detection_service] = lambda: mock_ad_service
    app.dependency_overrides[get_model_service] = lambda: mock_model_service
    app.dependency_overrides[get_feedback_service] = lambda: mock_feedback_service

    yield

    app.dependency_overrides.clear()


@patch("app.api.routes.log_parser_service")
def test_stream_multi_source_success(mock_log_parser, mock_ad_service):
    """Test the streaming endpoint with a successful case."""
    raw_log = {"raw_log": "log1", "service": "s1", "source": "src1", "format_type": "json"}
    parsed_log = ParsedLogRecord(raw_log="log1", service="s1", source="src1", timestamp=datetime.now(), features={})
    anomaly = AnomalyResult(
        raw_log="log1",
        service="s1",
        source="src1",
        timestamp=datetime.now(),
        anomaly_score=-0.9,
        log_level="error",
        message="",
        rule_violation=False,
        features={},
        metadata={},
        context={},
    )

    mock_log_parser.parse_logs.return_value = [parsed_log]
    mock_ad_service.detect_and_store_anomalies.return_value = [anomaly]

    response = client.post("/api/v1/stream/multi-source", json={"logs": [raw_log]})

    assert response.status_code == 200
    data = response.json()
    assert data[0]["is_anomaly"] == 1


def test_get_anomalies(mock_ad_service):
    """Test retrieving anomaly records."""
    mock_ad_service.get_recent_anomalies.return_value = []

    response = client.get("/api/v1/anomalies")

    assert response.status_code == 200
    assert response.json() == []
    mock_ad_service.get_recent_anomalies.assert_called_once_with(100)


def test_clear_anomalies(mock_ad_service):
    """Test clearing all anomaly records."""
    response = client.delete("/api/v1/anomalies")
    assert response.status_code == 200
    mock_ad_service.clear_anomalies.assert_called_once()


def test_train_model(mock_model_service):
    response = client.post(
        "/api/v1/train", json={"logs": [{"raw_log": "log", "service": "s", "source": "s", "format_type": "json"}]}
    )
    assert response.status_code == 202
    assert "started in the background" in response.json()["message"]
    # The actual task execution is not tested here, just that the route works


def test_submit_feedback(mock_feedback_service):
    feedback_data = {
        "feedback": [{"log": {"raw_log": "log", "service": "s", "source": "s", "format_type": "json"}, "is_anomaly": 1}]
    }
    response = client.post("/api/v1/feedback", json=feedback_data)
    assert response.status_code == 202
    assert "Feedback received" in response.json()["message"]
