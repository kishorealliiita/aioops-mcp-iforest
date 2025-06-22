from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from enum import Enum

from app.schemas.enums import LogFormat


class LogRecord(BaseModel):
    """Base log record schema."""
    resp_time: float = Field(..., description="Response time in milliseconds")
    bytes_out: int = Field(..., description="Bytes transferred")
    error_rate: float = Field(..., description="Error rate percentage")
    
    class Config:
        schema_extra = {
            "example": {
                "resp_time": 150.5,
                "bytes_out": 1024,
                "error_rate": 0.02
            }
        }


class RawLogRecord(BaseModel):
    """Raw log record from any source."""
    raw_log: str = Field(..., description="Raw log line")
    service: str = Field(..., description="Service name (e.g., web_server, database)")
    source: str = Field(..., description="Log source identifier")
    format_type: LogFormat = Field(..., description="Log format type")
    custom_config: Optional[Dict[str, Any]] = Field(default=None, description="Custom parsing configuration")


class MultiSourcePredictRequest(BaseModel):
    """Request schema for multi-source log prediction."""
    logs: List[RawLogRecord] = Field(..., description="List of raw log records from different sources")
    
    class Config:
        schema_extra = {
            "example": {
                "logs": [
                    {
                        "raw_log": '{"timestamp": "2024-01-01T10:00:00Z", "level": "ERROR", "message": "Database connection failed", "response_time": 5000}',
                        "service": "web_server",
                        "source": "nginx",
                        "format_type": "json"
                    },
                    {
                        "raw_log": "2024-01-01T10:00:01Z ERROR query_time=5000ms connection_count=100 error_rate=0.15",
                        "service": "database", 
                        "source": "postgresql",
                        "format_type": "key_value"
                    }
                ]
            }
        }


class TrainRequest(BaseModel):
    """Request schema for model training."""
    logs: List[Dict[str, Any]] = Field(..., description="Training data logs")
    
    class Config:
        schema_extra = {
            "example": {
                "logs": [
                    {"resp_time": 150.5, "bytes_out": 1024, "error_rate": 0.02},
                    {"resp_time": 200.0, "bytes_out": 2048, "error_rate": 0.05}
                ]
            }
        }


class MultiSourceTrainRequest(BaseModel):
    """Request schema for multi-source model training."""
    logs: List[RawLogRecord] = Field(..., description="Training data from different sources")
    
    class Config:
        schema_extra = {
            "example": {
                "logs": [
                    {
                        "raw_log": '{"timestamp": "2024-01-01T10:00:00Z", "level": "INFO", "message": "Request processed", "response_time": 150}',
                        "service": "web_server",
                        "source": "nginx",
                        "format_type": "json"
                    }
                ]
            }
        }


class FeedbackRecord(BaseModel):
    """Schema for a single feedback item, linking a log to a label."""
    log: RawLogRecord
    is_anomaly: int = Field(..., description="User-provided label (1=anomaly, 0=normal)", ge=0, le=1)


class FeedbackRequest(BaseModel):
    """Request schema for submitting feedback."""
    feedback: List[FeedbackRecord]

    class Config:
        schema_extra = {
            "example": {
                "feedback": [
                    {
                        "log": {
                            "raw_log": "2024-01-01T10:05:00Z ERROR query_time=15000ms connection_count=900",
                            "service": "database",
                            "source": "postgresql",
                            "format_type": "key_value"
                        },
                        "is_anomaly": 1
                    },
                    {
                        "log": {
                            "raw_log": "{\"timestamp\": \"2024-01-01T10:06:00Z\", \"level\": \"INFO\", \"response_time\": 200}",
                            "service": "web_server",
                            "source": "nginx",
                            "format_type": "json"
                        },
                        "is_anomaly": 0
                    }
                ]
            }
        }


class MultiSourceStreamRequest(BaseModel):
    """Request schema for multi-source streaming analysis."""
    logs: List[RawLogRecord] = Field(..., description="Raw log records to stream")
    tags: Dict[str, str] = Field(default={}, description="Optional metadata tags")


