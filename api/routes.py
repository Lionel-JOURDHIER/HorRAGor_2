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
from fastapi import APIRouter, HTTPException

from schemas import (
    HealthResponse,
    FilmDetail,
    FilmShort,
    ChatRequest,
    ChatResponse,
    WikipediaResponse,
    DirectorsResponse,
    GenresResponse,
)


router = APIRouter()

# HEALTH ----------------------------------------------------------
@router.get("/health", response_model=HealthResponse, tags=["System"])
async def health():
    """Check API availability."""
    return HealthResponse(status="ok")

# LISTS -----------------------------------------------------------
@router.get("/list_real", response_model=DirectorsResponse, tags=["Metadata"])
async def list_real():
    """Return list of directors."""
    return DirectorsResponse(directors=["Christopher Nolan", "Ridley Scott"])


@router.get("/list_genre", response_model=GenresResponse, tags=["Metadata"])
async def list_genre():
    """Return list of genres."""
    return GenresResponse(genres=["Sci-Fi", "Action", "Drama"])

# FILMS -----------------------------------------------------------
@router.get( "/film/{tmdb_id}", response_model=FilmDetail, tags=["Films"])
async def get_film_detail(tmdb_id: int):
    """ Return full movie details by TMDB id."""
    return FilmDetail( tmdb_id=tmdb_id, title="The Matrix", original_language="en")

# CHAT ----------------------------------------------------------
@router.post("/chat", response_model=ChatResponse, tags=["Agent"])
async def chat(request: ChatRequest):
    """ Main endpoint for ReAct agent interaction."""
    # TODO: replace with LangGraph call
    return ChatResponse(
        answer=f"Received: {request.message}",
        steps=[],
        recommendations=[
            FilmShort(
                tmdb_id=603,
                title="The Matrix",
                release_date=None,
                genres=["Sci-Fi"],
                tmdb_score=8.7
            )
        ]
    )

# WIKIPEDIA ----------------------------------------------------
@router.get("/wikipedia/{tmdb_id}", response_model=WikipediaResponse, tags=["Wikipedia"])
async def wikipedia(tmdb_id: int):
    """ Retrieve movie info from Wikipedia using TMDB ID."""

    # TODO: connect Wikipedia tool
    return WikipediaResponse(
        title="The Matrix",
        synopsis="Wikipedia data not implemented yet.",
        source_url=None
    )