from types import SimpleNamespace

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
# get_graph_config
# ----------------------------


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


# # ----------------------------
# # run_agent
# # ----------------------------

# @pytest.mark.asyncio
# @patch("api.modules.chat_service.graph")
# async def test_run_agent(mock_graph):
#     mock_graph.ainvoke = AsyncMock(
#         return_value={
#             "steps": [{"step": "test"}],
#             "answer": "ok",
#         }
#     )

#     request = SimpleNamespace(
#         message="hello",
#         filters=None,
#         session_id="test-session",
#     )

#     result = await chat_service.run_agent(request)

#     assert result["answer"] == "ok"
#     assert result["steps"] == [{"step": "test"}]

#     mock_graph.ainvoke.assert_awaited_once()


# # ----------------------------
# # run_agent_stream
# # ----------------------------

# @pytest.mark.asyncio
# @patch("api.modules.chat_service.graph")
# async def test_run_agent_stream(mock_graph):

#     async def fake_stream(*args, **kwargs):
#         yield {"node": {"a": 1}}

#     mock_graph.astream = MagicMock(
#         return_value=fake_stream()
#     )

#     request = SimpleNamespace(
#         message="hello",
#         filters=None,
#         session_id="test-session",
#     )

#     stream = await chat_service.run_agent_stream(request)

#     events = []

#     async for event in stream:
#         events.append(event)

#     assert events == [
#         {"node": {"a": 1}}
#     ]

#     mock_graph.astream.assert_called_once()


# # ----------------------------
# # run_agent_stream_final
# # ----------------------------

# @pytest.mark.asyncio
# @patch("api.modules.chat_service.graph")
# async def test_run_agent_stream_final(mock_graph):

#     async def fake_stream(*args, **kwargs):
#         yield {
#             "node1": {
#                 "current_step": "s1",
#                 "steps": [],
#             }
#         }

#         yield {
#             "node2": {
#                 "answer": "done",
#             }
#         }

#     mock_graph.astream = MagicMock(
#         return_value=fake_stream()
#     )

#     request = SimpleNamespace(
#         message="hello",
#         filters=None,
#         session_id="test-session",
#     )

#     stream = chat_service.run_agent_stream_final(request)

#     events = []

#     async for event in stream:
#         events.append(event)

#     assert events[0]["type"] == "step"
#     assert events[0]["node"] == "node1"

#     assert events[1]["type"] == "step"
#     assert events[1]["node"] == "node2"

#     assert events[-1]["type"] == "final"
#     assert "result" in events[-1]
#     assert events[-1]["result"]["answer"] == "done"

#     mock_graph.astream.assert_called_once()
