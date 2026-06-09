"""api/main.py
Point d'entrée principal de l'API REST FastAPI pour le projet HorRAGor.

Ce module initialise l'application FastAPI, configure le cycle de vie (lifespan)
du serveur et expose les points d'accès (endpoints) HTTP consommés directement
par l'interface utilisateur.

Fonctionnalités principales :
    - Gestion du cycle de vie ('lifespan') : Déclenche le chargement initial en RAM
      de l'index FAISS et du cache de titres de Supabase au démarrage d'Uvicorn.
    - Gestion des Endpoints pour le Front : Centralisation et inclusion des routes
      REST de l'application (dialogue avec l'agent LangGraph, récupération des films).

Dépendances principales :
    - fastapi (FastAPI, Lifespan)
    - faiss.faiss_service (faiss_global_service)
    - .modules.routes (router)

Auteur/Responsable : Hanna (Epic 3)
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.routes import router

# LOGGER ------------------------------------------------------
from logger import get_logger, setup_logger

setup_logger()

logger = get_logger("MAIN")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Cycle de vie de l'API :
    - Démarrage : charge ou construit l'index FAISS, puis le persiste.
    - Arrêt : libération propre des ressources.
    """
    from database.connection import db_session
    from database.faiss_service import faiss_global_service

    index_path = os.getenv("FAISS_INDEX_PATH", "faiss_data/horragor.index")
    mapping_path = os.getenv("FAISS_MAPPING_PATH", "faiss_data/horragor_mapping.json")

    logger.info(
        f"🚀 [LIFESPAN] Chargement de l'index FAISS... (ID: {id(faiss_global_service)})"
    )
    loaded = faiss_global_service.load_index(index_path, mapping_path)

    # Si le fichier n'a pas pu être chargé ou s'il a chargé 0 élément
    if not loaded or faiss_global_service.index.ntotal == 0:
        logger.info(
            "🔧 Index absent ou vide en RAM. Reconstruction immédiate depuis Supabase..."
        )
        with db_session() as session:
            faiss_global_service.build_index(session)
        faiss_global_service.save_index(index_path, mapping_path)

    logger.info(
        f"✅ [LIFESPAN] Index prêt. Films en RAM : {faiss_global_service.index.ntotal}"
    )
    yield


app = FastAPI(title="HorRAGor API", version="0.1.0", lifespan=lifespan)

app.include_router(router)
