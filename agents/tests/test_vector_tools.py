from unittest.mock import AsyncMock, MagicMock, patch

import faiss
import numpy as np
import pytest
from agents.tools.vector_tools import (
    SMALL_POOL_THRESHOLD,
    faiss_global_service,
    search_similar_movies_by_id,
    search_vector_catalog,
)
from shared.schemas import FilmShort

# Nombre de vecteurs synthétiques : dépasse SMALL_POOL_THRESHOLD pour que le
# scénario « grand pool » (recherche globale + post-filtre) soit atteignable.
SYNTHETIC_VECTOR_COUNT = SMALL_POOL_THRESHOLD + 500
SYNTHETIC_TMDB_ID_BASE = 900000


@pytest.fixture
def mock_external_services():
    """Isole search_vector_catalog des services réseau réels (Ollama, Database API).

    L'embedding et l'hydratation SQL sont simulés ; seule la recherche FAISS
    elle-même reste réelle, sur l'index chargé par `setup_faiss_index`.
    """
    mock_embedder = MagicMock()
    mock_embedder.embed_query.return_value = [0.1] * 1024
    with (
        patch("agents.tools.vector_tools.OLLAMA_CLIENT_EMBEDD", mock_embedder),
        patch(
            "agents.tools.vector_tools.get_films_short_by_ids",
            new_callable=AsyncMock,
        ) as mock_get_films,
    ):
        mock_get_films.side_effect = lambda ids: [
            FilmShort(tmdb_id=i, title=f"Film {i}", overview="...", tmdb_score=7.0)
            for i in ids
        ]
        yield


@pytest.fixture(scope="module", autouse=True)
def setup_faiss_index():
    """Hydrate le service FAISS avec un index synthétique construit en mémoire.

    L'index et le mapping réels (`faiss_data/`) sont ignorés par git — voir
    CLAUDE.md § L'index FAISS est embarqué dans l'image `api` — et donc absents
    d'un checkout CI. `rules/tests-python.md` § Fixtures interdit de toute façon
    un chemin en dur vers un dossier du dépôt : les vecteurs sont générés ici,
    déterministes (graine fixe), sans dépendre d'aucun fichier local.
    """
    rng = np.random.default_rng(42)
    vectors = rng.random(
        (SYNTHETIC_VECTOR_COUNT, faiss_global_service.dimension), dtype=np.float32
    )
    faiss_global_service.index = faiss.IndexFlatL2(faiss_global_service.dimension)
    faiss_global_service.index.add(vectors)
    faiss_global_service.id_mapping = {
        i: SYNTHETIC_TMDB_ID_BASE + i for i in range(SYNTHETIC_VECTOR_COUNT)
    }


@pytest.fixture(scope="module")
def real_tmdb_ids():
    """IDs tmdb présents dans l'index FAISS synthétique de `setup_faiss_index`.

    Simule le pool que renverrait `filter_films_by_criteria` (Database API
    réelle, hors de portée d'un test isolé) : des candidate_ids qui existent
    réellement dans l'index en mémoire, pour que la recherche vectorielle qui
    suit ait un pool où trouver des résultats.
    """
    return [SYNTHETIC_TMDB_ID_BASE + i for i in range(SYNTHETIC_VECTOR_COUNT)]


# ──────────────────────────────────────────────────────────────
# SCÉNARIO 1 : Catalogue complet (Aucun filtre)
# ──────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_search_global_no_filters(mock_external_services):
    query = "un tueur avec un masque de hockey dans un camp de vacances"

    results = await search_vector_catalog.ainvoke(
        {"query": query, "top_k": 3, "candidate_ids": None}
    )

    assert results is not None
    assert len(results) <= 3
    # On s'assure que les scores de similarité sont cohérents (ex: entre 0 et 100)
    assert all(0 <= res.similarity_score <= 100 for res in results)


# ──────────────────────────────────────────────────────────────
# SCÉNARIO 2 : Petit Pool (Filtre strict / Moins que le seuil)
# ──────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_search_small_pool_kubrick(real_tmdb_ids, mock_external_services):
    query = "un écrivain fou dans un hôtel enneigé et hanté"
    candidate_ids = real_tmdb_ids[:50]
    assert len(candidate_ids) < SMALL_POOL_THRESHOLD

    results = await search_vector_catalog.ainvoke(
        {"query": query, "top_k": 3, "candidate_ids": candidate_ids}
    )

    assert len(results) > 0


# ──────────────────────────────────────────────────────────────
# SCÉNARIO 3 : Grand Pool (Supérieur au seuil avec la bonne liste)
# ──────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_search_large_pool_thriller(real_tmdb_ids, mock_external_services):
    query = "un monstre qui terrifie des adolescents dans leurs rêves"
    candidate_ids = real_tmdb_ids
    assert len(candidate_ids) >= SMALL_POOL_THRESHOLD

    results = await search_vector_catalog.ainvoke(
        {"query": query, "top_k": 3, "candidate_ids": candidate_ids}
    )

    assert len(results) <= 3
    assert len(results) > 0


