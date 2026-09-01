from unittest.mock import MagicMock, patch

import pytest
import requests

from api.monitoring.monitoring_service import MonitoringService


def test_monitoring_service_init():
    with patch.dict(
        "os.environ",
        {
            "LANGFUSE_HOST": "http://langfuse:3000",
            "LANGFUSE_PUBLIC_KEY": "public",
            "LANGFUSE_SECRET_KEY": "secret",
        },
        clear=True,
    ):
        service = MonitoringService()

    assert service.host == "http://langfuse:3000"
    assert service.public_key == "public"
    assert service.secret_key == "secret"


def test_monitoring_service_default_host():
    with patch.dict("os.environ", {}, clear=True):
        service = MonitoringService()

    assert service.host == "http://localhost:3000"
    assert service.public_key is None
    assert service.secret_key is None


def test_auth():
    service = MonitoringService()

    service.public_key = "public"
    service.secret_key = "secret"

    assert service.auth == ("public", "secret")


@patch("api.monitoring.monitoring_service.requests.get")
def test_get_traces(mock_get):
    mock_response = MagicMock()

    mock_response.json.return_value = {
        "data": [
            {
                "id": "trace-1",
                "latency": 100,
            },
            {
                "id": "trace-2",
                "latency": 200,
            },
        ]
    }

    mock_get.return_value = mock_response

    service = MonitoringService()
    service.host = "http://langfuse:3000"
    service.public_key = "public"
    service.secret_key = "secret"

    result = service.get_traces(limit=50)

    assert len(result) == 2
    assert result[0]["id"] == "trace-1"

    mock_get.assert_called_once_with(
        "http://langfuse:3000/api/public/traces",
        params={"limit": 50},
        auth=("public", "secret"),
        timeout=10,
    )

    mock_response.raise_for_status.assert_called_once()
    mock_response.json.assert_called_once()


@patch("api.monitoring.monitoring_service.requests.get")
def test_get_traces_empty(mock_get):
    mock_response = MagicMock()

    mock_response.json.return_value = {
        "data": []
    }

    mock_get.return_value = mock_response

    service = MonitoringService()

    result = service.get_traces()

    assert result == []


@patch("api.monitoring.monitoring_service.requests.get")
def test_get_traces_http_error(mock_get):
    mock_response = MagicMock()

    mock_response.raise_for_status.side_effect = requests.HTTPError(
        "Langfuse unavailable"
    )

    mock_get.return_value = mock_response

    service = MonitoringService()

    with pytest.raises(requests.HTTPError):
        service.get_traces()


def test_get_metrics():
    service = MonitoringService()

    traces = [
        {
            "latency": 100,
            "usage": {
                "input": 10,
                "output": 20,
            },
        },
        {
            "latency": 300,
            "usage": {
                "input": 30,
                "output": 40,
            },
        },
    ]

    with patch.object(
        service,
        "get_traces",
        return_value=traces,
    ):
        result = service.get_metrics()

    assert result == {
        "total_traces": 2,
        "average_latency_ms": 200,
        "input_tokens": 40,
        "output_tokens": 60,
        "total_tokens": 100,
    }


def test_get_metrics_empty():
    service = MonitoringService()

    with patch.object(
        service,
        "get_traces",
        return_value=[],
    ):
        result = service.get_metrics()

    assert result == {
        "total_traces": 0,
        "average_latency_ms": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
    }


def test_get_metrics_missing_usage():
    service = MonitoringService()

    traces = [
        {
            "latency": 100,
        },
        {
            "latency": 200,
            "usage": {},
        },
    ]

    with patch.object(
        service,
        "get_traces",
        return_value=traces,
    ):
        result = service.get_metrics()

    assert result == {
        "total_traces": 2,
        "average_latency_ms": 150,
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
    }