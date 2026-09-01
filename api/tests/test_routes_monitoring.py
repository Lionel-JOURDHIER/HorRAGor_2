from unittest.mock import patch

from api.main import app


@patch("api.routes_monitoring.monitoring_service.get_metrics")
def test_monitoring_metrics(mock_get_metrics, client):
    mock_get_metrics.return_value = {
        "total_traces": 10,
        "average_latency_ms": 125.5,
        "input_tokens": 100,
        "output_tokens": 200,
        "total_tokens": 300,
    }

    response = client.get("/monitoring/metrics")

    assert response.status_code == 200
    assert response.json() == {
        "total_traces": 10,
        "average_latency_ms": 125.5,
        "input_tokens": 100,
        "output_tokens": 200,
        "total_tokens": 300,
    }

    mock_get_metrics.assert_called_once()


@patch("api.routes_monitoring.monitoring_service.get_metrics")
def test_monitoring_metrics_error(mock_get_metrics, client):
    mock_get_metrics.side_effect = Exception("Langfuse unavailable")

    response = client.get("/monitoring/metrics")

    assert response.status_code == 500
    assert response.json()["detail"] == "Langfuse unavailable"

    mock_get_metrics.assert_called_once()


@patch("api.routes_monitoring.monitoring_service.get_traces")
def test_monitoring_traces(mock_get_traces, client):
    mock_get_traces.return_value = [
        {
            "id": "trace-1",
            "latency": 100,
        },
        {
            "id": "trace-2",
            "latency": 200,
        },
    ]

    response = client.get("/monitoring/traces")

    assert response.status_code == 200
    assert response.json() == {
        "traces": [
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

    mock_get_traces.assert_called_once_with(20)


@patch("api.routes_monitoring.monitoring_service.get_traces")
def test_monitoring_traces_with_limit(mock_get_traces, client):
    mock_get_traces.return_value = []

    response = client.get("/monitoring/traces?limit=50")

    assert response.status_code == 200
    assert response.json() == {"traces": []}

    mock_get_traces.assert_called_once_with(50)


@patch("api.routes_monitoring.monitoring_service.get_traces")
def test_monitoring_traces_error(mock_get_traces, client):
    mock_get_traces.side_effect = Exception("Langfuse unavailable")

    response = client.get("/monitoring/traces")

    assert response.status_code == 500
    assert response.json()["detail"] == "Langfuse unavailable"

    mock_get_traces.assert_called_once_with(20)