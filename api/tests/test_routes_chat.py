import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from api.main import app

# ----------------------------
# /chat/response
# ----------------------------

@patch("api.routes.run_agent")
def test_chat_response(mock_run_agent, client):
    mock_run_agent.return_value = {
        "answer": "hello",
        "steps": [
            {
                "step": "s1",
                "status": "completed"
            }
        ],
        "retrieved_movies": [
            {
                "tmdb_id": 898555,
                "title": "Film"
            }
        ]
    }

    payload = {
        "message": "hi",
        "filters": None
    }

    response = client.post("/chat/response", json=payload)

    assert response.status_code == 200
    data = response.json()

    assert data["answer"] == "hello"
    assert isinstance(data["steps"], list)
    assert isinstance(data["recommendations"], list)


@patch("api.routes.run_agent")
def test_chat_response_error(mock_run_agent, client):
    mock_run_agent.side_effect = Exception("fail")

    payload = {
        "message": "hi",
        "filters": None
    }

    response = client.post("/chat/response", json=payload)

    assert response.status_code == 500


# ----------------------------
# /chat/stream (SSE)
# ----------------------------

@patch("api.routes.run_agent_stream")
def test_chat_stream(mock_stream, client):
    mock_stream.return_value = iter([
        {"node1": {"steps": [{"step": "a"}]}}
    ])

    payload = {
        "message": "hi",
        "filters": None
    }

    response = client.post("/chat/stream", json=payload)

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]


# ----------------------------
# /chat/response_stream
# ----------------------------

@patch("api.routes.run_agent_stream_final")
def test_chat_response_stream(mock_stream, client):
    mock_stream.return_value = iter([
        {
            "type": "step",
            "node": "n1",
            "step": {"steps": [{"step": "x"}]}
        },
        {
            "type": "final",
            "result": {
                "answer": "ok",
                "steps": [{"step": "x"}],
                "retrieved_movies": []
            }
        }
    ])

    payload = {
        "message": "hi",
        "filters": None
    }

    response = client.post("/chat/response_stream", json=payload)

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]