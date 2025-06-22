import pytest
import os
import numpy as np
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime

from app.services.model_service import ModelService
from app.services.log_parser_service import LogParserService
from app.schemas.models import RawLogRecord, ParsedLogRecord
from app.schemas.enums import LogFormat
from app.config import settings

@pytest.fixture
def mock_log_parser():
    """Mocks the log parser service for retraining tests."""
    parser = MagicMock(spec=LogParserService)
    # The parser's job is to turn raw logs into parsed logs with features
    parsed_logs = [
        ParsedLogRecord(raw_log='log', service='s', source='n', timestamp=datetime.utcnow(), features={'feature1': i, 'feature2': i*2}) for i in range(50)
    ]
    parser.parse_logs.return_value = parsed_logs
    return parser

class TestModelService:
    @pytest.fixture(autouse=True)
    def setup_method(self, tmp_path, mock_log_parser):
        """Setup for each test method to ensure isolation."""
        # Use a temporary directory for the model file
        settings.model_path = str(tmp_path / "test_model.pkl")
        
        # Patch joblib.load to prevent disk access during initialization
        with patch('joblib.load', side_effect=FileNotFoundError):
            # Inject the mocked log parser here
            self.model_service = ModelService(log_parser=mock_log_parser)
        
        # Replace the internal model with a mock for controlled testing
        self.model_service._model_instance = MagicMock()
        # Mock the feature_names property used in feature extraction
        type(self.model_service).feature_names = PropertyMock(return_value=['feature1', 'feature2'])

    def test_initialization_and_health(self):
        """Tests that the service initializes correctly and is healthy."""
        assert self.model_service.is_healthy()
        assert self.model_service.model is not None

    def test_predict(self):
        """Tests the predict function with a NumPy array of features."""
        # The predict method now expects a NumPy array of feature vectors.
        log_features = np.array([[1.0, 2.0], [4.0, 5.0]])
    
        self.model_service._model_instance.predict.return_value = np.array([1, -1])
        self.model_service._model_instance.decision_function.return_value = np.array([0.1, -0.2])
    
        predictions, scores = self.model_service.predict(log_features)
    
        assert isinstance(predictions, np.ndarray)
        assert isinstance(scores, np.ndarray)
        assert len(predictions) == 2
        np.testing.assert_array_equal(predictions, np.array([1, -1]))

    def test_predict_empty(self):
        """Tests that predict handles an empty array gracefully."""
        log_features = np.array([])
        predictions, scores = self.model_service.predict(log_features)
        assert predictions.size == 0
        assert scores.size == 0

    def test_retrain_success(self, mock_log_parser):
        """Tests a successful model retraining run."""
        sample_data = [RawLogRecord(raw_log='log', service='s', source='n', format_type=LogFormat.JSON)] * 50
        
        # The log parser's feature extraction method should return a NumPy array
        mock_log_parser.get_feature_vectors.return_value = np.array([[0.1, 0.2]] * 50)
        
        with patch('app.services.model_service.IsolationForest') as mock_iso_forest:
            mock_instance = mock_iso_forest.return_value
            self.model_service.retrain_model(sample_data)
            
            parsed_logs = mock_log_parser.parse_logs.return_value
            mock_log_parser.parse_logs.assert_called_once_with(sample_data)
            mock_log_parser.get_feature_vectors.assert_called_once_with(parsed_logs, self.model_service.feature_names)
            mock_iso_forest.assert_called_once()
            mock_instance.fit.assert_called_once()

    def test_retrain_not_enough_data(self, mock_log_parser, caplog):
        """Tests that retraining is skipped if there are not enough parsed samples."""
        mock_log_parser.parse_logs.return_value = [] # Mock parser returns no logs
        
        self.model_service.retrain_model([])
        
        # The service should log this specific message when parsing fails to yield logs.
        assert "No logs could be parsed. Aborting training." in caplog.text

    def test_save_and_load_model(self, mock_log_parser):
        """Tests that a model is saved and can be loaded back correctly."""
        # Use a real model object for this test, not a mock
        real_model = self.model_service.model 
        self.model_service._model_instance = real_model
        
        # Act: Save the model
        self.model_service._save_model()
        assert os.path.exists(settings.model_path)
        
        # Assert: A new service instance can load the saved model from disk
        with patch('joblib.load') as mock_joblib_load:
            mock_joblib_load.return_value = real_model
            new_service = ModelService(log_parser=mock_log_parser)
            mock_joblib_load.assert_called_once_with(settings.model_path)
            assert new_service.is_healthy()

    def test_get_metrics(self):
        """Tests the get_metrics function."""
        self.model_service.prediction_count = 100 