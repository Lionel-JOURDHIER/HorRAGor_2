from pathlib import Path

import pytest

from agents.tools.sql_tools import _build_filtered_ids, filter_films_by_criteria
from agents.tools.vector_tools import (
    SMALL_POOL_THRESHOLD,
    faiss_global_service,
    search_similar_movies_by_id,
    search_vector_catalog,
)
from api.schemas import FilmShort
from database.connection import db_session


@pytest.fixture(scope="module", autouse=True)
def setup_faiss_index():
    """Hydrate le service FAISS vide avec le fichier d'index physique pour les tests."""

    # 1. Résolution dynamique du chemin vers ton fichier (indépendant du dossier d'où pytest est lancé)
    project_root = Path(__file__).resolve().parent.parent.parent
    index_path = project_root / "faiss_data" / "horragor.index"
    mapping_path = project_root / "faiss_data" / "horragor_mapping.json"

    # Sécurité : on s'assure que le test trouve bien le fichier
    assert index_path.exists(), f"❌ Fichier index introuvable à : {index_path}"

    # 2. Chargement des données dans ton instance globale
    # (Remplace "load_index" par le vrai nom de la méthode dans ta classe FaissService)
    faiss_global_service.load_index(
        index_path=str(index_path), mapping_path=str(mapping_path)
    )


# ──────────────────────────────────────────────────────────────
# SCÉNARIO 1 : Catalogue complet (Aucun filtre)
# ──────────────────────────────────────────────────────────────
def test_search_global_no_filters():
    query = "un tueur avec un masque de hockey dans un camp de vacances"

    results = search_vector_catalog.func(query=query, top_k=3, candidate_ids=None)

    assert results is not None
    assert len(results) <= 3
    # On s'assure que les scores de similarité sont cohérents (ex: entre 0 et 100)
    assert all(0 <= res.similarity_score <= 100 for res in results)


# ──────────────────────────────────────────────────────────────
# SCÉNARIO 2 : Petit Pool (Filtre strict / Moins que le seuil)
# ──────────────────────────────────────────────────────────────
def test_search_small_pool_kubrick():
    query = "un écrivain fou dans un hôtel enneigé et hanté"

    candidate_ids = filter_films_by_criteria.func(realisateur="Kubrick")

    assert candidate_ids is not None
    assert len(candidate_ids) < SMALL_POOL_THRESHOLD

    results = search_vector_catalog.func(
        query=query, top_k=3, candidate_ids=candidate_ids
    )

    assert len(results) > 0
    # Optionnel : si "The Shining" est dans ta base, tu peux valider sa présence
    # assert any("Shining" in res.title for res in results)


# ──────────────────────────────────────────────────────────────
# SCÉNARIO 3 : Grand Pool (Supérieur au seuil avec la bonne liste)
# ──────────────────────────────────────────────────────────────
def test_search_large_pool_thriller():
    query = "un monstre qui terrifie des adolescents dans leurs rêves"

    candidate_ids = filter_films_by_criteria.func(
        genres_included=["Horror", "Thriller"]
    )

    assert candidate_ids is not None
    assert len(candidate_ids) >= SMALL_POOL_THRESHOLD

    results = search_vector_catalog.func(
        query=query, top_k=3, candidate_ids=candidate_ids
    )

    assert len(results) <= 3
    assert len(results) > 0


# ──────────────────────────────────────────────────────────────
# SCÉNARIO 4 : Le Court-circuit de sécurité (Pool vide)
# ──────────────────────────────────────────────────────────────
def test_search_empty_pool_short_circuit():
    query = "un film d'horreur spatial avec des aliens"

    # Filtre impossible (Kubrick n'a pas sorti de film en 2026)
    candidate_ids = filter_films_by_criteria.func(
        realisateur="Kubrick", release_year_min=2026
    )

    # Validation du contrat d'interface : l'outil SQL DOIT renvoyer une liste vide
    assert candidate_ids == []

    # L'outil vectoriel doit intercepter la liste vide et court-circuiter immédiatement
    results = search_vector_catalog.func(
        query=query, top_k=3, candidate_ids=candidate_ids
    )

    # Strictement aucun résultat et exécution instantanée
    assert results == []


# ──────────────────────────────────────────────────────────────
# TESTS COMPLÉMENTAIRES POUR ATTEINDRE 100% DE COUVERTURE SQL
# ──────────────────────────────────────────────────────────────


