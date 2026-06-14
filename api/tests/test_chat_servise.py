import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from api.modules import chat_service


# ----------------------------
# normalize_steps
# ----------------------------

def test_normalize_steps_dict():
    steps = [{"step": "a"}, {"step": "b"}]
    out = chat_service.normalize_steps(steps)

    assert out == steps


def test_normalize_steps_model_dump():
    obj = SimpleNamespace(model_dump=lambda: {"step": "x"})
    out = chat_service.normalize_steps([obj])

    assert out == [{"step": "x"}]


def test_normalize_steps_fallback():
    obj = SimpleNamespace(step="s1", status="ok")
    out = chat_service.normalize_steps([obj])

    assert out == [{"step": "s1", "status": "ok"}]


def test_normalize_steps_none():
    assert chat_service.normalize_steps(None) == []


# ----------------------------
# run_agent
# ----------------------------

@patch("api.modules.chat_service.graph")
def test_run_agent(mock_graph):
    mock_graph.invoke.return_value = {
        "steps": [{"step": "test"}],
        "answer": "ok"
    }

    request = SimpleNamespace(
        message="hello",
        filters=None
    )

    result = chat_service.run_agent(request)

    assert result["answer"] == "ok"
    assert "steps" in result
    mock_graph.invoke.assert_called_once()


# ----------------------------
# run_agent_stream
# ----------------------------

@patch("api.modules.chat_service.graph")
def test_run_agent_stream(mock_graph):
    mock_graph.stream.return_value = iter([{"node": {"a": 1}}])

    request = SimpleNamespace(
        message="hello",
        filters=None
    )

    stream = chat_service.run_agent_stream(request)

    events = list(stream)

    assert events == [{"node": {"a": 1}}]
    mock_graph.stream.assert_called_once()


# ----------------------------
# run_agent_stream_final
# ----------------------------

@patch("api.modules.chat_service.graph")
def test_run_agent_stream_final(mock_graph):
    mock_graph.stream.return_value = iter([
        {"node1": {"current_step": "s1", "steps": []}},
        {"node2": {"answer": "done"}}
    ])

    request = SimpleNamespace(
        message="hello",
        filters=None
    )

    stream = chat_service.run_agent_stream_final(request)
    events = list(stream)

    assert events[0]["type"] == "step"
    assert events[-1]["type"] == "final"
    assert "result" in events[-1]
