# api/modules/chat_service.py
"""
Docstring....
"""
# api/modules/chat_service.py
"""
Docstring....
"""

from agents.graph import graph
from api.schemas import ChatFilters
from api.schemas import AgentState as GraphState


def normalize_steps(steps):
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
        result.append({
            "step": getattr(s, "step", None),
            "status": getattr(s, "status", None),
        })

    return result


def run_agent(chat_request):

    initial_filters = chat_request.filters or ChatFilters()

    initial_state = GraphState(
        user_query=chat_request.message,
        initial_filters=initial_filters,
        current_step=None,
        steps=[],
        sql_filters=ChatFilters(),
        candidate_ids=None,
        retrieved_movies=[],
        answer=None
    )

    final_state = graph.invoke(initial_state, config={"recursion_limit": 10})

    return {
        **final_state,
        "steps": normalize_steps(final_state.get("steps"))
    }

def run_agent_stream(chat_request):

    initial_filters = chat_request.filters or ChatFilters()

    initial_state = GraphState(
        user_query=chat_request.message,
        initial_filters=initial_filters,
        current_step=None,
        steps=[],
        sql_filters=ChatFilters(),
        candidate_ids=None,
        retrieved_movies=[],
        answer=None
    )



    return graph.stream(initial_state, config={"recursion_limit": 10}, stream_mode="updates")

def run_agent_stream_final(chat_request):
    initial_state = GraphState(
        user_query=chat_request.message,
        initial_filters=chat_request.filters or ChatFilters(),
        current_step=None,
        steps=[],
        sql_filters=ChatFilters(),
        candidate_ids=None,
        retrieved_movies=[],
        answer=None
    )

    stream = graph.stream(
        initial_state,
        config={"recursion_limit": 10},
        stream_mode="updates"
    )

    final_state = None

    for event in stream:
        if not isinstance(event, dict):
            continue

        for node_name, state in event.items():
            final_state = state

            # 1) промежуточные шаги
            yield {
                "step": {
                    "current_step": state.get("current_step"),
                    "steps": normalize_steps(state.get("steps", []))
                },
                "result": {}
            }

    # 2) финальный результат (после завершения graph)
    if final_state is not None:
        if hasattr(final_state, "model_dump"):
            final_state = final_state.model_dump()

        yield {
            "step": {},
            "result": {
                **final_state,
                "steps": normalize_steps(final_state.get("steps", []))
            }
        }