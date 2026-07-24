# api/modules/chat_service.py
"""
Service layer for conversational agent execution.

This module provides helper functions used by API endpoints to
execute the LangGraph workflow and format its outputs.

Features:
    - Execute the agent and return the final response.
    - Stream intermediate graph updates.
    - Stream both intermediate steps and the final result.
    - Normalize agent execution steps into serializable dictionaries.

Functions:
    normalize_steps:
        Convert agent steps into JSON-serializable dictionaries.

    run_agent:
        Execute the workflow and return the final state.

    run_agent_stream:
        Stream graph execution updates.

    run_agent_stream_final:
        Stream execution updates and emit the final aggregated result.
"""

from typing import Any

from agents.graph import graph as build_my_graph
from shared.schemas import AgentState as GraphState
from shared.schemas import ChatFilters

graph = build_my_graph()


def normalize_steps(steps: list[Any] | None) -> list[dict]:
    """
    Normalize agent execution steps.

    Converts heterogeneous step objects (dictionaries, Pydantic models,
    or custom objects) into a list of JSON-serializable dictionaries.

    Args:
        steps: Collection of execution steps.

    Returns:
        list[dict]: Normalized steps.
    """
    result = []

    for s in steps or []:
        # already dict → keep
        if isinstance(s, dict):
            result.append(s)
            continue

        # Pydantic / BaseModel → convert to dict
        if hasattr(s, "model_dump"):
            result.append(s.model_dump())
            continue

        # fallback (safety net)
        result.append(
            {
                "step": getattr(s, "step", None),
                "status": getattr(s, "status", None),
            }
        )

    return result


def run_agent(chat_request):
    """
    Execute the conversational agent workflow.

    Builds the initial graph state from the user request,
    runs the workflow to completion, and returns the final state.

    Args:
        chat_request: User request containing message and filters.

    Returns:
        dict: Final workflow state including normalized execution steps.
    """
    initial_filters = chat_request.filters or ChatFilters()

    initial_state = GraphState(
        user_query=chat_request.message,
        initial_filters=initial_filters,
        current_step=None,
        steps=[],
        sql_filters=ChatFilters(),
        candidate_ids=None,
        retrieved_movies=[],
        answer=None,
    )

    final_state = graph.invoke(initial_state, config={"recursion_limit": 10})

    return {**final_state, "steps": normalize_steps(final_state.get("steps"))}


def run_agent_stream(chat_request):
    """
    Execute the workflow in streaming mode.

    Returns a LangGraph event stream containing intermediate
    state updates produced during graph execution.

    Args:
        chat_request: User request containing message and filters.

    Returns:
        Iterator producing graph update events.
    """
    initial_filters = chat_request.filters or ChatFilters()

    initial_state = GraphState(
        user_query=chat_request.message,
        initial_filters=initial_filters,
        current_step=None,
        steps=[],
        sql_filters=ChatFilters(),
        candidate_ids=None,
        retrieved_movies=[],
        answer=None,
    )

    return graph.stream(
        initial_state, config={"recursion_limit": 10}, stream_mode="updates"
    )


def run_agent_stream_final(chat_request):
    """
    Stream workflow execution and aggregate the final state.

    Yields:
        dict:
            Step events:
                {
                    "type": "step",
                    "node": str,
                    "step": {...}
                }

            Final event:
                {
                    "type": "final",
                    "result": {...}
                }

    Args:
        chat_request: User request containing message and filters.
    """
    initial_state = GraphState(
        user_query=chat_request.message,
        initial_filters=chat_request.filters or ChatFilters(),
        current_step=None,
        steps=[],
        sql_filters=ChatFilters(),
        candidate_ids=None,
        retrieved_movies=[],
        answer=None,
    )

    stream = graph.stream(
        initial_state, config={"recursion_limit": 10}, stream_mode="updates"
    )

    final_state: dict[str, Any] = {}

    for event in stream:
        if not isinstance(event, dict):
            continue

        for node_name, state in event.items():
            if node_name in ("card_node", "format_cards_node"):
                payload = {
                    "type": "card",
                    "films": [
                        (f.model_dump() if hasattr(f, "model_dump") else f)
                        for f in (state.get("retrieved_movies") or [])
                    ],
                }
                yield {"type": "card", "payload": payload}
            # Pydantic -> dict
            if hasattr(state, "model_dump"):
                state = state.model_dump()

            # НАКАПЛИВАЕМ state вместо перезаписи
            final_state.update(state)

            yield {
                "type": "step",
                "node": node_name,
                "step": {
                    "current_step": final_state.get("current_step"),
                    "steps": normalize_steps(final_state.get("steps", [])),
                },
            }

    yield {
        "type": "final",
        "result": {
            **final_state,
            "steps": normalize_steps(final_state.get("steps", [])),
        },
    }
