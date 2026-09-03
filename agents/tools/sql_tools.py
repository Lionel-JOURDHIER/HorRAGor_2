"""
LangGraph tools for movie filtering.

This module communicates only with Database API.

No direct:
- SQLAlchemy
- PostgreSQL
- database models

All database operations are performed through HTTP requests.
"""

from typing import List, Optional

from langchain_core.tools import tool

from api.modules.database_client import (
    filter_films as api_filter_films,
    get_films_details_by_ids as api_get_films_details,
)

from logger import get_logger, setup_logger


setup_logger()
logger = get_logger("DATABASE_TOOLS")


@tool
async def filter_films_by_criteria(
    tmdb_id: Optional[int] = None,
    realisateur: Optional[str] = None,
    genres_included: Optional[List[str]] = None,
    genres_excluded: Optional[List[str]] = None,
    release_year_min: Optional[int] = None,
    release_year_max: Optional[int] = None,
    tmdb_score_min: Optional[float] = None,
    runtime_min: Optional[int] = None,
    runtime_max: Optional[int] = None,
) -> Optional[List[int]]:
    """
    Filter movies using Database API.

    This tool is used before semantic search.
    It returns a restricted list of TMDB ids.

    Returns:
        - List[int]: eligible movie ids
        - None: no active filters or empty result
    """

    filters = {
        "tmdb_id": tmdb_id,
        "realisateur": realisateur,
        "genres_included": genres_included,
        "genres_excluded": genres_excluded,
        "release_year_min": release_year_min,
        "release_year_max": release_year_max,
        "tmdb_score_min": tmdb_score_min,
        "runtime_min": runtime_min,
        "runtime_max": runtime_max,
    }

    # Remove empty values
    filters = {
        key: value
        for key, value in filters.items()
        if value is not None
    }

    # No business filters
    if not filters:
        logger.info(
            "No filters provided, using full catalog"
        )
        return None

    try:

        ids = await api_filter_films(filters)

        if not ids:

            logger.warning(
                "No films found after filtering"
            )

            return None

        logger.info(
            f"Database API returned {len(ids)} films"
        )

        return ids


    except Exception as e:

        logger.exception(
            f"Database API filtering failed: {e}"
        )

        # Important:
        # Agent continues with FAISS full catalog
        return None



@tool
async def get_films_details(
    tmdb_ids: List[int],
):
    """
    Retrieve detailed movie information.

    Uses Database API instead of direct database access.

    Args:
        tmdb_ids:
            List of TMDB movie identifiers.

    Returns:
        List[FilmDetail]
    """

    if not tmdb_ids:

        logger.info(
            "No TMDB ids provided"
        )

        return []


    try:

        films = await api_get_films_details(
            tmdb_ids
        )

        logger.info(
            f"Retrieved {len(films)} film details"
        )

        return films


    except Exception as e:

        logger.exception(
            f"Failed to retrieve film details: {e}"
        )

        return []