def test_build_filtered_ids_no_filters_active():
    """Lignes 24-25 : Aucun filtre actif (retourne None)"""
    with db_session() as session:
        result = _build_filtered_ids(
            session=session,
            realisateur=None,
            genres_included=None,
            genres_excluded=None,
            release_year_min=None,
            release_year_max=None,
            tmdb_score_min=None,
            runtime_min=None,
            runtime_max=None,
        )
        assert result is None


def test_build_filtered_ids_with_genres_excluded():
    """Lignes 44-53 : Exclusion de genres (NOT EXISTS)"""
    with db_session() as session:
        result = _build_filtered_ids(
            session=session,
            genres_included=["Horror"],
            genres_excluded=["Comedy", "Sci-Fi"],
        )
        assert isinstance(result, list)


def test_build_filtered_ids_with_runtime_bounds():
    """Lignes 61-64 : Filtres sur la durée du film (runtime min/max)"""
    with db_session() as session:
        result = _build_filtered_ids(
            session=session, genres_included=["Horror"], runtime_min=60, runtime_max=120
        )
        assert isinstance(result, list)


def test_build_filtered_ids_with_tmdb_score():
    """Lignes 65-68 : Import dynamique et filtre du score TMDB"""
    with db_session() as session:
        result = _build_filtered_ids(
            session=session, genres_included=["Horror"], tmdb_score_min=6.0
        )
        assert isinstance(result, list)


from unittest.mock import patch

import pytest

# ──────────────────────────────────────────────────────────────
# TESTS COMPLÉMENTAIRES : EXCEPTION ET RETOURS VIDES (Outil 1)
# ──────────────────────────────────────────────────────────────


def test_search_vector_catalog_empty_faiss_results():
    """Ligne rouge 'if not faiss_results: return []'"""
    # On simule un cas où FAISS ne trouve absolument rien (retourne une liste vide)
    with patch("database.faiss_service.faiss_global_service.search", return_value=[]):
        results = search_vector_catalog.func(
            query="requête obscure", candidate_ids=None
        )
        assert results == []


def test_search_vector_catalog_exception_handling():
    """Lignes rouges du bloc 'except Exception as e'"""
    # On force une exception (ex: SideEffect provoquant une erreur) lors de la recherche
    with patch(
        "database.faiss_service.faiss_global_service.search",
        side_effect=Exception("FAISS Crash de test"),
    ):
        results = search_vector_catalog.func(query="test exception", candidate_ids=None)
        assert results == []


# ──────────────────────────────────────────────────────────────
# TESTS COMPLÉMENTAIRES : search_similar_movies_by_id (Outil 2)
# ──────────────────────────────────────────────────────────────


def test_search_similar_movies_id_not_found():
    """Lignes rouges 'if not query_vector: return []'"""
    # On simule un ID de film qui n'a pas de vecteur d'embedding en base
    with patch(
        "database.faiss_service.faiss_global_service.get_vector_by_id",
        return_value=None,
    ):
        results = search_similar_movies_by_id.func(movie_id=999999, candidate_ids=None)
        assert results == []


def test_search_similar_movies_no_faiss_results():
    """Lignes rouges 'if not faiss_results: return []' pour le deuxième outil"""
    dummy_vector = [0.1] * 384  # Ajuste la dimension selon ton modèle
    with (
        patch(
            "database.faiss_service.faiss_global_service.get_vector_by_id",
            return_value=dummy_vector,
        ),
        patch("agents.tools.vector_tools._search_in_pool", return_value=[]),
    ):
        results = search_similar_movies_by_id.func(
            movie_id=123, candidate_ids=[456, 789]
        )
        assert results == []


def test_search_similar_movies_success_flow():
    """Couvre tout le reste du bloc du bas (ordered_ids, distance_map, mapping et return)"""
    dummy_vector = [0.1] * 384
    mock_faiss_results = [(456, 0.2)]  # (tmdb_id, distance)
    mock_films_short = [
        FilmShort(tmdb_id=456, title="Film Test", overview="...", tmdb_score=7.0)
    ]

    with (
        patch(
            "database.faiss_service.faiss_global_service.get_vector_by_id",
            return_value=dummy_vector,
        ),
        patch(
            "agents.tools.vector_tools._search_in_pool", return_value=mock_faiss_results
        ),
        patch(
            "agents.tools.vector_tools.get_films_short_by_ids",
            return_value=mock_films_short,
        ),
    ):
        results = search_similar_movies_by_id.func(
            movie_id=123, candidate_ids=[456, 789]
        )
        assert len(results) == 1
        assert results[0].similarity_score is not None


