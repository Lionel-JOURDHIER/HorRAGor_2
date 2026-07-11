import pytest

from agents.router import (
    route_after_title_check,
    route_by_intent,
    route_direct_id_valid,
    route_hybrid_id_valid,
    route_need_wikipedia,
    route_return_wiki,
    route_validation_direct,
    route_validation_hybrid,
    route_verif_film,
)

# ==============================================================================
# MOCK / FIXTURE D'ÉTAT
# ==============================================================================


class DummyState:
    """Mock de AgentState pour injecter facilement les variables requises par le router."""

    def __init__(self, **kwargs):
        self.intent = kwargs.get("intent", "RECHERCHE")
        self.current_step = kwargs.get("current_step", "")
        self.retrieved_movies = kwargs.get("retrieved_movies", [])
        self.branch_search_wiki = kwargs.get("branch_search_wiki", "RAG")
        self.search_branch = kwargs.get("search_branch", "hybrid")
        self.retry_count = kwargs.get("retry_count", 0)


class DummyMovie:
    """Mock très basique d'un film pour remplir retrieved_movies."""

    def __init__(self, title="Mock Film"):
        self.title = title


# ==============================================================================
# TESTS PHASE 1 : ROUTAGE DE L'INTENTION & ENTRÉE
# ==============================================================================


@pytest.mark.parametrize(
    "intent_value, expected_route",
    [
        ("DISCUSSION", "Load_film_node"),
        ("RECHERCHE", "route_after_title_check"),
        ("CHITCHAT", "narrator_node"),
        ("AUCUN_FILM_TROUVE", "narrator_node"),
        ("INTENTION_INCONNUE", "route_after_title_check"),  # Fallback
    ],
)
def test_route_by_intent(intent_value, expected_route):
    state = DummyState(intent=intent_value)
    assert route_by_intent(state) == expected_route


@pytest.mark.parametrize(
    "step_value, expected_route",
    [
        ("has_title", "direct_movie_detail"),
        ("no_title", "filter_and_search_hybrid"),
        ("n_importe_quoi", "filter_and_search_hybrid"),  # Fallback
    ],
)
def test_route_after_title_check(step_value, expected_route):
    state = DummyState(current_step=step_value)
    assert route_after_title_check(state) == expected_route


@pytest.mark.parametrize(
    "movies, step_value, expected_route",
    [
        ([], "", "route_after_title_check"),  # Aucun film en mémoire
        ([DummyMovie()], "intent_rupture", "merge_filters_node"),  # Rupture sémantique
        ([DummyMovie()], "valid", "route_need_wikipedia"),  # Validation réussie
    ],
)
def test_route_verif_film(movies, step_value, expected_route):
    state = DummyState(retrieved_movies=movies, current_step=step_value)
    assert route_verif_film(state) == expected_route


# ==============================================================================
# TESTS PHASE 2 : ROUTAGE DE RECHERCHE & RÉFLEXION
# ==============================================================================


@pytest.mark.parametrize(
    "branch, search_branch, status, expected_route",
    [
        # Provenance RAG
        ("RAG", "direct", "valid_missing_synopsis", "wikipedia_search_node"),
        ("RAG", "direct", "valid", "card_node"),
        ("RAG", "hybrid", "valid", "format_cards_node"),
        # Provenance DISCUSSION
        ("DISCUSSION", "any", "valid_missing_data", "wikipedia_search_node"),
        ("DISCUSSION", "any", "valid", "narrator_node"),
        # Fallback
        ("INCONNU", "any", "valid", "narrator_node"),
    ],
)
def test_route_need_wikipedia(branch, search_branch, status, expected_route):
    state = DummyState(
        branch_search_wiki=branch, search_branch=search_branch, current_step=status
    )
    assert route_need_wikipedia(state) == expected_route


@pytest.mark.parametrize(
    "movies, retry, expected_route",
    [
        ([DummyMovie()], 0, "Affichage_film_unique"),  # 1 film trouvé
        ([DummyMovie(), DummyMovie()], 0, "Affichage_films"),  # >1 films trouvés
        ([], 0, "Search_vector_node"),  # 0 film, retry 0 -> RETRY
        ([], 1, "Search_vector_node"),  # 0 film, retry 1 -> RETRY
        ([], 2, "narrator_node"),  # 0 film, retry 2 -> FAIL
    ],
)
def test_route_direct_id_valid(movies, retry, expected_route):
    state = DummyState(retrieved_movies=movies, retry_count=retry)
    assert route_direct_id_valid(state) == expected_route


@pytest.mark.parametrize(
    "movies, retry, expected_route",
    [
        ([DummyMovie()], 0, "Affichage_film_unique"),  # 1 film trouvé
        ([DummyMovie(), DummyMovie()], 0, "Affichage_films"),  # >1 films trouvés
        ([], 0, "Merge_filters_node"),  # 0 film, retry 0 -> RETRY
        ([], 1, "Merge_filters_node"),  # 0 film, retry 1 -> RETRY
        ([], 2, "narrator_node"),  # 0 film, retry 2 -> FAIL
    ],
)
def test_route_hybrid_id_valid(movies, retry, expected_route):
    state = DummyState(retrieved_movies=movies, retry_count=retry)
    assert route_hybrid_id_valid(state) == expected_route


@pytest.mark.parametrize(
    "branch, expected_route",
    [
        ("RAG", "end_rag"),
        ("DISCUSSION", "narrator_node"),
        ("INCONNU", "narrator_node"),  # Fallback
    ],
)
def test_route_return_wiki(branch, expected_route):
    state = DummyState(branch_search_wiki=branch)
    assert route_return_wiki(state) == expected_route


# ==============================================================================
# TESTS PHASE 3 : ROUTAGE DE VALIDATION
# ==============================================================================


@pytest.mark.parametrize(
    "status, retry, expected_route",
    [
        ("valid", 0, "route_need_wikipedia"),  # PASS
        ("invalid_coherence", 0, "Search_vector_node"),  # RETRY
        ("invalid_coherence", 1, "Search_vector_node"),  # RETRY
        ("invalid_coherence", 2, "narrator_node"),  # FAIL
    ],
)
def test_route_validation_direct(status, retry, expected_route):
    state = DummyState(current_step=status, retry_count=retry)
    assert route_validation_direct(state) == expected_route


@pytest.mark.parametrize(
    "status, retry, expected_route",
    [
        ("valid", 0, "route_need_wikipedia"),  # PASS
        ("valid_partial", 0, "route_need_wikipedia"),  # PASS PARTIEL
        ("invalid_coherence", 0, "Merge_filters_node"),  # RETRY
        ("invalid_coherence", 1, "Merge_filters_node"),  # RETRY
        ("invalid_coherence", 2, "narrator_node"),  # FAIL
    ],
)
def test_route_validation_hybrid(status, retry, expected_route):
    state = DummyState(current_step=status, retry_count=retry)
    assert route_validation_hybrid(state) == expected_route
