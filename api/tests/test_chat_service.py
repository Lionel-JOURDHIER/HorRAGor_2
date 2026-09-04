
from types import SimpleNamespace
import pytest
from unittest.mock import MagicMock, patch
from api.modules import chat_service
from api.modules.chat_service import (
    get_conversation_history,
    get_graph_config,
    init_graph,
    normalize_steps,
    run_agent_stream_final,
)
from shared.schemas import ChatRequest

# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_user():
    user = MagicMock()
    user.id = 1
    return user


@pytest.fixture
def chat_request():
    return ChatRequest(
        message="films like Inception",
    )
# ============================================================================
# init_graph
# ============================================================================


def test_init_graph():
    mock_checkpointer = MagicMock()
    mock_graph = MagicMock()

    with patch(
        "api.modules.chat_service.build_my_graph",
        return_value=mock_graph,
    ) as mock_build:

        init_graph(mock_checkpointer)

    mock_build.assert_called_once_with(
        checkpointer=mock_checkpointer
    )

    assert chat_service.graph == mock_graph


# ============================================================================
# normalize_steps
# ============================================================================


def test_normalize_steps_none():
    result = normalize_steps(None)

    assert result == []


def test_normalize_steps_empty():
    result = normalize_steps([])

    assert result == []



def test_normalize_steps_dict():
    steps = [
        {
            "step": "search",
            "status": "success",
        }
    ]

    result = normalize_steps(steps)

    assert result == steps


def test_normalize_steps_multiple_dicts():
    steps = [
        {"step": "search", "status": "success"},
        {"step": "filter", "status": "success"},
    ]

    result = normalize_steps(steps)

    assert result == steps


def test_normalize_steps_model_dump():

    obj = SimpleNamespace(model_dump=lambda: {"step": "x"})


    result = normalize_steps([step])

    assert result == [
        {
            "step": "search",
            "status": "success",
        }
    ]

    step.model_dump.assert_called_once()


def test_normalize_steps_fallback():

    obj = SimpleNamespace(step="s1", status="ok")


    result = normalize_steps([step])


    assert out == [{"step": "s1", "status": "ok"}]



def test_normalize_steps_fallback_missing_attributes():
    step = object()

    result = normalize_steps([step])

    assert result == [
        {
            "step": None,
            "status": None,
        }
    ]


# ============================================================================
# get_graph_config

def test_get_graph_config_thread_id_from_user():
    request = SimpleNamespace(message="hello")
    user = SimpleNamespace(id=42)

    config = chat_service.get_graph_config(request, user)

    assert config["configurable"]["thread_id"] == "user_42"
    assert config["recursion_limit"] == 15
    assert "callbacks" in config
    assert "metadata" in config


def test_get_graph_config_different_users_get_different_threads():
    request = SimpleNamespace(message="hello")

    config_a = chat_service.get_graph_config(request, SimpleNamespace(id=1))
    config_b = chat_service.get_graph_config(request, SimpleNamespace(id=2))

    assert (
        config_a["configurable"]["thread_id"] != config_b["configurable"]["thread_id"]
    )

    assert result["recursion_limit"] == 15
    assert result["configurable"]["thread_id"] == "user_1"

    assert result["metadata"]["application"] == "HorRAGor"
    assert result["metadata"]["environment"] == "development"

    assert "callbacks" in result
    assert len(result["callbacks"]) == 1


def test_get_graph_config_uses_user_id(chat_request):
    user = MagicMock()
    user.id = 42

    result = get_graph_config(
        chat_request,
        user,
    )

    assert result["configurable"]["thread_id"] == "user_42"


# ============================================================================
# get_conversation_history
# ============================================================================


@pytest.mark.asyncio
async def test_get_conversation_history_empty(mock_user):
    mock_graph = MagicMock()

    async def empty_history(config):
        return
        yield

    mock_graph.aget_state_history = empty_history

    with patch(
        "api.modules.chat_service.graph",
        mock_graph,
    ):
        result = await get_conversation_history(mock_user)

    assert result == []


@pytest.mark.asyncio
async def test_get_conversation_history_single_conversation(mock_user):
    mock_graph = MagicMock()

    snapshot = MagicMock()
    snapshot.values = {
        "user_query": "What is Inception?",
        "answer": "Inception is a science-fiction film.",
        "retrieved_movies": [],
    }

    async def state_history(config):
        yield snapshot

    mock_graph.aget_state_history = state_history

    with patch(
        "api.modules.chat_service.graph",
        mock_graph,
    ):
        result = await get_conversation_history(mock_user)

    assert result == [
        {
            "role": "user",
            "content": "What is Inception?",
        },
        {
            "role": "assistant",
            "content": "Inception is a science-fiction film.",
            "films": [],
        },
    ]


