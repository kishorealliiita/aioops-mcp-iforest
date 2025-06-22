import pytest
from app.services.log_parser_service import LogParserService
from app.schemas.models import RawLogRecord
from app.schemas.enums import LogFormat
from pydantic import ValidationError

@pytest.fixture(scope="module")
def log_parser():
    """Provides a LogParserService instance for testing."""
    return LogParserService()

def test_parse_json_log(log_parser):
    """Tests parsing of a valid JSON log."""
    raw_log = RawLogRecord(
        raw_log='{"timestamp": "2024-07-25T10:00:00Z", "level": "INFO", "response_time": 120, "bytes_out": 512}',
        service="web",
        source="nginx",
        format_type=LogFormat.JSON
    )
    parsed_logs = log_parser.parse_logs([raw_log])
    assert len(parsed_logs) == 1
    parsed = parsed_logs[0]
    assert parsed.service == "web"
    assert parsed.source == "nginx"
    assert parsed.features["response_time"] == 120
    assert parsed.features["bytes_out"] == 512
    assert parsed.log_level == "INFO"

def test_parse_key_value_log(log_parser):
    """Tests parsing of a valid key-value log."""
    raw_log = RawLogRecord(
        raw_log="timestamp=2024-07-25T10:05:00Z level=ERROR query_time=5000ms error_rate=0.75",
        service="db",
        source="postgres",
        format_type=LogFormat.KEY_VALUE
    )
    parsed_logs = log_parser.parse_logs([raw_log])
    assert len(parsed_logs) == 1
    parsed = parsed_logs[0]
    assert parsed.service == "db"
    assert parsed.features["query_time"] == 5000
    assert parsed.features["error_rate"] == 0.75
    assert parsed.log_level == "ERROR"

def test_parse_regex_log_with_custom_pattern(log_parser):
    """Tests parsing a log with a custom regex pattern."""
    raw_log = RawLogRecord(
        raw_log="[2024-07-25 10:10:10] [CRITICAL] [auth_service] - User 'admin' failed to login from IP 192.168.1.100",
        service="auth",
        source="app_security",
        format_type=LogFormat.REGEX,
        custom_config={
            "pattern": r"\[(.*?)\] \[(\w+)\] \[(.*?)\] - (.*)",
            "field_mapping": {
                "0": "timestamp",
                "1": "level",
                "2": "service_name",
                "3": "message"
            }
        }
    )
    parsed_logs = log_parser.parse_logs([raw_log])
    assert len(parsed_logs) == 1
    parsed = parsed_logs[0]
    assert parsed.service == "auth"
    assert parsed.log_level == "CRITICAL"
    assert parsed.message == "User 'admin' failed to login from IP 192.168.1.100"
    assert "service_name" not in parsed.features

def test_parse_malformed_json_log(log_parser):
    """Tests that a malformed JSON log is handled gracefully."""
    raw_log = RawLogRecord(
        raw_log='{"timestamp": "2024-07-25T10:15:00Z", "message": "Forgot a comma"',
        service="worker",
        source="celery",
        format_type=LogFormat.JSON
    )
    parsed_logs = log_parser.parse_logs([raw_log])
    # Should be skipped, not crash
    assert len(parsed_logs) == 0

def test_parse_unsupported_format(log_parser):
    """Tests that an unsupported format raises a validation error."""
    # Using a string that is not in the LogFormat enum should raise a Pydantic validation error
    with pytest.raises(ValidationError):
        RawLogRecord(
            raw_log="<xml><event>some event</event></xml>",
            service="legacy",
            source="system",
            format_type="xml"
        )

def test_numeric_extraction_from_string(log_parser):
    """Tests that numeric values are correctly extracted from strings in key-value logs."""
    raw_log = RawLogRecord(
        raw_log="response_time=500ms duration=1.5s",
        service="api",
        source="gateway",
        format_type=LogFormat.KEY_VALUE
    )
    parsed_logs = log_parser.parse_logs([raw_log])
    assert len(parsed_logs) == 1
    features = parsed_logs[0].features
    assert features["response_time"] == 500
    assert features["duration"] == 1.5

def test_batch_parsing_with_mixed_formats_and_errors(log_parser):
    """Tests parsing a batch of logs with mixed formats and some errors."""
    logs = [
        # Valid JSON
        RawLogRecord(raw_log='{"resp_time": 100}', service="s1", source="n1", format_type=LogFormat.JSON),
        # Malformed JSON
        RawLogRecord(raw_log='{"resp_time": 200', service="s2", source="n2", format_type=LogFormat.JSON),
        # Valid Key-Value
        RawLogRecord(raw_log='resp_time=300', service="s3", source="n3", format_type=LogFormat.KEY_VALUE),
        # Valid Regex
        RawLogRecord(
            raw_log="[2024-07-25 10:10:10] [INFO] - Resp: 400",
            service="s4", source="n4", format_type=LogFormat.REGEX,
            custom_config={
                "pattern": r"\[(.*?)\] \[(.*?)\] - Resp: (\d+)",
                "field_mapping": {"1": "level", "2": "resp_time"}
            }
        ),
        # Key-Value with no numeric features
        RawLogRecord(raw_log='msg="hello world"', service="s5", source="n5", format_type=LogFormat.KEY_VALUE),
    ]

    parsed_logs = log_parser.parse_logs(logs)
    
    # Expect 3 valid logs with numeric features
    assert len(parsed_logs) == 3

    # Check features
    assert parsed_logs[0].features["resp_time"] == 100
    assert parsed_logs[1].features["resp_time"] == 300
    assert parsed_logs[2].features["resp_time"] == 400 