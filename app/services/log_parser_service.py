import re
import json
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone
from dataclasses import dataclass
import numpy as np
from dateutil.parser import parse as parse_datetime

from app.utils.logger import setup_logger
from app.schemas.enums import LogFormat
from app.config import settings
from app.schemas.models import RawLogRecord, ParsedLogRecord

logger = setup_logger("log_parser_service")


@dataclass
class ParsedLog:
    """Normalized log structure for anomaly detection."""
    timestamp: datetime
    level: str
    message: str
    service: str
    source: str
    features: Dict[str, Union[int, float, str]]
    raw_log: str
    metadata: Dict[str, Any]


class LogParserService:
    """A service for parsing logs from various formats."""

    def _normalize_timestamp(self, timestamp_str: Optional[str]) -> datetime:
        """
        Parses a timestamp string and ensures it's timezone-aware (UTC).
        If the string is naive, it's assumed to be UTC.
        If no string is provided, returns the current UTC time.
        """
        if not timestamp_str:
            return datetime.now(timezone.utc)
        
        dt = parse_datetime(timestamp_str)
        if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
            # If naive, assume UTC
            return dt.replace(tzinfo=timezone.utc)
        return dt

    def parse_logs(self, raw_logs: List[RawLogRecord]) -> List[ParsedLogRecord]:
        """Parses a list of raw logs into a structured format, skipping invalid records."""
        parsed_records = []
        for log in raw_logs:
            try:
                parser_method = self._get_parser_method(log.format_type)
                parsed_data = parser_method(log)

                if parsed_data and parsed_data.get("features"):
                    parsed_records.append(ParsedLogRecord(**parsed_data))
                else:
                    logger.debug(f"Skipping log due to no features or parsing failure: {log.raw_log}")
            except Exception as e:
                logger.error(f"Failed to parse log '{log.raw_log}': {e}", exc_info=True)
        return parsed_records

    def _get_parser_method(self, format_type: LogFormat):
        """Returns the appropriate parsing method for the given format."""
        if format_type == LogFormat.JSON:
            return self._parse_json
        if format_type == LogFormat.KEY_VALUE:
            return self._parse_key_value
        if format_type == LogFormat.REGEX:
            return self._parse_regex
        raise ValueError(f"Unsupported log format: {format_type}")

    def _extract_numeric(self, value: Any) -> Optional[Union[int, float]]:
        """Extracts a numeric value from a string, float, or int."""
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, str):
            # Find all numbers in the string (handles "500ms", "1.5s", etc.)
            numbers = re.findall(r"[-+]?\d*\.\d+|\d+", value)
            if numbers:
                return float(numbers[0])
        return None

    def _parse_json(self, log: RawLogRecord) -> Optional[Dict]:
        """Parses a JSON formatted log line."""
        try:
            data = json.loads(log.raw_log)
            features = {k: self._extract_numeric(v) for k, v in data.items() if self._extract_numeric(v) is not None}
            return {
                "raw_log": log.raw_log,
                "service": log.service,
                "source": log.source,
                "timestamp": self._normalize_timestamp(data.get("timestamp")),
                "log_level": data.get("level", "unknown"),
                "message": data.get("message", ""),
                "features": features,
            }
        except json.JSONDecodeError:
            logger.warning(f"Malformed JSON log: {log.raw_log}")
            return None

    def _parse_key_value(self, log: RawLogRecord) -> Optional[Dict]:
        """Parses a key-value formatted log line."""
        try:
            pairs = re.findall(r'(\w+)=(".*?"|[^ ]+)', log.raw_log)
            data = {k: v.strip('"') for k, v in pairs}
            features = {k: self._extract_numeric(v) for k, v in data.items() if self._extract_numeric(v) is not None}
            return {
                "raw_log": log.raw_log,
                "service": log.service,
                "source": log.source,
                "timestamp": self._normalize_timestamp(data.get("timestamp")),
                "log_level": data.get("level", "unknown"),
                "message": data.get("message", ""),
                "features": features,
            }
        except Exception:
            logger.warning(f"Could not parse key-value log: {log.raw_log}")
            return None

    def _parse_regex(self, log: RawLogRecord) -> Optional[Dict]:
        """Parses a log line using a regex pattern from custom config."""
        custom_config = log.custom_config
        if not custom_config or "pattern" not in custom_config or "field_mapping" not in custom_config:
            return None
        
        match = re.search(custom_config["pattern"], log.raw_log)
        if not match:
            return None
            
        groups = match.groups()
        data = {custom_config["field_mapping"][str(i)]: groups[i] for i in range(len(groups)) if str(i) in custom_config["field_mapping"]}

        features = {k: self._extract_numeric(v) for k, v in data.items() if self._extract_numeric(v) is not None}
        return {
            "raw_log": log.raw_log,
            "service": log.service,
            "source": log.source,
            "timestamp": self._normalize_timestamp(data.get("timestamp")),
            "log_level": data.get("level", "unknown"),
            "message": data.get("message", ""),
            "features": features,
        }

    def _parse_custom(self, raw_log: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Parse logs using custom parsing logic."""
        if not config or 'parser_function' not in config:
            raise ValueError("Custom parser function required")
        
        # This would be a user-defined function
        parser_func = config['parser_function']
        return parser_func(raw_log)
    
    def _extract_features(self, raw_log: str, parsed_data: Dict[str, Any], format_type: LogFormat) -> Dict[str, Union[int, float, str]]:
        """Extract numerical features for anomaly detection, aware of the log format."""
        features = {}
        source_data = parsed_data.get('metadata', {})

        # --- Priority 1: Extract from parsed structured data (JSON/Key-Value) ---
        if format_type in [LogFormat.JSON, LogFormat.KEY_VALUE] and source_data:
            # Standardize common keys (e.g., resp_time, response_time -> response_time)
            key_aliases = {
                'response_time': ['response_time', 'resp_time', 'duration_ms'],
                'http_status': ['http_status', 'status_code', 'status'],
                'bytes': ['bytes', 'bytes_out', 'content_length'],
                'error_rate': ['error_rate', 'failure_rate'],
            }
            for standard_key, alias_list in key_aliases.items():
                for alias in alias_list:
                    if alias in source_data:
                        try:
                            features[standard_key] = float(source_data[alias])
                            break # Found it, move to next standard key
                        except (ValueError, TypeError):
                            continue
        
        # --- Priority 2: Fallback to Regex for any format (good for unstructured) ---
        # This will also fill in any features missed in structured parsing.
        for feature_name, pattern in self.common_patterns.items():
            if feature_name in features: continue # Skip if already extracted
            matches = re.findall(pattern, raw_log, re.IGNORECASE)
            if matches:
                if feature_name in ['response_time', 'bytes', 'error_rate']:
                    try:
                        features[feature_name] = float(matches[0])
                    except (ValueError, IndexError):
                        features[feature_name] = 0.0
                else:
                    # For non-numeric patterns like IP, count occurrences
                    features[feature_name] = int(len(matches))

        # --- Priority 3: General calculated features ---
        level_mapping = {
            'DEBUG': 0, 'INFO': 1, 'WARN': 2, 'WARNING': 2,
            'ERROR': 3, 'CRITICAL': 4, 'FATAL': 5
        }
        features['log_level_numeric'] = int(level_mapping.get(
            str(parsed_data.get('level', 'INFO')).upper(), 1
        ))
        features['message_length'] = int(len(parsed_data.get('message', '')))
        features['word_count'] = int(len(parsed_data.get('message', '').split()))
        features['special_chars'] = int(len(re.findall(r'[^a-zA-Z0-9\s]', raw_log)))
        
        return features
    
    def get_feature_vectors(self, parsed_logs: List[ParsedLogRecord], feature_names: List[str]) -> np.ndarray:
        """
        For each parsed log, extracts a feature vector as a NumPy array,
        ensuring a consistent order and handling missing features.
        """
        feature_vectors = []
        for log in parsed_logs:
            # Create a vector in the order specified by feature_names
            vector = [log.features.get(name, 0.0) for name in feature_names]
            feature_vectors.append(vector)
        return np.array(feature_vectors)

    def _parse_timestamp(self, timestamp_str: Optional[str]) -> datetime:
        """Parse various timestamp formats."""
        if not timestamp_str:
            return datetime.utcnow()
        
        # Common timestamp formats
        formats = [
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%d %H:%M:%S.%f',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%S.%f',
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(timestamp_str, fmt)
            except ValueError:
                continue
        
        # If no format matches, return current time
        logger.warning(f"Could not parse timestamp: {timestamp_str}")
        return datetime.utcnow()
    
    def _create_fallback_log(self, raw_log: str, service_name: str, source: str) -> ParsedLog:
        """Create a fallback parsed log when parsing fails."""
        return ParsedLog(
            timestamp=datetime.utcnow(),
            level='ERROR',
            message=f"Failed to parse log: {raw_log[:100]}...",
            service=service_name,
            source=source,
            features={
                'message_length': int(len(raw_log)),
                'word_count': int(len(raw_log.split())),
                'special_chars': int(len(re.findall(r'[^a-zA-Z0-9\s]', raw_log))),
                'log_level_numeric': int(3)  # ERROR level
            },
            raw_log=raw_log,
            metadata={'parse_error': True}
        )

    def extract_features(self, parsed_logs: list) -> 'np.ndarray':
        """
        Extracts feature vectors from a list of ParsedLog objects for model training.
        Returns a numpy array of shape (n_samples, n_features).
        """
        features = []
        for log in parsed_logs:
            feature_vector = []
            for column in getattr(settings, "feature_columns", ["resp_time", "bytes_out", "error_rate"]):
                value = log.features.get(column, 0)
                try:
                    feature_vector.append(float(value))
                except (ValueError, TypeError):
                    feature_vector.append(0.0)
            features.append(feature_vector)
        return np.array(features)


# Global parser service instance
log_parser_service = LogParserService() 