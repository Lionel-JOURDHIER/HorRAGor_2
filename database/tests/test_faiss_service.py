from unittest.mock import MagicMock, patch

import numpy as np
import pytest

import database.populate as populate
from database.faiss_service import FaissService


def test_faiss_service_build_index():
    """Vérifie que l'index FAISS se construit bien à partir des données mockées."""
    # 1. Mock de la session et des objets retournés par SQLAlchemy
    mock_session = MagicMock()
    mock_embedding = MagicMock()
    mock_embedding.tmdb_id = 999
    # Vecteur de dimension 1024
    mock_embedding.embedd_title = [0.1] * 1024

    # On simule le retour de la requête SQL
    mock_session.query.return_value.all.return_value = [mock_embedding]

    # 2. Initialisation du service
    service = FaissService(dimension=1024)
    service.build_index(mock_session)

    # 3. Assertions
    assert service.index.ntotal == 1
    assert service.id_mapping[0] == 999


def test_faiss_service_search():
    """Vérifie que la recherche retourne bien un résultat."""
    service = FaissService(dimension=1024)

    # On ajoute manuellement un vecteur de test dans l'index
    test_vec = np.array([[0.5] * 1024], dtype="float32")
    service.index.add(test_vec)
    service.id_mapping[0] = 777

    # Recherche avec le même vecteur
    results = service.search([0.5] * 1024, k=1)

    assert results == [777]


@patch("database.populate.generate_local_embedding")
@patch("database.populate.get_db")
def test_run_pipeline_batch_recovery(mock_get_db, mock_embed):
    """Vérifie que le bloc 'except' sauve bien le lot en cours si Ollama crash."""
    mock_session = MagicMock()
    mock_context = MagicMock()
    mock_context.__enter__.return_value = mock_session
    mock_get_db.return_value.__next__.return_value = mock_context

    # Film 1 (titre + overview) et Film 2 (titre + overview) réussissent.
    # L'exception est levée juste après la création du Film 2 pour simuler un crash pendant la boucle.
    mock_embed.side_effect = [
        [0.1] * 1024,
        [0.1] * 1024,  # Film 1 : OK
        [0.2] * 1024,
        [0.2] * 1024,  # Film 2 : OK
        Exception("Crash Ollama simulé"),  # Déclenchement du crash au tour d'après
    ]

    # On simule 3 films dans la base source pour forcer la boucle à continuer
    mock_row1 = MagicMock(tmdb_id=1, title="Film 1", overview="Synopsis 1")
    mock_row2 = MagicMock(tmdb_id=2, title="Film 2", overview="Synopsis 2")
    mock_row3 = MagicMock(tmdb_id=3, title="Film 3", overview="Synopsis 3")

    with patch(
        "database.populate.fetch_source_films",
        return_value=[mock_row1, mock_row2, mock_row3],
    ):
        with patch(
            "database.populate.fetch_already_vectorized_ids", return_value=set()
        ):
            with pytest.raises(Exception) as exc_info:
                populate.run_pipeline()

            assert "Crash Ollama simulé" in str(exc_info.value)

    # Vérifie que malgré le crash, le merge du tampon (Film 1 et Film 2) a bien été exécuté
    assert mock_session.merge.called
    assert mock_session.commit.called
