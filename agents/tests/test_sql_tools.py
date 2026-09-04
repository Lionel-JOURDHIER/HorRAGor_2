from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
from agents.tools.sql_tools import (
    filter_films_by_criteria,
    get_films_details,
)
from shared.schemas import FilmDetail

# ==============================================================================
# TESTS POUR get_films_details
# ==============================================================================


@pytest.mark.asyncio
async def test_get_films_details_success():
    """Vérifie la récupération des détails via la Database API."""
    film = FilmDetail(
        tmdb_id=666,
        title="L'Armée des Morts",
        original_title="Dawn of the Dead",
        original_language="en",
        release_date=date(2004, 3, 31),
        runtime=101,
        status="Released",
        synopsis="Un groupe de survivants se réfugie dans un centre commercial.",
        tagline="Quand il n'y a plus de place en enfer...",
        poster_url="/path.jpg",
        backdrop_url="/back.jpg",
        budget=26000000,
        revenue=102000000,
        imdb_score=7.3,
        tmdb_score=7.2,
        tmdb_vote_count=3500,
        genres=["Action", "Horror"],
        director="Zack Snyder",
    )

    with patch(
        "agents.tools.sql_tools.api_get_films_details",
        new_callable=AsyncMock,
        return_value=[film],
    ) as mock_api:
        result = await get_films_details.coroutine([666])

        assert len(result) == 1
        detail = result[0]
        assert isinstance(detail, FilmDetail)
        assert detail.tmdb_id == 666
        assert detail.title == "L'Armée des Morts"
        assert detail.genres == ["Action", "Horror"]
        assert detail.director == "Zack Snyder"
        assert detail.release_date == date(2004, 3, 31)

        mock_api.assert_awaited_once_with([666])


@pytest.mark.asyncio
async def test_get_films_details_empty_input():
    """L'envoi d'une liste vide doit court-circuiter directement à un tableau vide."""
    result = await get_films_details.coroutine([])

    assert result == []


@pytest.mark.asyncio
async def test_get_films_details_empty_result():
    """Couvre le cas où la Database API ne retourne aucun film."""
    with patch(
        "agents.tools.sql_tools.api_get_films_details",
        new_callable=AsyncMock,
        return_value=[],
    ) as mock_api:
        result = await get_films_details.coroutine([666])

        assert result == []
        mock_api.assert_awaited_once_with([666])


@pytest.mark.asyncio
async def test_get_films_details_exception():
    """Force le bloc except à s'exécuter pour couvrir la gestion des erreurs."""
    with patch(
        "agents.tools.sql_tools.api_get_films_details",
        new_callable=AsyncMock,
        side_effect=Exception("Database API Failure"),
    ):
        result = await get_films_details.coroutine([666])

        assert result == []


# ==============================================================================
# TESTS POUR FILTER_FILMS_BY_CRITERIA
# ==============================================================================


@pytest.mark.asyncio
async def test_filter_films_by_criteria_no_filters_active():
    """Vérifie que la fonction renvoie None si aucun filtre n'est activé."""
    result = await filter_films_by_criteria.coroutine()

    assert result is None


@pytest.mark.asyncio
async def test_filter_films_by_criteria_success():
    """Vérifie la transmission de tous les critères à la Database API."""
    with patch(
        "agents.tools.sql_tools.api_filter_films",
        new_callable=AsyncMock,
        return_value=[11, 22],
    ) as mock_api:
        # On passe TOUS les arguments possibles pour couvrir chaque condition.
        result = await filter_films_by_criteria.coroutine(
            tmdb_id=666,
            realisateur="Snyder",
            genres_included=["Horror"],
            genres_excluded=[
                "Comedy",
                "Romance",
            ],
            release_year_min=2000,
            release_year_max=2010,
            tmdb_score_min=6.5,
            runtime_min=90,
            runtime_max=180,
        )

        assert result == [11, 22]

        mock_api.assert_awaited_once_with(
            {
                "tmdb_id": 666,
                "realisateur": "Snyder",
                "genres_included": ["Horror"],
                "genres_excluded": [
                    "Comedy",
                    "Romance",
                ],
                "release_year_min": 2000,
                "release_year_max": 2010,
                "tmdb_score_min": 6.5,
                "runtime_min": 90,
                "runtime_max": 180,
            }
        )


@pytest.mark.asyncio
async def test_filter_films_by_criteria_empty_pool_correct():
    """Couvre la branche 'if not ids:' avec un filtre actif mais sans résultats."""
    with patch(
        "agents.tools.sql_tools.api_filter_films",
        new_callable=AsyncMock,
        return_value=[],
    ) as mock_api:
        # On force le retour de la Database API à être une liste vide []
        result = await filter_films_by_criteria.coroutine(realisateur="Inexistant")

        assert result is None

        mock_api.assert_awaited_once_with({"realisateur": "Inexistant"})


@pytest.mark.asyncio
async def test_filter_films_by_criteria_exception():
    """Force le bloc except à s'exécuter pour couvrir la gestion des erreurs."""
    with patch(
        "agents.tools.sql_tools.api_filter_films",
        new_callable=AsyncMock,
        side_effect=Exception("Database API Failure"),
    ):
        result = await filter_films_by_criteria.coroutine(realisateur="Snyder")

        assert result is None
