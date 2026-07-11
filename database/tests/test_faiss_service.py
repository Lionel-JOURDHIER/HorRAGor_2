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

    assert results == [(777, 0.0)]


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


# --- NOUVEAUX TESTS À AJOUTER À LA FIN DU FICHIER ---


def test_save_and_load_index(tmp_path):
    """Vérifie la persistance sur disque (écriture et lecture) de l'index et du mapping."""
    # 1. Préparation d'un service avec des données factices
    service = FaissService(dimension=4)  # Dimension réduite pour le test
    test_vec = np.array([[0.1, 0.2, 0.3, 0.4]], dtype="float32")
    service.index.add(test_vec)
    service.id_mapping = {0: 123}

    # Chemins temporaires gérés par pytest
    index_file = tmp_path / "test.index"
    mapping_file = tmp_path / "test.json"

    # 2. Test de la sauvegarde
    service.save_index(str(index_file), str(mapping_file))

    assert index_file.exists(), "Le fichier .index n'a pas été créé."
    assert mapping_file.exists(), "Le fichier .json de mapping n'a pas été créé."

    # 3. Test du chargement dans un nouveau service vide
    new_service = FaissService(dimension=4)
    success = new_service.load_index(str(index_file), str(mapping_file))

    assert success is True
    assert new_service.index.ntotal == 1
    # Vérifie que les clés JSON (str) ont bien été reconverties en int
    assert new_service.id_mapping == {0: 123}


def test_load_index_missing_files(tmp_path):
    """Vérifie le comportement quand les fichiers d'index sont absents."""
    service = FaissService(dimension=4)
    success = service.load_index(
        str(tmp_path / "none.index"), str(tmp_path / "none.json")
    )

    assert success is False


def test_load_or_build_when_files_exist():
    """Vérifie que la construction est ignorée si l'index est chargé depuis le disque."""
    service = FaissService(dimension=4)
    mock_session = MagicMock()

    # On simule un chargement réussi
    service.load_index = MagicMock(return_value=True)
    service.build_index = MagicMock()

    service.load_or_build(mock_session)

    # L'index a été trouvé, build_index ne doit PAS être appelé
    service.load_index.assert_called_once()
    service.build_index.assert_not_called()


def test_load_or_build_when_files_missing():
    """Vérifie la construction et la sauvegarde si l'index est introuvable sur le disque."""
    service = FaissService(dimension=4)
    mock_session = MagicMock()

    # On simule l'absence de fichiers
    service.load_index = MagicMock(return_value=False)
    service.build_index = MagicMock()
    service.save_index = MagicMock()

    service.load_or_build(mock_session)

    # L'index n'a pas été trouvé, build_index ET save_index doivent être appelés
    service.load_index.assert_called_once()
    service.build_index.assert_called_once_with(mock_session)
    service.save_index.assert_called_once()


def test_get_vector_by_id():
    """Vérifie la récupération d'un vecteur depuis la RAM via l'ID TMDB."""
    service = FaissService(dimension=2)

    # Cas 1 : Index vide
    assert service.get_vector_by_id(999) is None

    # Ajout d'un vecteur
    test_vec = np.array([[0.5, 0.8]], dtype="float32")
    service.index.add(test_vec)
    service.id_mapping[0] = 999

    # Cas 2 : Récupération réussie
    vec = service.get_vector_by_id(999)
    assert pytest.approx(vec) == [0.5, 0.8]

    # Cas 3 : ID TMDB introuvable dans le mapping
    assert service.get_vector_by_id(777) is None
