"""
Tests unitaires pour le pipeline ETL 'populate.py'.
Garantit une couverture à 100% en interceptant correctement l'appel next(get_db()).
"""

from unittest.mock import MagicMock, patch

import pytest

import database.populate as populate


@patch("database.populate.OLLAMA_CLIENT_EMBEDD")
def test_generate_local_embedding_nominal(mock_ollama_client):
    """Vérifie que la fonction appelle correctement l'inférence Ollama."""
    # ✅ On configure directement la méthode de l'instance mockée
    mock_ollama_client.embed_query.return_value = [0.1] * 1024

    # Appel de ta fonction
    vector = populate.generate_local_embedding("Inception")

    # Assertions
    assert len(vector) == 1024
    assert vector[0] == 0.1


def test_generate_local_embedding_edge_cases():
    """Valide la gestion des chaînes vides ou None sans instancier Ollama."""
    vec_none = populate.generate_local_embedding(None)
    vec_empty = populate.generate_local_embedding("   ")

    assert len(vec_none) == 1024
    assert len(vec_empty) == 1024
    assert vec_none == [0.0] * 1024


@patch("database.populate.engine")
@patch("database.populate.get_db")
@patch("database.populate.generate_local_embedding")
@patch("database.populate.fetch_already_vectorized_ids")
@patch("database.populate.fetch_source_films")
def test_run_pipeline_nominal_flow(
    mock_fetch_src, mock_fetch_vec, mock_embed, mock_get_db, mock_engine
):
    """Teste le flux complet avec un film à traiter et aucun doublon."""
    mock_session = MagicMock()

    # Configuration du Context Manager retourné lors de l'appel à next()
    mock_context = MagicMock()
    mock_context.__enter__.return_value = mock_session

    # next(mock_get_db()) va maintenant renvoyer directement notre mock_context contrôlé
    mock_get_db.return_value.__next__.return_value = mock_context

    # Simulation du vecteur renvoyé par l'inférence
    mock_embed.return_value = [0.2] * 1024

    # Données simulées
    mock_row = MagicMock()
    mock_row.tmdb_id = 999
    mock_row.title = "Interstellar"
    mock_row.overview = "Voyage spatial."

    mock_fetch_src.return_value = [mock_row]
    mock_fetch_vec.return_value = set()

    populate.run_pipeline()

    assert mock_session.merge.called
    assert mock_session.commit.called


@patch("database.populate.engine")
@patch("database.populate.get_db")
@patch("database.populate.fetch_already_vectorized_ids")
@patch("database.populate.fetch_source_films")
def test_run_pipeline_deduplicated(
    mock_fetch_src, mock_fetch_vec, mock_get_db, mock_engine
):
    """Vérifie qu'un film déjà présent dans 'film_embeddings' est ignoré (DRY)."""
    mock_session = MagicMock()
    mock_context = MagicMock()
    mock_context.__enter__.return_value = mock_session
    mock_get_db.return_value.__next__.return_value = mock_context

    mock_row = MagicMock()
    mock_row.tmdb_id = 999
    mock_row.title = "Avatar"
    mock_row.overview = "Planète bleue."

    mock_fetch_src.return_value = [mock_row]
    mock_fetch_vec.return_value = {999}

    populate.run_pipeline()

    assert mock_session.merge.called is False


@patch("database.populate.engine")
@patch("database.populate.get_db")
@patch("database.populate.fetch_source_films")
def test_run_pipeline_error_handling(mock_fetch_src, mock_get_db, mock_engine):
    """Vérifie le déclenchement automatique du rollback en cas de crash durant l'extraction."""
    mock_session = MagicMock()
    mock_context = MagicMock()
    mock_context.__enter__.return_value = mock_session
    mock_get_db.return_value.__next__.return_value = mock_context

    # On force la levée d'une exception lors de l'appel à l'extraction
    mock_fetch_src.side_effect = Exception("Crash Supabase simulé")

    with pytest.raises(Exception) as exc_info:
        populate.run_pipeline()

    assert "Crash Supabase simulé" in str(exc_info.value)
    assert mock_session.rollback.called


def test_fetch_source_films_isolated():
    """Valide l'exécution brute de la requête SQL d'extraction des films."""
    mock_session = MagicMock()
    mock_result = MagicMock()

    # Données fictives simulant le retour de fetchall()
    mock_data = [
        MagicMock(tmdb_id=1, title="Film A", overview="Description A"),
        MagicMock(tmdb_id=2, title="Film B", overview="Description B"),
    ]
    mock_result.fetchall.return_value = mock_data
    mock_session.execute.return_value = mock_result

    # Appel direct de la fonction globale
    res = populate.fetch_source_films(mock_session)

    assert len(res) == 2
    assert res[0].title == "Film A"
    mock_session.execute.assert_called_once()


def test_fetch_already_vectorized_ids_isolated():
    """Valide l'extraction et la conversion en set des IDs déjà vectorisés."""
    mock_session = MagicMock()
    mock_result = MagicMock()

    # Simulation des lignes retournées par la table 'film_embeddings'
    mock_rows = [
        MagicMock(tmdb_id=101),
        MagicMock(tmdb_id=102),
        MagicMock(tmdb_id=101),  # Doublon potentiel à filtrer par le set
    ]
    mock_result.fetchall.return_value = mock_rows
    mock_session.execute.return_value = mock_result

    # Appel direct de la fonction globale
    res = populate.fetch_already_vectorized_ids(mock_session)

    # L'utilisation d'un set (DRY) doit éliminer le doublon 101 automatiquement
    assert res == {101, 102}
    assert isinstance(res, set)
    mock_session.execute.assert_called_once()
