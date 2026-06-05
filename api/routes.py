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
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from agents.tools.wiki_tools import wikipedia_search

from database.connection import get_db
from database.queries import get_film_details_by_id, get_all_directors, get_all_genres

from api.schemas import (
    HealthResponse,
    FilmDetail,
    FilmShort,
    ChatRequest,
    ChatResponse,
    WikipediaResponse,
    DirectorsResponse,
    GenresResponse,
    ErrorResponse
)

# LOGGER ------------------------------------------------------
from logger import setup_logger, get_logger
setup_logger()
logger = get_logger("ROUTES")

# ROUTER ---------------------------------------------------------
router = APIRouter()


# HEALTH ----------------------------------------------------------
@router.get("/health", response_model=HealthResponse, responses={500: {"model": ErrorResponse}}, tags=["System"])
async def health(db: Session = Depends(get_db)):
    """Check API availability."""
    try:
        db.execute(text("SELECT 1"))
        logger.info("HEATH SUSSESS")
        return HealthResponse(status="ok")
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

# LISTS -----------------------------------------------------------
@router.get("/list_real", response_model=DirectorsResponse, responses={500: {"model": ErrorResponse}}, tags=["Metadata"])
async def list_real(session: Session = Depends(get_db)):
    """Return list of directors."""
    try:
        directors = get_all_directors(session)
        return directors
    except Exception as e:
        logger.error(f"Failed to retrieve directors: {str(e)}")
        raise HTTPException( status_code=500, detail=f"Failed to retrieve directors: {str(e)}")
        


@router.get("/list_genre", response_model=GenresResponse, responses={500: {"model": ErrorResponse}}, tags=["Metadata"])
async def list_genre(session: Session = Depends(get_db)):
    """Return list of genres."""
    try:
        genres = get_all_genres(session)
        return genres
    except Exception as e:
        logger.error(f"Failed to retrieve genres: {str(e)}")
        raise HTTPException( status_code=500, detail=f"Failed to retrieve genres: {str(e)}")

# FILMS -----------------------------------------------------------
@router.get( "/film/{tmdb_id}", response_model=FilmDetail, responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},tags=["Films"])
async def get_film_detail(tmdb_id: int, session: Session = Depends(get_db)):
    """ Return full movie details by TMDB id."""
    try:
        film = get_film_details_by_id(session, tmdb_id)
        if film is None:
            logger.error("Film is None")
            raise HTTPException( status_code=404, detail="Film not found")

        return film

    except HTTPException:
        logger.error("Error get_film_details_by_id")
        raise

    except Exception as e:
        logger.error(f"Failed to retrieve film: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve film: {str(e)}"
        )


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
@router.get("/wikipedia/{tmdb_id}", response_model=WikipediaResponse, responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}, tags=["Wikipedia"])
async def wikipedia(tmdb_id: int, session: Session = Depends(get_db)):
    """ Retrieve movie info from Wikipedia using TMDB ID."""
    try:
        film = get_film_details_by_id(session, tmdb_id)
        if not film:
            raise HTTPException(status_code=404, detail="Film not found")
        
        title = film.title
        year = film.release_date.year if film.release_date else None

        response_wiki = wikipedia_search.invoke({"title": title,"year": year})
        logger.info("Sussesfully Retrieve movie info from Wikipedia")
        return response_wiki

    except Exception as e:
        logger.error(f"Failed to retrieve film: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve film: {str(e)}")