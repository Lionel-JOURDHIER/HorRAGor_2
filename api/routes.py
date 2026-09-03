"""
api/routes.py

Routes de l'API IA HorRAGor.

Responsabilités:
- communication client
- exécution agent LangGraph
- streaming SSE
- génération de réponses

La base de données est accessible uniquement via Database API.
"""

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agents.tools.wiki_tools import wikipedia_search

from api.auth_utils import get_current_user
from api.modules.chat_service import (
    # run_agent,
    # run_agent_stream,
    run_agent_stream_final,
)
from api.modules.database_client import get_film
from database.tables.users import User

from shared.schemas import (
    AgentStep,
    ChatRequest,
    ChatResponse,
    FilmShort,
    ErrorResponse,
    WikipediaResponse,
    HealthResponse,
    FilmDetail
)

# LOGGER -----------------------------------------------------------
from logger import get_logger, setup_logger


setup_logger()
logger = get_logger("AI_ROUTES")

# ROUTER -----------------------------------------------------------
router = APIRouter()

# HEALTH ----------------------------------------------------------
@router.get(
    "/health",
    response_model=HealthResponse,
    responses={500: {"model": ErrorResponse}},
    tags=["System"],
)
async def health():
    return {
        "status": "ok",
        "service": "ai_api"
    }


# CHAT ----------------------------------------------------------
# @router.post(
#     "/chat/response",
#     response_model=ChatResponse,
#     responses={
#         404: {"model": ErrorResponse},
#         500: {"model": ErrorResponse},
#     },
#     tags=["Agent"],
# )
# async def chat(request: ChatRequest):
#     """
#     Execute the agent and return the final response.

#     Args:
#         request: User query and conversation context.

#     Returns:
#         ChatResponse containing:
#         - generated answer
#         - execution steps
#         - movie recommendations

#     Raises:
#         HTTPException:
#             500 if the agent execution fails.
#     """

#     try:
#         result = run_agent(request)

#         return ChatResponse(
#             answer=result.get("answer") or "No answer generated",
#             steps=[
#                 s
#                 if isinstance(s, AgentStep)
#                 else AgentStep(**s)
#                 if isinstance(s, dict)
#                 else AgentStep.model_validate(s)
#                 for s in (result.get("steps") or [])
#             ],
#             recommendations=[
#                 FilmShort.model_validate(r) if isinstance(r, dict) else r
#                 for r in result.get("retrieved_movies") or []
#             ],
#         )

#     except Exception as e:
#         logger.exception("Failed to get response from agent")
#         raise HTTPException(
#             status_code=500, detail=f"Failed to get response from agent: {str(e)}"
#         )


# @router.post(
#     "/chat/stream",
#     responses={
#         404: {"model": ErrorResponse},
#         500: {"model": ErrorResponse},
#     },
#     tags=["Agent"],
# )
# async def chat_stream(request: ChatRequest):
#     """
#     Stream agent execution steps using Server-Sent Events (SSE).

#     Each event contains:
#     - node: current graph node
#     - step: latest execution step

#     Returns:
#         StreamingResponse with media type `text/event-stream`.
#     """

#     async def event_generator():
#         try:
#             stream = await run_agent_stream(request)
#             for event in stream:
#                 if not isinstance(event, dict):
#                     continue

#                 for node_name, state in event.items():
#                     if isinstance(state, dict):
#                         steps = state.get("steps", [])
#                     else:
#                         steps = getattr(state, "steps", [])

#                     if not steps:
#                         continue

#                     last_step = steps[-1]

#                     payload = {
#                         "node": node_name,
#                         "step": (
#                             last_step.model_dump()
#                             if hasattr(last_step, "model_dump")
#                             else (
#                                 last_step.dict()
#                                 if hasattr(last_step, "dict")
#                                 else str(last_step)
#                             )
#                         ),
#                     }

#                     yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

#             yield f"data: {json.dumps({'status': 'done'})}\n\n"
#         except Exception as e:
#             logger.exception("Streaming failed")

#             yield (f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n")

#     return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/chat/response_stream", tags=["Agent"])
async def chat_stream_final(
    request: ChatRequest, current_user: User = Depends(get_current_user)
):
    """
    Stream agent execution steps and final response.

    Requires authentication : la mémoire de conversation LangGraph
    (thread_id du checkpointer) est indexée sur l'utilisateur courant.

    SSE event types:
    - step: intermediate execution state
    - final: final ChatResponse
    - done: stream completion

    Returns:
        StreamingResponse with incremental updates and
        the final validated ChatResponse.
    """

    async def event_generator():
        try:
            stream = run_agent_stream_final(request, current_user)
            async for event in stream:
                # STEP EVENTS
                if event["type"] == "step":
                    steps = event["step"]["steps"]

                    if not steps:
                        continue

                    for step in steps:
                        payload = {
                            "node": event["node"],
                            "step": step
                        }
                        yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
 
                    # last_step = steps[-1]
                    # payload = {"node": event["node"], "step": last_step}
                    # yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

                # FINAL RESPONSE
                elif event["type"] == "final":
                    result = event["result"]

                    movies = result.get("retrieved_movies") or []

                    film = None
                    recommendations = []

                    if len(movies) == 1:
                        movie = movies[0]

                        if isinstance(movie, FilmDetail):
                            film = movie
                        else:
                            movie_data = (
                                movie.model_dump()
                                if isinstance(movie, BaseModel)
                                else movie
                            )
                            film = FilmDetail.model_validate(movie_data)

                    elif len(movies) > 1:
                        recommendations = [
                            movie
                            if isinstance(movie, FilmShort)
                            else FilmShort.model_validate(
                                movie.model_dump()
                                if isinstance(movie, BaseModel)
                                else movie
                            )
                            for movie in movies
                        ]

                    response = ChatResponse(
                        answer=result.get("answer") or "No answer generated",

                        steps=[
                            step
                            if isinstance(step, AgentStep)
                            else AgentStep(**step)
                            if isinstance(step, dict)
                            else AgentStep.model_validate(step)
                            for step in (result.get("steps") or [])
                        ],

                        film=film,
                        recommendations=recommendations,
                    )

                    payload = json.loads(response.model_dump_json())

                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        except Exception as e:
            logger.exception("Streaming final response failed")
            yield (f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n")

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# WIKIPEDIA ----------------------------------------------------
@router.get(
    "/wikipedia/{tmdb_id}",
    response_model=WikipediaResponse,
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    tags=["Wikipedia"],
)
async def wikipedia(tmdb_id: int):
    """Retrieve movie info from Wikipedia using TMDB ID."""
    try:
        film = await get_film(tmdb_id)

        if not film:
            raise HTTPException(
                status_code=404,
                detail="Film not found"
            )

        title = film.title
        year = film.release_date.year if film.release_date else None

        response_wiki = wikipedia_search.invoke(
            {
                "title": title,
                "year": year,
            }
        )

        logger.info(
            "Successfully retrieved movie info from Wikipedia"
        )

        return response_wiki

    except HTTPException:
        raise

    except Exception as e:
        logger.exception(
            f"Failed to retrieve wikipedia info: {str(e)}"
        )

        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve wikipedia info: {str(e)}"
        )