# ──────────────────────────────────────────────────────────────
# SCÉNARIO 4 : Le Court-circuit de sécurité (Pool vide)
# ──────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_search_empty_pool_short_circuit():
    query = "un film d'horreur spatial avec des aliens"

    # L'outil vectoriel doit intercepter la liste vide et court-circuiter immédiatement
    results = await search_vector_catalog.ainvoke(
        {"query": query, "top_k": 3, "candidate_ids": []}
    )

    # Strictement aucun résultat et exécution instantanée
    assert results == []


# ──────────────────────────────────────────────────────────────
# TESTS COMPLÉMENTAIRES : EXCEPTION ET RETOURS VIDES (Outil 1)
# ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_search_vector_catalog_empty_faiss_results(mock_external_services):
    """Ligne rouge 'if not faiss_results: return []'"""
    # On simule un cas où FAISS ne trouve absolument rien (retourne une liste vide)
    with patch("database.faiss_service.faiss_global_service.search", return_value=[]):
        results = await search_vector_catalog.ainvoke(
            {"query": "requête obscure", "candidate_ids": None}
        )
        assert results == []


@pytest.mark.asyncio
async def test_search_vector_catalog_exception_handling(mock_external_services):
    """Lignes rouges du bloc 'except Exception as e'"""
    # On force une exception (ex: SideEffect provoquant une erreur) lors de la recherche
    with patch(
        "database.faiss_service.faiss_global_service.search",
        side_effect=Exception("FAISS Crash de test"),
    ):
        results = await search_vector_catalog.ainvoke(
            {"query": "test exception", "candidate_ids": None}
        )
        assert results == []


# ──────────────────────────────────────────────────────────────
# TESTS COMPLÉMENTAIRES : search_similar_movies_by_id (Outil 2)
# ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_search_similar_movies_id_not_found():
    """Lignes rouges 'if not query_vector: return []'"""
    # On simule un ID de film qui n'a pas de vecteur d'embedding en base
    with patch(
        "database.faiss_service.faiss_global_service.get_vector_by_id",
        return_value=None,
    ):
        results = await search_similar_movies_by_id.ainvoke(
            {"movie_id": 999999, "candidate_ids": None}
        )
        assert results == []


@pytest.mark.asyncio
async def test_search_similar_movies_no_faiss_results():
    """Lignes rouges 'if not faiss_results: return []' pour le deuxième outil"""
    dummy_vector = [0.1] * 384  # Ajuste la dimension selon ton modèle
    with (
        patch(
            "database.faiss_service.faiss_global_service.get_vector_by_id",
            return_value=dummy_vector,
        ),
        patch("agents.tools.vector_tools._search_in_pool", return_value=[]),
    ):
        results = await search_similar_movies_by_id.ainvoke(
            {"movie_id": 123, "candidate_ids": [456, 789]}
        )
        assert results == []


@pytest.mark.asyncio
async def test_search_similar_movies_success_flow():
    """Couvre le reste du bloc du bas (ordered_ids, distance_map, mapping, return)."""
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
        results = await search_similar_movies_by_id.ainvoke(
            {"movie_id": 123, "candidate_ids": [456, 789]}
        )
        assert len(results) == 1
        assert results[0].similarity_score is not None


@pytest.mark.asyncio
async def test_search_similar_movies_exception_handling():
    """Bloc d'exception final 'except Exception as e' du deuxième outil"""
    with patch(
        "database.faiss_service.faiss_global_service.get_vector_by_id",
        side_effect=Exception("Crash global"),
    ):
        results = await search_similar_movies_by_id.ainvoke(
            {"movie_id": 123, "candidate_ids": [456]}
        )
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


@pytest.mark.asyncio
async def test_search_similar_movies_else_candidate_ids_none():
    """Force le bloc else à retourner [] quand candidate_ids est None."""
    # On simule un vecteur valide pour passer la première étape 'if not query_vector:'
    dummy_vector = [0.1] * 1024

    with patch(
        "database.faiss_service.faiss_global_service.get_vector_by_id",
        return_value=dummy_vector,
    ):
        # On passe explicitement candidate_ids=None pour rentrer dans le else rouge
        results = await search_similar_movies_by_id.ainvoke(
            {"movie_id": 123, "top_k": 5, "candidate_ids": None}
        )

        # On valide le contrat d'interface : le retour doit être une liste vide
        assert results == []


def test_search_in_pool_faiss_id_not_in_sub_mapping():
    """Couvre la condition de sécurité 'if faiss_id in sub_mapping'."""
    import numpy as np
    from agents.tools.vector_tools import _search_in_pool

    candidate_ids = [123]
    dummy_vector = [0.1] * 1024
    mock_vector = [0.2] * 1024

    # On simule un ID (-1) que FAISS retourne mais absent du dictionnaire local
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
