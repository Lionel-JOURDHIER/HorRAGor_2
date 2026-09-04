from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from api.modules.database_client import (
    filter_films,
    get_directors,
    get_film,
    get_films_details_by_ids,
    get_films_short_by_ids,
    get_genres,
)
from shared.schemas import FilmDetail, FilmShort


def mock_response(json_data, status_code=200):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_data

    if status_code >= 400:
        import httpx

        response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "HTTP error",
            request=MagicMock(),
            response=response,
        )

    return response


@pytest.mark.asyncio
async def test_get_film():
    film_data = {
        "tmdb_id": 115128,
        "title": "Creature of the Walking Dead",
        "original_title": "Creature of the Walking Dead",
        "original_language": "en",
        "release_date": "1965-06-15",
        "runtime": 72,
        "status": "Released",
        "synopsis": "A horror movie.",
        "tagline": "Horror-Cade of Excitement",
        "genres": ["Horror", "Science Fiction"],
        "poster_url": None,
        "backdrop_url": None,
        "budget": None,
        "revenue": None,
        "tmdb_score": 3.3,
        "tmdb_vote_count": 16,
        "imdb_score": 2.9,
        "imdb_vote_count": 346,
        "rotten_tomatometer": None,
        "rotten_audience_score": 0,
        "aggregated_score": 31.0,
        "collection": None,
        "director": None,
        "realisateur": None,
    }

    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value=mock_response(film_data))

    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "api.modules.database_client.httpx.AsyncClient",
        return_value=mock_client,
    ):
        result = await get_film(115128)

    assert isinstance(result, FilmDetail)
    assert result.tmdb_id == 115128
    assert result.title == "Creature of the Walking Dead"

    mock_client.get.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_film_error():
    response = mock_response(
        {"detail": "Film not found"},
        status_code=404,
    )

    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value=response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "api.modules.database_client.httpx.AsyncClient",
        return_value=mock_client,
    ):
        with pytest.raises(Exception):
            await get_film(999999)


@pytest.mark.asyncio
async def test_get_directors():
    directors = [
        "Christopher Nolan",
        "Steven Spielberg",
    ]

    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value=mock_response(directors))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "api.modules.database_client.httpx.AsyncClient",
        return_value=mock_client,
    ):
        result = await get_directors()

    assert result == directors
    mock_client.get.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_genres():
    genres = [
        "Horror",
        "Science Fiction",
        "Drama",
    ]

    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value=mock_response(genres))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "api.modules.database_client.httpx.AsyncClient",
        return_value=mock_client,
    ):
        result = await get_genres()

    assert result == genres
    mock_client.get.assert_awaited_once()


@pytest.mark.asyncio
async def test_filter_films():
    response_data = {"tmdb_ids": [115128, 123456, 789012]}

    mock_client = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_response(response_data))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    filters = {"genres": ["Horror"]}

    with patch(
        "api.modules.database_client.httpx.AsyncClient",
        return_value=mock_client,
    ):
        result = await filter_films(filters)

    assert result == [115128, 123456, 789012]

    mock_client.post.assert_awaited_once()


@pytest.mark.asyncio
async def test_filter_films_without_ids():
    mock_client = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_response({}))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "api.modules.database_client.httpx.AsyncClient",
        return_value=mock_client,
    ):
        result = await filter_films({})

    assert result == []


@pytest.mark.asyncio
async def test_get_films_details_by_ids_empty():
    result = await get_films_details_by_ids([])

    assert result == []


@pytest.mark.asyncio
async def test_get_films_details_by_ids():
    films = [
        {
            "tmdb_id": 115128,
            "title": "Film 1",
            "original_title": "Film 1",
            "original_language": "en",
            "release_date": "1965-06-15",
            "runtime": 72,
            "status": "Released",
            "synopsis": "Test",
            "tagline": None,
            "genres": ["Horror"],
            "poster_url": None,
            "backdrop_url": None,
            "budget": None,
            "revenue": None,
            "tmdb_score": 3.3,
            "tmdb_vote_count": 10,
            "imdb_score": 2.9,
            "imdb_vote_count": 20,
            "rotten_tomatometer": None,
            "rotten_audience_score": None,
            "aggregated_score": None,
            "collection": None,
            "director": None,
            "realisateur": None,
        }
    ]

    mock_client = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_response(films))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "api.modules.database_client.httpx.AsyncClient",
        return_value=mock_client,
    ):
        result = await get_films_details_by_ids([115128])

    assert len(result) == 1
    assert isinstance(result[0], FilmDetail)
    assert result[0].tmdb_id == 115128


@pytest.mark.asyncio
async def test_get_films_short_by_ids():
    films = [
        {
            "tmdb_id": 115128,
            "title": "Film 1",
            "release_date": "1965-06-15",
            "genres": ["Horror"],
            "tmdb_score": 3.3,
            "similarity_score": 0.95,
            "poster_url": None,
            "synopsis": "Test",
        }
    ]

    mock_client = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_response(films))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "api.modules.database_client.httpx.AsyncClient",
        return_value=mock_client,
    ):
        result = await get_films_short_by_ids([115128])

    assert len(result) == 1
    assert isinstance(result[0], FilmShort)
    assert result[0].tmdb_id == 115128
    assert result[0].title == "Film 1"
