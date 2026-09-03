import os
import httpx

from shared.schemas import FilmDetail,FilmShort


DATABASE_API_URL = os.getenv(
    "DATABASE_API_URL",
    "http://database_api:8000"
)


async def get_film(
    tmdb_id: int
) -> FilmDetail:
    """
    Retrieve one film from Database API.
    """

    async with httpx.AsyncClient() as client:

        response = await client.get(
            f"{DATABASE_API_URL}/db/film/{tmdb_id}"
        )

    response.raise_for_status()

    return FilmDetail.model_validate(
        response.json()
    )


async def get_directors():
    """
    Retrieve directors list.
    """

    async with httpx.AsyncClient() as client:

        response = await client.get(
            f"{DATABASE_API_URL}/db/list_real"
        )

    response.raise_for_status()

    return response.json()



async def get_genres():
    """
    Retrieve genres list.
    """

    async with httpx.AsyncClient() as client:

        response = await client.get(
            f"{DATABASE_API_URL}/db/list_genre"
        )

    response.raise_for_status()

    return response.json()



async def filter_films(
    filters: dict
) -> list[int]:
    """
    Filter films through Database API.

    Returns:
        List of tmdb ids.
    """

    async with httpx.AsyncClient() as client:

        response = await client.post(
            f"{DATABASE_API_URL}/db/filter_films",
            json=filters,
        )

    response.raise_for_status()

    return response.json().get(
        "tmdb_ids",
        []
    )



async def get_films_details_by_ids(
    tmdb_ids: list[int],
) -> list[FilmDetail]:
    """
    Retrieve multiple films details from Database API.
    """

    if not tmdb_ids:
        return []


    async with httpx.AsyncClient() as client:

        response = await client.post(
            f"{DATABASE_API_URL}/db/films/details",
            json={
                "tmdb_ids": tmdb_ids
            },
        )


    response.raise_for_status()


    films = response.json()


    return [
        FilmDetail.model_validate(film)
        for film in films
    ]


async def get_films_short_by_ids(
    tmdb_ids: list[int],
) -> list[FilmShort]:

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{DATABASE_API_URL}/db/films/short",
            json={
                "tmdb_ids": tmdb_ids
            }
        )

    response.raise_for_status()

    return [
        FilmShort.model_validate(item)
        for item in response.json()
    ]