class StreamResult(BaseModel):
    """Result schema for streaming analysis."""
    score: float = Field(..., description="Anomaly score")
    is_anomaly: int = Field(..., description="Anomaly prediction (0=normal, 1=anomaly)")


class PredictionResult(BaseModel):
    """Result schema for batch prediction."""
    score: float = Field(..., description="Anomaly score")
    is_anomaly: int = Field(..., description="Anomaly prediction (0=normal, 1=anomaly)")


class AnomalyResult(BaseModel):
    """Enhanced anomaly result schema."""
    timestamp: datetime = Field(..., description="When the anomaly was detected")
    service: str = Field(..., description="Service name")
    source: str = Field(..., description="Log source")
    log_level: str = Field(..., description="Log level")
    message: str = Field(..., description="Log message")
    anomaly_score: float = Field(..., description="Anomaly score")
    rule_violation: bool = Field(..., description="Whether rule-based detection triggered")
    features: Dict[str, Union[int, float, str]] = Field(..., description="Extracted features")
    raw_log: str = Field(..., description="Original raw log")
    metadata: Dict[str, Any] = Field(..., description="Additional metadata")
    context: Dict[str, Any] = Field(..., description="Detection context")


class AnomalyContext(BaseModel):
    """Holds the contextual state for a service's anomaly detection."""
    baseline_features: Optional[List[Dict[str, Any]]] = Field(default=None, description="Baseline feature set for the service")
    last_anomaly_timestamp: Optional[datetime] = Field(default=None, description="Timestamp of the last detected anomaly")


class ParsedLogRecord(BaseModel):
    """Represents a log after parsing, with extracted features."""
    raw_log: str
    service: str
    source: str
    timestamp: datetime
    log_level: Optional[str] = "unknown"
    message: Optional[str] = ""
    features: Dict[str, Union[int, float, str]]


class AnomalyRecord(BaseModel):
    """Schema for anomaly records."""
    timestamp: datetime = Field(..., description="When the anomaly was detected")
    score: float = Field(..., description="Anomaly score")
    log_data: Dict[str, Any] = Field(..., description="Original log data")
    tags: Optional[Dict[str, str]] = Field(default=None, description="Associated tags")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = Field(default="1.0.0")


class MetricsResponse(BaseModel):
    """Metrics response."""
    prediction_count: int = Field(..., description="Total predictions made")
    anomaly_count: int = Field(..., description="Total anomalies detected")
    last_trained: Optional[datetime] = Field(None, description="Last training timestamp")
    feedback_received: int = Field(..., description="Total feedback received")
    model_accuracy: Optional[float] = Field(None, description="Model accuracy if available")


class ServiceMetricsResponse(BaseModel):
    """Service-specific metrics response."""
    service: str = Field(..., description="Service name")
    total_anomalies: int = Field(..., description="Total anomalies for this service")
    avg_score: float = Field(..., description="Average anomaly score")
    recent_anomalies: int = Field(..., description="Anomalies in the last hour")
    max_score: float = Field(..., description="Most anomalous score")
    min_score: float = Field(..., description="Least anomalous score")


class ServiceConfig(BaseModel):
    """Service configuration schema."""
    service: str = Field(..., description="Service name")
    critical_features: List[str] = Field(..., description="Critical features for this service")
    baseline_window_hours: int = Field(..., description="Baseline window in hours")
    anomaly_threshold: float = Field(..., description="Anomaly detection threshold")
    alert_threshold: float = Field(..., description="Alert triggering threshold")


class LogFormatConfig(BaseModel):
    """Log format configuration schema."""
    format_type: LogFormat = Field(..., description="Log format type")
    pattern: Optional[str] = Field(None, description="Regex pattern for regex format")
    field_mapping: Optional[Dict[str, str]] = Field(None, description="Field mapping for regex format")
    custom_parser: Optional[str] = Field(None, description="Custom parser function name") 