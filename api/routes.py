"""
api/routes.py

Module de définition des routes HTTP de l'API HorRAGor.

Ce module centralise l'ensemble des endpoints REST exposés par FastAPI.
Il assure la communication entre le client (interface Streamlit),
les services métiers, la base de données Supabase et l'agent ReAct
implémenté avec LangGraph.

Endpoints disponibles :
    - GET /health
        Vérifie la disponibilité de l'API.

    - GET /film/{tmdb_id}
        Retourne les informations détaillées d'un film.

    - GET /list_real
        Retourne la liste des réalisateurs disponibles.

    - GET /list_genre
        Retourne la liste des genres disponibles.

    - POST /chat
        Traite une requête utilisateur et déclenche le workflow
        de l'agent conversationnel.

    - GET /wikipedia
        Récupère des informations complémentaires depuis Wikipédia.

Responsabilités :
    - Validation des requêtes entrantes via les schémas Pydantic.
    - Appel des services métier.
    - Gestion des réponses HTTP.
    - Gestion des erreurs et des exceptions.

Dépendances principales :
    - fastapi
    - schemas
    - services
    - langgraph

Auteur : Hanna
Projet : HorRAGor
"""

# IMPORT ----------------------------------------------------------
from fastapi import APIRouter
from schemas import (
    HealthResponse,
    FilmDetail,
    FilmShort,
    ChatRequest,

)


router = APIRouter()

# HEALTH ----------------------------------------------------------
@router.get(
    "/health",
    response_model=HealthResponse
)
async def health():

    return HealthResponse(
        status="ok"
    )

# FILMS -----------------------------------------------------------

@router.get("/list_real")
async def list_real():

    return {
        "directors": [
            "Christopher Nolan",
            "Ridley Scott"
        ]
    }

@router.get("/list_genre")
async def list_genre():

    return {
        "genres": [
            "Sci-Fi",
            "Action",
            "Drama"
        ]
    }

@router.get("/film/{tmdb_id}", response_model=FilmShort)
async def get_film(tmdb_id: int):

    return FilmDetail(
        tmdb_id=603,
        title="The Matrix",
        original_language="en"
    )

@router.get("/film/{tmdb_id}", response_model=FilmDetail)
async def get_film(tmdb_id: int):

    return FilmDetail(
        tmdb_id=603,
        title="The Matrix",
        original_language="en"
    )

# CHAT ----------------------------------------------------------
@router.post("/chat")
async def chat(
        request: ChatRequest
):

    return {
        "answer": "Film trouvé."
    }

# WIKIPEDIA ----------------------------------------------------
