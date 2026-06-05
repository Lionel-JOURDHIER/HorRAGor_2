from datetime import date
from unittest.mock import MagicMock

import pytest

from api.schemas import DirectorsResponse, FilmDetail, FilmShort, GenresResponse
from database.queries import (
    get_all_directors,
    get_all_genres,
    get_film_details_by_id,
    get_films_short_by_ids,
)


@pytest.fixture
def mock_session():
    """Fixture qui fournit une session SQLAlchemy mockée."""
    return MagicMock()


def test_get_film_details_by_id_success(mock_session):
    """Vérifie l'extraction complète et le mapping d'un film existant."""
    # 1. Préparation des faux objets de table (MPD)
    mock_film = MagicMock(
        tmdb_id=898555,
        title="Machine Learning",
        original_title="ML",
        original_language="en",
        release_date=date(2021, 11, 13),
        runtime=683,
        status="Released",
        overview="Synopsis text",
        tagline="Tagline",
        poster_path="/path.jpg",
        budget=2500,
        revenue=10000,
        director_id=1,
        id_collection=1,
    )

    mock_s_tmdb = MagicMock(vote_average=10.0, vote_count=1)
    mock_s_imdb = MagicMock(average_rating=8.5, num_votes=100)
    mock_s_rt = MagicMock(rt_tomatometer=90, rt_audience_score=88)

    # ⚡ FIX ICI : On assigne l'attribut .name et .collection_name explicitement
    mock_real = MagicMock()
    mock_real.name = "Christopher Nolan"

    mock_coll = MagicMock()
    mock_coll.collection_name = "AI Collection"

    # Simulation du résultat du premier .execute().first() (Tuple Merise)
    mock_session.execute.return_value.first.return_value = (
        mock_film,
        mock_s_tmdb,
        mock_s_imdb,
        mock_s_rt,
        mock_real,
        mock_coll,
    )

    # Simulation du résultat pour la requête des genres (.scalars().all())
    mock_session.execute.return_value.scalars.return_value.all.return_value = [
        "Science Fiction",
        "Horror",
    ]

    # 2. Appel de la fonction
    result = get_film_details_by_id(mock_session, 898555)

    # 3. Assertions
    assert isinstance(result, FilmDetail)
    assert result.title == "Machine Learning"
    assert result.genres == ["Science Fiction", "Horror"]
    assert result.realisateur == "Christopher Nolan"
    assert result.director == "Christopher Nolan"
    assert (
        result.aggregated_score == 91.66666666666667
    )  # Moyenne de (100 + 85 + 90) / 3


def test_get_film_details_by_id_not_found(mock_session):
    """Vérifie que la fonction retourne None si le film n'existe pas."""
    mock_session.execute.return_value.first.return_value = None

    result = get_film_details_by_id(mock_session, 999999)
    assert result is None


def test_get_films_short_by_ids_no_records(mock_session):
    """Vérifie le comportement de get_films_short_by_ids lorsque la liste d'IDs

    est transmise, mais qu'aucun film correspondant n'existe en base de données.
    Cible spécifiquement la condition 'if not records:'.
    """
    # On simule le fait que la requête principale ne trouve rien dans Supabase
    mock_session.execute.return_value.all.return_value = []

    # Appel de la fonction avec un ID fictif
    result = get_films_short_by_ids(mock_session, [999999])

    # Assertions : la fonction doit couper court et renvoyer une liste vide
    assert result == []
    # On s'assure que session.execute n'a été appelé qu'une seule fois (la requête des genres n'est jamais déclenchée)
    assert mock_session.execute.call_count == 1


def test_get_all_directors(mock_session):
    """Vérifie la récupération de la liste des réalisateurs."""
    mock_session.execute.return_value.scalars.return_value.all.return_value = [
        "Nolan",
        "Spielberg",
    ]

    result = get_all_directors(mock_session)
    assert isinstance(result, DirectorsResponse)
    assert result.directors == ["Nolan", "Spielberg"]


def test_get_all_genres(mock_session):
    """Vérifie la récupération de la liste des genres."""
    mock_session.execute.return_value.scalars.return_value.all.return_value = [
        "Action",
        "Sci-Fi",
    ]

    result = get_all_genres(mock_session)
    assert isinstance(result, GenresResponse)
    assert result.genres == ["Action", "Sci-Fi"]


def test_get_films_short_by_ids(mock_session):
    """Vérifie le mapping compact au format FilmShort (Retour FAISS)."""
    mock_film = MagicMock(
        tmdb_id=898555, title="Machine Learning", release_date=date(2021, 11, 13)
    )
    mock_score = MagicMock(vote_average=10.0)

    # Mock de la première requête (Films + Scores)
    mock_session.execute.return_value.all.side_effect = [
        [(mock_film, mock_score)],  # Retour 1 : Liste de films
        [(898555, "Science Fiction")],  # Retour 2 : Liste de genres associés
    ]

    result = get_films_short_by_ids(mock_session, [898555])

    assert len(result) == 1
    assert isinstance(result[0], FilmShort)
    assert result[0].title == "Machine Learning"
    assert result[0].genres == ["Science Fiction"]
    assert result[0].tmdb_score == 10.0


def test_get_films_short_by_ids_empty(mock_session):
    """Vérifie qu'une liste d'IDs vide retourne immédiatement une liste vide."""
    result = get_films_short_by_ids(mock_session, [])
    assert result == []
