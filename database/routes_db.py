"""
database/routes_db.py

Module de définition des routes HTTP de l'API HorRAGor.

communication entre les clients (AI API ou interface d'administration)
et la base de données.

Cette API est dédiée exclusivement à l'accès aux données.
Elle ne contient aucune logique d'agent, de LangGraph ou de génération LLM.

Endpoints disponibles :
    - GET /health
        Vérifie la disponibilité de l'API.

    - GET /film/{tmdb_id}
        Retourne les informations détaillées d'un film.

    - GET /list_real
        Retourne la liste des réalisateurs disponibles.

    - GET /list_genre
        Retourne la liste des genres disponibles.


Responsabilités :
    - Validation des requêtes entrantes via les schémas Pydantic.
    - Appel des services métier.
    - Gestion des réponses HTTP.
    - Gestion des erreurs et des exceptions.

Dépendances principales :
    - fastapi
    - pydantic schemas
    - sqlalchemy
    - database services

Auteur : Hanna
Projet : HorRAGor
"""

# IMPORT ----------------------------------------------------------
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from typing import List

from shared.schemas import (
    DirectorsResponse,
    ErrorResponse,
    FilmDetail,
    GenresResponse,
    HealthResponse,
    FilmFilterRequest,
    FilmIdsRequest
)

from database.connection import get_db
from database.queries import get_all_directors, get_all_genres, get_film_details_by_id, get_filtered_ids, get_films_details_by_ids

# LOGGER ------------------------------------------------------
from logger import get_logger, setup_logger

setup_logger()
logger = get_logger("ROUTES")

# ROUTER ---------------------------------------------------------
router = APIRouter()


# HEALTH ----------------------------------------------------------
@router.get(
    "/health",
    response_model=HealthResponse,
    responses={500: {"model": ErrorResponse}},
    tags=["Health"],
)
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
@router.get(
    "/list_real",
    response_model=DirectorsResponse,
    responses={500: {"model": ErrorResponse}},
    tags=["Metadata"],
)
async def list_real(session: Session = Depends(get_db)):
    """Return list of directors."""
    try:
        directors = get_all_directors(session)
        return directors
    except Exception as e:
        logger.error(f"Failed to retrieve directors: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve directors: {str(e)}"
        )


@router.get(
    "/list_genre",
    response_model=GenresResponse,
    responses={500: {"model": ErrorResponse}},
    tags=["Metadata"],
)
async def list_genre(session: Session = Depends(get_db)):
    """Return list of genres."""
    try:
        genres = get_all_genres(session)
        return genres
    except Exception as e:
        logger.error(f"Failed to retrieve genres: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve genres: {str(e)}"
        )


# FILMS -----------------------------------------------------------
@router.get(
    "/film/{tmdb_id}",
    response_model=FilmDetail,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    tags=["Films"],
)
async def get_film_detail(tmdb_id: int, session: Session = Depends(get_db)):
    """Return full movie details by TMDB id."""
    try:
        film = get_film_details_by_id(session, tmdb_id)
        if film is None:
            logger.error("Film is None")
            raise HTTPException(status_code=404, detail="Film not found")

        return film

    except HTTPException:
        logger.error("Error get_film_details_by_id")
        raise

    except Exception as e:
        logger.error(f"Failed to retrieve film: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve film: {str(e)}"
        )

@router.post(
    "/filter_films",
    tags=["Films"],
)
async def filter_films(
    request: FilmFilterRequest,
    session: Session = Depends(get_db),
):
    """
    Filter films by business criteria.
    Returns list of TMDB ids.
    """

    try:
        ids = get_filtered_ids(
            session=session,
            tmdb_id=request.tmdb_id,
            realisateur=request.realisateur,
            genres_included=request.genres_included,
            genres_excluded=request.genres_excluded,
            release_year_min=request.release_year_min,
            release_year_max=request.release_year_max,
            tmdb_score_min=request.tmdb_score_min,
            runtime_min=request.runtime_min,
            runtime_max=request.runtime_max,
        )

        return {
            "tmdb_ids": ids or []
        }

    except Exception as e:
        logger.exception(
            "Failed to filter films"
        )

        raise HTTPException(
            status_code=500,
            detail=f"Failed to filter films: {str(e)}"
        )

@router.post(
    "/films/details",
    response_model=list[FilmDetail],
    tags=["Films"],
)
async def films_details(
    request: FilmIdsRequest,
    session: Session = Depends(get_db),
):
    """
    Retrieve multiple films details by TMDB ids.
    """

    try:
        films = get_films_details_by_ids(
            session,
            request.tmdb_ids
        )

        return films

    except Exception as e:
        logger.exception(
            "Failed to retrieve films details"
        )

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
    

@router.post(
    "/films/short",
    tags=["Films"],
)
async def films_short(
    request: FilmIdsRequest,
    session: Session = Depends(get_db),
):
    try:
        return get_films_short_by_ids(
            session,
            request.tmdb_ids,
        )

    except Exception as e:
        logger.exception("Failed to retrieve films")
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )