"""
Configuration commune des tests pytest.

Ce fichier contient les fixtures partagées par tous les tests.
"""

import pytest
from unittest.mock import Mock


def pytest_addoption(parser):
    """Ajoute une option pour exécuter les tests d'intégration réels."""
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Exécuter les tests d'intégration avec l'API réelle"
    )


def pytest_configure(config):
    """Configure les markers de tests."""
    config.addinivalue_line(
        "markers", "integration: tests d'intégration nécessitant l'API réelle"
    )


@pytest.fixture
def mock_api_response_health():
    """Mock d'une réponse API pour /health."""
    mock = Mock()
    mock.json.return_value = {"status": "ok"}
    mock.status_code = 200
    mock.raise_for_status = Mock()
    return mock


@pytest.fixture
def mock_api_response_genres():
    """Mock d'une réponse API pour /list_genre."""
    mock = Mock()
    mock.json.return_value = {
        "genres": ["Horror", "Thriller", "Mystery", "Drama"]
    }
    mock.status_code = 200
    mock.raise_for_status = Mock()
    return mock


@pytest.fixture
def mock_api_response_directors():
    """Mock d'une réponse API pour /list_real."""
    mock = Mock()
    mock.json.return_value = {
        "directors": ["John Carpenter", "Wes Craven", "James Wan"]
    }
    mock.status_code = 200
    mock.raise_for_status = Mock()
    return mock


@pytest.fixture
def sample_film_detail():
    """Film de test complet."""
    return {
        "tmdb_id": 694,
        "title": "The Shining",
        "release_date": "1980-05-23",
        "runtime": 144,
        "genres": ["Horror", "Thriller"],
        "director": "Stanley Kubrick",
        "tmdb_score": 8.2,
        "overview": "A family heads to an isolated hotel for the winter..."
    }


@pytest.fixture
def sample_film_short():
    """Film de test format court."""
    return {
        "tmdb_id": 694,
        "title": "The Shining",
        "release_date": "1980-05-23",
        "genres": ["Horror", "Thriller"],
        "tmdb_score": 8.2
    }


@pytest.fixture
def mock_chat_response_success():
    """Mock d'une réponse chat réussie."""
    mock = Mock()
    mock.json.return_value = {
        "answer": "L'agent de recommandation est en cours de développement.",
        "steps": [],
        "recommendations": []
    }
    mock.status_code = 200
    mock.raise_for_status = Mock()
    return mock


@pytest.fixture
def sample_filters():
    """Filtres de recherche de test."""
    return {
        "realisateur": "John Carpenter",
        "genres_included": ["Horror"],
        "genres_excluded": ["Comedy"],
        "release_year_min": 1970,
        "release_year_max": 2020,
        "tmdb_score_min": 7.0,
        "runtime_min": 80,
        "runtime_max": 150
    }
