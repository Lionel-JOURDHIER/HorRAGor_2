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
from fastapi import Request

from api.monitoring.langfuse_client import langfuse
from api.routes import router
from api.routes_monitoring import router as monitoring_router

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

@app.middleware("http")
async def langfuse_middleware(request: Request, call_next):
    """
    Middleware FastAPI pour l'instrumentation Langfuse.

    Crée automatiquement une observation Langfuse pour chaque requête HTTP reçue
    par l'API. Cette observation permet de tracer le cycle complet d'une requête
    utilisateur et de mesurer les performances du backend.

    Fonctionnalités :
        - Création d'un span Langfuse pour chaque endpoint appelé.
        - Capture des informations HTTP :
            * méthode HTTP (GET, POST, ...)
            * URL de la requête.
        - Enregistrement du statut de réponse HTTP.
        - Capture des erreurs éventuelles.
        - Envoi des données vers Langfuse après traitement.

    Cette instrumentation constitue la première couche d'observabilité :
        HTTP Request
            ↓
        FastAPI Middleware
            ↓
        Langfuse Observation
            ↓
        Endpoint / LangGraph Agent

    Args:
        request (Request):
            Objet représentant la requête HTTP entrante.

        call_next (Callable):
            Fonction FastAPI permettant de transmettre la requête
            au prochain middleware ou endpoint.

    Returns:
        Response:
            Réponse HTTP générée par l'application FastAPI.

    Notes:
        Le SDK Langfuse v4 utilise une approche basée sur OpenTelemetry.
        La méthode start_as_current_observation() retourne un context manager,
        automatiquement fermé à la sortie du bloc `with`.
    """

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
