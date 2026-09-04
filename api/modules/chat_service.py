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
from logger import get_logger, setup_logger
from shared.schemas import ChatFilters, ChatRequest

from api.monitoring.langfuse_callback import langfuse_handler

setup_logger()
logger = get_logger("CHAT_SERVICE")

# Construit par `init_graph()` au démarrage de l'API (lifespan de
# api/main.py), avec un checkpointer async — construire le graphe ici, à
# l'import du module, ne peut pas fonctionner : il faut un AsyncSqliteSaver
# déjà ouvert, ce qui suppose une boucle asyncio active.
graph = None


def init_graph(checkpointer) -> None:
    """Compile le graphe LangGraph avec le checkpointer fourni.

    Appelé une fois au démarrage de l'API, depuis le lifespan de
    `api/main.py`, une fois l'`AsyncSqliteSaver` ouvert.

    Args:
        checkpointer: Backend de persistance async pour la mémoire de
            conversation (langgraph.checkpoint.sqlite.aio.AsyncSqliteSaver).
    """
    global graph
    graph = build_my_graph(checkpointer=checkpointer)


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


def get_graph_config(chat_request: ChatRequest, user: Any) -> dict[str, Any]:
    """
    Génère le dictionnaire de configuration requis par LangGraph.

    Le thread_id du checkpointer est l'identifiant de l'utilisateur
    authentifié : chaque utilisateur a sa propre mémoire de conversation,
    persistée entre les redémarrages (checkpointer SQLite).

    Args:
        chat_request: Requête utilisateur (message, filtres).
        user: Utilisateur authentifié courant (database.tables.users.User).

    Returns:
        Configuration transmise à `graph.astream`.
    """
    thread_id = f"user_{user.id}"

    logger.info(
        f"[NOUVELLE REQUÊTE CHAT] utilisateur={user.id} thread_id={thread_id} "
        f'message="{chat_request.message}"'
    )

    return {
        "recursion_limit": 15,  # Marge pour les aller-retours RAG + Wikipédia
        "configurable": {"thread_id": thread_id},
        "callbacks": [langfuse_handler],
        "metadata": {
            "application": "HorRAGor",
            "environment": "development",
        },
    }


# async def run_agent(chat_request):
#     """
#     Execute the conversational agent workflow.

#     Builds the initial graph state from the user request,
#     runs the workflow to completion, and returns the final state.

#     Args:
#         chat_request: User request containing message and filters.

#     Returns:
#         dict: Final workflow state including normalized execution steps.
#     """
#     initial_filters = chat_request.filters or ChatFilters()

#     initial_state = {
#         "user_query": chat_request.message,
#         "initial_filters": chat_request.filters or ChatFilters(),
#         "current_step": None,
#         "steps": [],
#         "sql_filters": ChatFilters(),
#         "candidate_ids": None,
#         "retrieved_movies": [],
#         "answer": None,
#         "retry_count": 0,
#     }

#     config = get_graph_config(chat_request)

#     final_state = await graph.ainvoke(initial_state, config=config)

#     return {**final_state, "steps": normalize_steps(final_state.get("steps"))}


# async def run_agent_stream(chat_request):
#     """
#     Execute the workflow in streaming mode.

#     Returns a LangGraph event stream containing intermediate
#     state updates produced during graph execution.

#     Args:
#         chat_request: User request containing message and filters.

#     Returns:
#         Iterator producing graph update events.
#     """
#     initial_filters = chat_request.filters or ChatFilters()

#     initial_state = {
#         "user_query": chat_request.message,
#         "initial_filters": chat_request.filters or ChatFilters(),
#         "current_step": None,
#         "steps": [],
#         "sql_filters": ChatFilters(),
#         "candidate_ids": None,
#         "retrieved_movies": [],
#         "answer": None,
#         "retry_count": 0,
#     }

#     config = get_graph_config(chat_request)

#     return graph.astream(initial_state, config=config, stream_mode="updates")


async def get_conversation_history(user: Any) -> list[dict[str, Any]]:
    """Reconstruit l'historique affichable de la conversation d'un utilisateur.

    L'état LangGraph n'accumule pas les tours : `user_query`/`answer` sont
    écrasés à chaque nouvel appel de `graph.astream`. On rejoue donc
    l'historique des checkpoints du thread (`aget_state_history`, du plus
    récent au plus ancien) pour retrouver, dans l'ordre chronologique,
    chaque paire question/réponse effectivement affichée à l'utilisateur.

    Args:
        user: Utilisateur authentifié courant (database.tables.users.User).

    Returns:
        Messages {"role", "content", "films"?} dans l'ordre chronologique,
        au format attendu par `st.session_state.messages` côté frontend.
    """
    config = {"configurable": {"thread_id": f"user_{user.id}"}}
    checkpoints = [snap async for snap in graph.aget_state_history(config)]
    checkpoints.reverse()  # ordre chronologique (le plus ancien d'abord)

    history: list[dict[str, Any]] = []
    pending_query: str | None = None
    pending_answer: str | None = None
    pending_films: list[Any] = []

    def flush_pending() -> None:
        if pending_query is None:
            return
        history.append({"role": "user", "content": pending_query})
        history.append(
            {
                "role": "assistant",
                "content": pending_answer or "",
                "films": [
                    (f.model_dump() if hasattr(f, "model_dump") else f)
                    for f in pending_films
                ],
            }
        )

    for snapshot in checkpoints:
        values = snapshot.values
        query = values.get("user_query")

        if query and query != pending_query:
            flush_pending()
            pending_query = query
            pending_answer = None
            pending_films = []

        if values.get("answer"):
            pending_answer = values["answer"]
        if values.get("retrieved_movies"):
            pending_films = values["retrieved_movies"]

    flush_pending()
    return history


async def run_agent_stream_final(chat_request, user):
    """
    Stream workflow execution and aggregate the final state.

    Args:
        chat_request: User request containing message and filters.
        user: Authenticated user (database.tables.users.User), utilisé pour
            dériver le thread_id du checkpointer LangGraph.

    Yields:
        dict: Step and final events generated during workflow execution.
    """

    initial_state = {
        "user_query": chat_request.message,
        "initial_filters": chat_request.filters or ChatFilters(),
        "current_step": None,
        "steps": [],
        "sql_filters": ChatFilters(),
        "candidate_ids": None,
        "retrieved_movies": [],
        "answer": None,
        "retry_count": 0,
    }

    config = get_graph_config(chat_request, user)

    stream = graph.astream(initial_state, config=config, stream_mode="updates")

    final_state: dict[str, Any] = {}

    async for event in stream:
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