@pytest.mark.asyncio
async def test_get_conversation_history_multiple_conversations(
    mock_user,
):
    mock_graph = MagicMock()

    snapshot1 = MagicMock()
    snapshot1.values = {
        "user_query": "What is Inception?",
        "answer": "A science-fiction film.",
        "retrieved_movies": [],
    }

    snapshot2 = MagicMock()
    snapshot2.values = {
        "user_query": "Who directed it?",
        "answer": "Christopher Nolan.",
        "retrieved_movies": [],
    }

    async def state_history(config):
        # La fonction reverse() doit remettre ces snapshots
        # dans l'ordre chronologique.
        yield snapshot2
        yield snapshot1

    mock_graph.aget_state_history = state_history

    with patch(
        "api.modules.chat_service.graph",
        mock_graph,
    ):
        result = await get_conversation_history(mock_user)

    assert len(result) == 4

    assert result[0] == {
        "role": "user",
        "content": "Inception" if False else "What is Inception?",
    }

    assert result[1]["role"] == "assistant"
    assert result[1]["content"] == "A science-fiction film."

    assert result[2] == {
        "role": "user",
        "content": "Who directed it?",
    }

    assert result[3]["role"] == "assistant"
    assert result[3]["content"] == "Christopher Nolan."


@pytest.mark.asyncio
async def test_get_conversation_history_with_pydantic_films(
    mock_user,
):
    mock_graph = MagicMock()

    film = MagicMock()
    film.model_dump.return_value = {
        "id": 123,
        "title": "Inception",
    }

    snapshot = MagicMock()
    snapshot.values = {
        "user_query": "Give me movies",
        "answer": "Here are some movies.",
        "retrieved_movies": [film],
    }

    async def state_history(config):
        yield snapshot

    mock_graph.aget_state_history = state_history

    with patch(
        "api.modules.chat_service.graph",
        mock_graph,
    ):
        result = await get_conversation_history(mock_user)

    assert result[1]["films"] == [
        {
            "id": 123,
            "title": "Inception",
        }
    ]


@pytest.mark.asyncio
async def test_get_conversation_history_with_dict_films(
    mock_user,
):
    mock_graph = MagicMock()

    snapshot = MagicMock()
    snapshot.values = {
        "user_query": "Give me movies",
        "answer": "Here are some movies.",
        "retrieved_movies": [
            {
                "id": 123,
                "title": "Inception",
            }
        ],
    }

    async def state_history(config):
        yield snapshot

    mock_graph.aget_state_history = state_history

    with patch(
        "api.modules.chat_service.graph",
        mock_graph,
    ):
        result = await get_conversation_history(mock_user)

    assert result[1]["films"] == [
        {
            "id": 123,
            "title": "Inception",
        }
    ]


@pytest.mark.asyncio
async def test_get_conversation_history_ignores_snapshot_without_query(
    mock_user,
):
    mock_graph = MagicMock()

    snapshot = MagicMock()
    snapshot.values = {
        "user_query": None,
        "answer": "some answer",
        "retrieved_movies": [],
    }

    async def state_history(config):
        yield snapshot

    mock_graph.aget_state_history = state_history

    with patch(
        "api.modules.chat_service.graph",
        mock_graph,
    ):
        result = await get_conversation_history(mock_user)

    assert result == []


# ============================================================================
# run_agent_stream_final
# ============================================================================


@pytest.mark.asyncio
async def test_run_agent_stream_final_basic(
    chat_request,
    mock_user,
):
    mock_graph = MagicMock()

    async def fake_stream(*args, **kwargs):
        yield {
            "search_node": {
                "current_step": "search",
                "steps": [
                    {
                        "step": "search",
                        "status": "success",
                    }
                ],
            }
        }

    mock_graph.astream = fake_stream

    with patch(
        "api.modules.chat_service.graph",
        mock_graph,
    ):
        events = [
            event
            async for event in run_agent_stream_final(
                chat_request,
                mock_user,
            )
        ]

    assert len(events) == 2

    assert events[0]["type"] == "step"
    assert events[0]["node"] == "search_node"

    assert events[0]["step"]["current_step"] == "search"
    assert events[0]["step"]["steps"] == [
        {
            "step": "search",
            "status": "success",
        }
    ]

    assert events[1]["type"] == "final"
    assert events[1]["result"]["current_step"] == "search"