def test_search_similar_movies_exception_handling():
    """Bloc d'exception final 'except Exception as e' du deuxième outil"""
    with patch(
        "database.faiss_service.faiss_global_service.get_vector_by_id",
        side_effect=Exception("Crash global"),
    ):
        results = search_similar_movies_by_id.func(movie_id=123, candidate_ids=[456])
        assert results == []


# ──────────────────────────────────────────────────────────────
# TESTS COMPLÉMENTAIRES : STRATÉGIE ADAPTIVE _search_in_pool
# ──────────────────────────────────────────────────────────────


def test_search_in_pool_discard_exclude_id():
    """Ligne rouge 88 : Force l'exclusion du film source (exclude_id)"""
    from agents.tools.vector_tools import _search_in_pool

    # On passe un pool de candidats, et on demande explicitement d'exclure le 456
    candidate_ids = [123, 456, 789]
    dummy_vector = [0.1] * 1024  # Aligné sur la dimension 1024 de ta docstring

    mock_vector = [0.2] * 1024

    # On mocke get_vector_by_id pour simuler le parcours du petit pool
    with patch(
        "database.faiss_service.faiss_global_service.get_vector_by_id",
        return_value=mock_vector,
    ):
        results = _search_in_pool(
            query_vector=dummy_vector,
            candidate_ids=candidate_ids,
            top_k=2,
            exclude_id=456,
        )

        # On vérifie que le traitement s'est bien fait et que le 456 a été ignoré
        # (Les IDs retournés doivent uniquement être 123 ou 789)
        returned_ids = [res[0] for res in results]
        assert 456 not in returned_ids


def test_search_in_pool_sub_index_ntotal_zero():
    """Lignes rouges 101-102 : Cas où aucun vecteur n'a pu être chargé (ntotal == 0)"""
    from agents.tools.vector_tools import _search_in_pool

    candidate_ids = [123, 456]
    dummy_vector = [0.1] * 1024

    # En retournant None pour tous les IDs, la boucle 'if vector:' ne s'exécute jamais
    # sub_index.ntotal restera à 0, forçant le court-circuit 'return []'
    with patch(
        "database.faiss_service.faiss_global_service.get_vector_by_id",
        return_value=None,
    ):
        results = _search_in_pool(
            query_vector=dummy_vector,
            candidate_ids=candidate_ids,
            top_k=5,
            exclude_id=None,
        )

        assert results == []


def test_search_similar_movies_else_candidate_ids_none():
    """Ligne rouge : Force le bloc else à retourner [] quand candidate_ids est None"""
    from unittest.mock import patch

    # On simule un vecteur valide pour que le test passe la première étape 'if not query_vector:'
    dummy_vector = [0.1] * 1024

    with patch(
        "database.faiss_service.faiss_global_service.get_vector_by_id",
        return_value=dummy_vector,
    ):
        # On passe explicitement candidate_ids=None pour rentrer directement dans le else rouge
        results = search_similar_movies_by_id.func(
            movie_id=123, top_k=5, candidate_ids=None
        )

        # On valide le contrat d'interface : le retour doit être une liste vide
        assert results == []


def test_build_filtered_ids_with_release_year_bounds():
    """Ligne rouge : Force l'exécution du filtre de l'année maximale de sortie (release_year_max)"""
    with db_session() as session:
        # On définit une plage d'années pour forcer le passage dans les deux blocs 'if'
        result = _build_filtered_ids(
            session=session,
            genres_included=["Horror"],
            release_year_min=2000,
            release_year_max=2025,
        )

        # On valide que la requête s'exécute correctement et renvoie une liste
        assert isinstance(result, list)


def test_search_in_pool_faiss_id_not_in_sub_mapping():
    """Couvre la condition de sécurité de la boucle de restitution 'if faiss_id in sub_mapping'."""
    import numpy as np

    from agents.tools.vector_tools import _search_in_pool

    candidate_ids = [123]
    dummy_vector = [0.1] * 1024
    mock_vector = [0.2] * 1024

    # On simule un comportement où FAISS retourne un ID (-1) qui n'est pas dans notre dictionnaire local
    mock_D = np.array([[0.5]], dtype="float32")
    mock_I = np.array([[-1]], dtype="int64")  # -1 n'existe pas dans sub_mapping

    with (
        patch(
            "database.faiss_service.faiss_global_service.get_vector_by_id",
            return_value=mock_vector,
        ),
        patch("faiss.IndexFlatL2.search", return_value=(mock_D, mock_I)),
    ):
        results = _search_in_pool(
            query_vector=dummy_vector,
            candidate_ids=candidate_ids,
            top_k=1,
            exclude_id=None,
        )

        # Le résultat doit être vide puisque l'ID -1 a été filtré et ignoré
        assert results == []
