"""
api/main.py

Point d'entrée principal de l'API REST FastAPI.
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite
from agents.graph import CHECKPOINT_DB_PATH, CHECKPOINT_SERDE
from fastapi import FastAPI, Request
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from logger import get_logger, setup_logger
from prometheus_fastapi_instrumentator import Instrumentator

from api.auth_routes import router as auth_router
from api.modules.chat_service import init_graph
from api.monitoring.langfuse_client import langfuse
from api.routes import router
from api.routes_monitoring import router as monitoring_router

setup_logger()
logger = get_logger("MAIN")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Cycle de vie de l'API.

    - Charge l'index FAISS depuis les fichiers persistés.
    - Ouvre le checkpointer SQLite async de la mémoire de conversation
      LangGraph et compile le graphe (doit se faire ici : un
      AsyncSqliteSaver a besoin d'une boucle asyncio active, absente à
      l'import du module).
    - Aucun accès direct à SQLAlchemy ou Supabase.
    """

    from database.connection import db_session
    from database.faiss_service import faiss_global_service

    index_path = os.getenv(
        "FAISS_INDEX_PATH",
        "faiss_data/horragor.index",
    )

    mapping_path = os.getenv(
        "FAISS_MAPPING_PATH",
        "faiss_data/horragor_mapping.json",
    )

    logger.info(f"Chargement de l'index FAISS (instance={id(faiss_global_service)})...")

    loaded = faiss_global_service.load_index(
        index_path=index_path,
        mapping_path=mapping_path,
    )

    if not loaded:
        logger.warning(
            "Index FAISS absent sur le disque. Construction depuis Supabase..."
        )
        with db_session() as session:
            faiss_global_service.build_index(session)

        if faiss_global_service.index.ntotal == 0:
            logger.error(
                "Construction de l'index FAISS depuis Supabase : aucun film "
                "vectorisé trouvé (table film_embeddings vide)."
            )
            raise RuntimeError("FAISS index empty after build from Supabase.")

        faiss_global_service.save_index(index_path, mapping_path)

    logger.info(f"Index FAISS chargé : {faiss_global_service.index.ntotal} films.")

    Path(CHECKPOINT_DB_PATH).parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(CHECKPOINT_DB_PATH) as conn:
        checkpointer = AsyncSqliteSaver(conn, serde=CHECKPOINT_SERDE)
        init_graph(checkpointer)
        logger.info("Graphe LangGraph compilé avec le checkpointer SQLite async.")

        yield

    logger.info("Arrêt de l'API.")


app = FastAPI(
    title="HorRAGor API",
    version="0.1.0",
    lifespan=lifespan,
)

Instrumentator().instrument(app).expose(app)


@app.middleware("http")
async def langfuse_middleware(request: Request, call_next):
    """
    Middleware FastAPI pour l'instrumentation Langfuse.

    Les endpoints techniques et de monitoring sont exclus de Langfuse.
    """

    excluded_paths = {
        "/api/api/health",
        "/api/db/health",
        "/api/metrics",
        "/api/monitoring/metrics",
        "/api/monitoring/traces",
        "/api/docs",
        "/api/openapi.json",
    }

    if request.url.path in excluded_paths:
        return await call_next(request)

    with langfuse.start_as_current_observation(
        name=f"{request.method} {request.url.path}",
        as_type="span",
        input={
            "method": request.method,
            "url": str(request.url),
        },
    ) as observation:
        try:
            response = await call_next(request)

            observation.update(output={"status_code": response.status_code})

            return response

        except Exception as e:
            observation.update(output={"error": str(e)})
            raise

        finally:
            langfuse.flush()


app.include_router(router)
app.include_router(monitoring_router)
app.include_router(auth_router)
