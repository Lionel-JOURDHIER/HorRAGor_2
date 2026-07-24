"""
api/main.py

Point d'entrée principal de l'API REST FastAPI.
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.routes import router

from logger import get_logger, setup_logger

setup_logger()
logger = get_logger("MAIN")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Cycle de vie de l'API.

    - Charge l'index FAISS depuis les fichiers persistés.
    - Aucun accès direct à SQLAlchemy ou Supabase.
    """

    from database.faiss_service import faiss_global_service

    index_path = os.getenv(
        "FAISS_INDEX_PATH",
        "faiss_data/horragor.index",
    )

    mapping_path = os.getenv(
        "FAISS_MAPPING_PATH",
        "faiss_data/horragor_mapping.json",
    )

    logger.info(
        f"Chargement de l'index FAISS (instance={id(faiss_global_service)})..."
    )

    loaded = faiss_global_service.load_index(
        index_path=index_path,
        mapping_path=mapping_path,
    )

    if not loaded:
        logger.error(
            "Impossible de charger l'index FAISS. "
            "Les fichiers d'index sont absents."
        )
        raise RuntimeError(
            "FAISS index not found."
        )

    logger.info(
        f"Index FAISS chargé : {faiss_global_service.index.ntotal} films."
    )

    yield

    logger.info("Arrêt de l'API.")


app = FastAPI(
    title="HorRAGor API",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(router)