@pytest.mark.asyncio
async def test_run_agent_stream_final_card_event(
    chat_request,
    mock_user,
):
    mock_graph = MagicMock()

    film = MagicMock()
    film.model_dump.return_value = {
        "id": 1,
        "title": "Inception",
    }

    async def fake_stream(*args, **kwargs):
        yield {
            "card_node": {
                "retrieved_movies": [film],
                "current_step": "cards",
                "steps": [],
            }
        }

    mock_graph.astream = fake_stream

    with patch(
        "api.modules.chat_service.graph",
        mock_graph,
    ):
        events = [
            event
            async for event in run_agent_stream_final(
                chat_request,
                mock_user,
            )
        ]

    assert events[0]["type"] == "card"

    assert events[0]["payload"]["type"] == "card"

    assert events[0]["payload"]["films"] == [
        {
            "id": 1,
            "title": "Inception",
        }
    ]

    assert events[1]["type"] == "step"


@pytest.mark.asyncio
async def test_run_agent_stream_final_format_cards_node(
    chat_request,
    mock_user,
):
    mock_graph = MagicMock()

    async def fake_stream(*args, **kwargs):
        yield {
            "format_cards_node": {
                "retrieved_movies": [
                    {
                        "id": 2,
                        "title": "Interstellar",
                    }
                ],
                "current_step": "cards",
                "steps": [],
            }
        }

    mock_graph.astream = fake_stream

    with patch(
        "api.modules.chat_service.graph",
        mock_graph,
    ):
        events = [
            event
            async for event in run_agent_stream_final(
                chat_request,
                mock_user,
            )
        ]

    assert events[0]["type"] == "card"
    assert events[0]["payload"]["films"] == [
        {
            "id": 2,
            "title": "Interstellar",
        }
    ]


@pytest.mark.asyncio
async def test_run_agent_stream_final_ignores_non_dict_event(
    chat_request,
    mock_user,
):
    mock_graph = MagicMock()

    async def fake_stream(*args, **kwargs):
        yield "invalid event"
        yield None
        yield {
            "search_node": {
                "current_step": "search",
                "steps": [],
            }
        }

    mock_graph.astream = fake_stream

    with patch(
        "api.modules.chat_service.graph",
        mock_graph,
    ):
        events = [
            event
            async for event in run_agent_stream_final(
                chat_request,
                mock_user,
            )
        ]

    # Les événements non-dict sont ignorés.
    assert len(events) == 2
    assert events[0]["type"] == "step"
    assert events[1]["type"] == "final"


@pytest.mark.asyncio
async def test_run_agent_stream_final_model_dump_state(
    chat_request,
    mock_user,
):
    mock_graph = MagicMock()

    state = MagicMock()
    state.model_dump.return_value = {
        "current_step": "search",
        "steps": [
            {
                "step": "search",
                "status": "success",
            }
        ],
        "answer": "Result",
    }

    async def fake_stream(*args, **kwargs):
        yield {
            "search_node": state,
        }

    mock_graph.astream = fake_stream

    with patch(
        "api.modules.chat_service.graph",
        mock_graph,
    ):
        events = [
            event
            async for event in run_agent_stream_final(
                chat_request,
                mock_user,
            )
        ]

    state.model_dump.assert_called_once()

    assert events[-1]["type"] == "final"
    assert events[-1]["result"]["answer"] == "Result"


@pytest.mark.asyncio
async def test_run_agent_stream_final_accumulates_state(
    chat_request,
    mock_user,
):
    mock_graph = MagicMock()

    async def fake_stream(*args, **kwargs):
        yield {
            "search_node": {
                "current_step": "search",
                "steps": [
                    {
                        "step": "search",
                        "status": "success",
                    }
                ],
            }
        }

        yield {
            "answer_node": {
                "answer": "Final answer",
                "steps": [
                    {
                        "step": "answer",
                        "status": "success",
                    }
                ],
            }
        }

    mock_graph.astream = fake_stream

    with patch(
        "api.modules.chat_service.graph",
        mock_graph,
    ):
        events = [
            event
            async for event in run_agent_stream_final(
                chat_request,
                mock_user,
            )
        ]

    final_event = events[-1]

    assert final_event["type"] == "final"

    # Le state précédent est conservé.
    assert final_event["result"]["current_step"] == "search"

    # Le nouveau state est également conservé.
    assert final_event["result"]["answer"] == "Final answer"

    assert final_event["result"]["steps"] == [
        {
            "step": "answer",
            "status": "success",
        }
    ]

