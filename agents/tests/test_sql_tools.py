from collections import namedtuple
from datetime import date, datetime
from unittest.mock import MagicMock, patch

from agents.tools.sql_tools import (
    _build_filtered_ids,
    filter_films_by_criteria,
    get_films_details_by_ids,
)
from api.schemas import FilmDetail

# Structure nommée pour simuler les lignes Row retournées par SQLAlchemy
SQLRowSimulation = namedtuple(
    "Row", ["Film", "director_name", "tmdb_score", "tmdb_vote_count", "genres_csv"]
)


class FakeFilm:
    """Objet factice stable imitant le modèle SQLAlchemy Film."""

    tmdb_id = 666
    title = "L'Armée des Morts"
    original_title = "Dawn of the Dead"
    original_language = "en"
    release_date = date(2004, 3, 31)
    runtime = 101
    status = "Released"
    overview = "Un groupe de survivants se réfugie dans un centre commercial."
    tagline = "Quand il n'y a plus de place en enfer..."
    poster_path = "/path.jpg"
    backdrop_path = "/back.jpg"
    budget = 26000000
    revenue = 102000000
    imdb_score = 7.3


# ==============================================================================
# TESTS POUR get_films_details_by_ids
# ==============================================================================


def test_get_films_details_by_ids_success():
    """Vérifie le mapping complet et le split de la chaîne CSV des genres."""
    mock_row = SQLRowSimulation(
        Film=FakeFilm(),
        director_name="Zack Snyder",
        tmdb_score=7.2,
        tmdb_vote_count=3500,
        genres_csv="Action,Horror",
    )

    with patch("agents.tools.sql_tools.db_session") as mock_db_session:
        mock_session = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_session
        mock_session.execute.return_value.all.return_value = [mock_row]

        result = get_films_details_by_ids([666])

        assert len(result) == 1
        detail = result[0]
        assert isinstance(detail, FilmDetail)
        assert detail.tmdb_id == 666
        assert detail.title == "L'Armée des Morts"
        assert detail.genres == ["Action", "Horror"]
        assert detail.director == "Zack Snyder"
        assert detail.release_date == date(2004, 3, 31)


def test_get_films_details_by_ids_empty_input():
    """L'envoi d'une liste vide doit court-circuiter directement à un tableau vide."""
    result = get_films_details_by_ids([])
    assert result == []


def test_get_films_details_by_ids_no_genres_and_datetime():
    """Couvre les branches sans genres et la conversion d'un type non-date (ex: datetime)."""
    mock_film = FakeFilm()
    # Simulation d'un datetime complet pour tester le fallback .date() de la ligne 234
    mock_film.release_date = datetime(2004, 3, 31, 0, 0, 0)

    mock_row = SQLRowSimulation(
        Film=mock_film,
        director_name="Zack Snyder",
        tmdb_score=7.2,
        tmdb_vote_count=3500,
        genres_csv=None,  # Pas de genres associés
    )

    with patch("agents.tools.sql_tools.db_session") as mock_db_session:
        mock_session = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_session
        mock_session.execute.return_value.all.return_value = [mock_row]

        result = get_films_details_by_ids([666])
        assert result[0].genres == []
        assert result[0].release_date == date(2004, 3, 31)


def test_get_films_details_by_ids_missing_release_date():
    """Couvre le cas où release_date est absent ou None."""
    mock_film = FakeFilm()
    mock_film.release_date = None

    mock_row = SQLRowSimulation(
        Film=mock_film,
        director_name="Zack Snyder",
        tmdb_score=7.2,
        tmdb_vote_count=3500,
        genres_csv="Horror",
    )

    with patch("agents.tools.sql_tools.db_session") as mock_db_session:
        mock_session = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_session
        mock_session.execute.return_value.all.return_value = [mock_row]

        result = get_films_details_by_ids([666])
        assert result[0].release_date is None


def test_get_films_details_by_ids_exception():
    """Force le bloc except à s'exécuter pour couvrir la gestion globale des erreurs."""
    with patch("agents.tools.sql_tools.db_session") as mock_db_session:
        mock_db_session.side_effect = Exception("Database Failure")

        result = get_films_details_by_ids([666])
        assert result == []


# ==============================================================================
# TESTS POUR FILTER_FILMS_BY_CRITERIA & INTERNES
# ==============================================================================


def test_build_filtered_ids_no_filters_active():
    """Vérifie que la fonction renvoie None si aucun filtre n'est activé."""
    mock_session = MagicMock()
    result = _build_filtered_ids(mock_session)
    assert result is None


def test_filter_films_by_criteria_success():
    """Parcourt l'intégralité des branches d'injection de conditions SQL (Tous les IFs)."""
    with patch("agents.tools.sql_tools.db_session") as mock_db_session:
        mock_session = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_session

        # Simule le retour de execute().scalars().all()
        mock_session.execute.return_value.scalars.return_value.all.return_value = [
            11,
            22,
        ]

        # On passe TOUS les arguments possibles pour couvrir chaque condition 'if'
        result = filter_films_by_criteria.func(
            tmdb_id=666,
            realisateur="Snyder",
            genres_included=["Horror"],
            genres_excluded=[
                "Comedy",
                "Romance",
            ],  # Liste multiple pour boucler sur l'exclusion
            release_year_min=2000,
            release_year_max=2010,
            tmdb_score_min=6.5,
            runtime_min=90,
            runtime_max=180,
        )

        assert result == [11, 22]


def test_filter_films_by_criteria_empty_pool_correct():
    """Couvre la branche 'if not ids:' avec un filtre actif mais sans résultats."""
    with patch("agents.tools.sql_tools.db_session") as mock_db_session:
        mock_session = MagicMock()
        mock_db_session.return_value.__enter__.return_value = mock_session

        # On force le retour de la DB à être une liste vide []
        mock_session.execute.return_value.scalars.return_value.all.return_value = []

        # On passe un critère pour activer la logique et atteindre la ligne de log du pool vide
        result = filter_films_by_criteria.func(realisateur="Inexistant")

        assert result == []
