"""tests/test_nodes_rag.py"""

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage

from agents.nodes_rag import (
    card_node,
    format_cards_node,
    hydratation_node,
    intent_classifier_node,
    load_film_node,
    merge_filters_node,
    search_vector_node,
    title_router_node,
    validation_film_node,
    validation_node,
    verif_film_node,
)
from shared.schemas import ChatFilters

# ==============================================================================
# FIXTURES & MOCKS
# ==============================================================================


@pytest.fixture
def base_state():
    state = MagicMock()
    state.user_query = "un film d'horreur"
    state.intent = "RECHERCHE"
    state.current_step = None
    state.steps = []
    state.answer = None
    state.search_branch = "direct"
    state.sql_filters = ChatFilters()
    state.initial_filters = ChatFilters()
    state.retrieved_movies = []
    state.last_displayed_movies_id = []
    state.retry_count = 0
    state.candidate_ids = None
    state.enrich_ids = []
    state.data_enriched = ""
    state.branch_search_wiki = "RAG"
    return state


class MockFilmShort:
    def __init__(self, tmdb_id=123, title="Alien"):
        self.tmdb_id = tmdb_id
        self.title = title
        self.release_date = "1979-05-25"
        self.genres = ["Horror", "Science Fiction"]
        self.tmdb_score = 8.2
        self.synopsis = "A terrifying creature in space."


class MockFilmDetail(MockFilmShort):
    def __init__(self, tmdb_id=123, title="Alien"):
        super().__init__(tmdb_id=tmdb_id, title=title)
        self.realisateur = "Ridley Scott"
        self.director = "Ridley Scott"
        self.runtime = 117
        self.tagline = "In space no one can hear you scream."
        self.imdb_score = 8.1
        self.rotten_tomatometer = 98
        self.collection = None


# ==============================================================================
# intent_classifier_node
# ==============================================================================


@patch("agents.nodes_rag.structured_llm")
def test_intent_classifier_recherche(mock_llm, base_state):
    """Intent RECHERCHE — chemin nominal sans contexte."""
    base_state.last_displayed_movies_id = []
    mock_extractor = MagicMock()
    mock_extractor.invoke.return_value = MagicMock(intent="RECHERCHE")
    mock_llm.with_structured_output.return_value = mock_extractor

    result = intent_classifier_node(base_state)

    assert result["intent"] == "RECHERCHE"
    assert result["current_step"] == "RECHERCHE"
    assert any(s.step == "intent_classification" for s in result["steps"])


@patch("agents.nodes_rag.structured_llm")
def test_intent_classifier_discussion_avec_contexte(mock_llm, base_state):
    """Intent DISCUSSION avec film en mémoire → DISCUSSION conservé."""
    base_state.last_displayed_movies_id = [348]
    mock_extractor = MagicMock()
    mock_extractor.invoke.return_value = MagicMock(intent="DISCUSSION")
    mock_llm.with_structured_output.return_value = mock_extractor

    result = intent_classifier_node(base_state)

    assert result["intent"] == "DISCUSSION"


@patch("agents.nodes_rag.structured_llm")
def test_intent_classifier_discussion_sans_contexte_redirige(mock_llm, base_state):
    """Intent DISCUSSION sans film en mémoire → redirigé vers AUCUN_FILM_TROUVE."""
    base_state.last_displayed_movies_id = []
    mock_extractor = MagicMock()
    mock_extractor.invoke.return_value = MagicMock(intent="DISCUSSION")
    mock_llm.with_structured_output.return_value = mock_extractor

    result = intent_classifier_node(base_state)

    assert result["intent"] == "AUCUN_FILM_TROUVE"


@patch("agents.nodes_rag.structured_llm")
def test_intent_classifier_chitchat(mock_llm, base_state):
    """Intent CHITCHAT sans contexte → CHITCHAT conservé."""
    base_state.last_displayed_movies_id = []
    mock_extractor = MagicMock()
    mock_extractor.invoke.return_value = MagicMock(intent="CHITCHAT")
    mock_llm.with_structured_output.return_value = mock_extractor

    result = intent_classifier_node(base_state)

    assert result["intent"] == "CHITCHAT"


@patch("agents.nodes_rag.structured_llm")
def test_intent_classifier_intent_inconnu_sans_contexte(mock_llm, base_state):
    """Intent inconnu sans contexte → redirigé vers AUCUN_FILM_TROUVE."""
    base_state.last_displayed_movies_id = []
    mock_extractor = MagicMock()
    mock_extractor.invoke.return_value = MagicMock(intent="AUCUN_FILM_TROUVE")
    mock_llm.with_structured_output.return_value = mock_extractor

    result = intent_classifier_node(base_state)

    assert result["intent"] == "AUCUN_FILM_TROUVE"


@patch("agents.nodes_rag.structured_llm")
def test_intent_classifier_fallback_sur_erreur_llm(mock_llm, base_state):
    """Erreur LLM → fallback RECHERCHE."""
    base_state.last_displayed_movies_id = []
    mock_extractor = MagicMock()
    mock_extractor.invoke.side_effect = Exception("Ollama down")
    mock_llm.with_structured_output.return_value = mock_extractor

    result = intent_classifier_node(base_state)

    assert result["intent"] == "RECHERCHE"


@patch("agents.nodes_rag.structured_llm")
def test_intent_classifier_last_displayed_none(mock_llm, base_state):
    """last_displayed_movies_id=None → traité comme liste vide."""
    base_state.last_displayed_movies_id = None
    mock_extractor = MagicMock()
    mock_extractor.invoke.return_value = MagicMock(intent="RECHERCHE")
    mock_llm.with_structured_output.return_value = mock_extractor

    result = intent_classifier_node(base_state)

    assert result["intent"] == "RECHERCHE"


# ==============================================================================
# title_router_node
# ==============================================================================


@patch("agents.nodes_rag.llm")
def test_title_router_titre_detecte(mock_llm, base_state):
    """LLM détecte un titre → branche directe."""
    mock_llm.invoke.return_value = AIMessage(content="Alien")

    result = title_router_node(base_state)

    assert result["current_step"] == "has_title"
    assert result["search_branch"] == "direct"
    assert result["answer"] == "Alien"


@patch("agents.nodes_rag.llm")
def test_title_router_aucun_titre(mock_llm, base_state):
    """LLM retourne vide → branche hybride."""
    mock_llm.invoke.return_value = AIMessage(content="")

    result = title_router_node(base_state)

    assert result["current_step"] == "no_title"
    assert result["search_branch"] == "hybrid"


@patch("agents.nodes_rag.llm")
def test_title_router_nettoyage_guillemets(mock_llm, base_state):
    """Les guillemets parasites sont supprimés du titre détecté."""
    mock_llm.invoke.return_value = AIMessage(content='"The Shining"')

    result = title_router_node(base_state)

    assert result["answer"] == "The Shining"


@patch("agents.nodes_rag.llm")
def test_title_router_steps_append(mock_llm, base_state):
    """Un AgentStep est ajouté dans les deux cas."""
    mock_llm.invoke.return_value = AIMessage(content="Alien")

    result = title_router_node(base_state)

    assert any(s.step == "title_detection" for s in result["steps"])


# ==============================================================================
# merge_filters_node
# ==============================================================================


@patch("agents.nodes_rag.structured_llm")
def test_merge_filters_extraction_nominale(mock_llm, base_state):
    """Extraction LLM réussie → filtres dans sql_filters."""
    mock_extractor = MagicMock()
    mock_extractor.invoke.return_value = ChatFilters(realisateur="Kubrick")
    mock_llm.with_structured_output.return_value = mock_extractor

    result = merge_filters_node(base_state)

    assert result["sql_filters"].realisateur == "Kubrick"
    assert result["current_step"] == "filters_ready"


@patch("agents.nodes_rag.structured_llm")
def test_merge_filters_inversion_annees(mock_llm, base_state):
    """Bornes années inversées → corrigées automatiquement."""
    mock_extractor = MagicMock()
    mock_extractor.invoke.return_value = ChatFilters(
        release_year_min=2020, release_year_max=1990
    )
    mock_llm.with_structured_output.return_value = mock_extractor

    result = merge_filters_node(base_state)

    assert result["sql_filters"].release_year_min == 1990
    assert result["sql_filters"].release_year_max == 2020


@patch("agents.nodes_rag.structured_llm")
def test_merge_filters_guard_genres_excluded_catalogue_complet(mock_llm, base_state):
    """genres_excluded couvrant tout le catalogue → ignoré."""
    from agents.nodes_rag import CATALOG_GENRES

    mock_extractor = MagicMock()
    mock_extractor.invoke.return_value = ChatFilters(
        genres_excluded=list(CATALOG_GENRES)
    )
    mock_llm.with_structured_output.return_value = mock_extractor

    result = merge_filters_node(base_state)

    assert result["sql_filters"].genres_excluded == []


@patch("agents.nodes_rag.structured_llm")
def test_merge_filters_merge_avec_initial_filters(mock_llm, base_state):
    """Les filtres front-end sont conservés si le LLM n'écrase pas."""
    base_state.initial_filters = ChatFilters(genres_excluded=["Comedy"])
    mock_extractor = MagicMock()
    mock_extractor.invoke.return_value = ChatFilters(realisateur="Kubrick")
    mock_llm.with_structured_output.return_value = mock_extractor

    result = merge_filters_node(base_state)

    assert result["sql_filters"].realisateur == "Kubrick"
    assert result["sql_filters"].genres_excluded == ["Comedy"]


@patch("agents.nodes_rag.structured_llm")
def test_merge_filters_fallback_sur_erreur_llm(mock_llm, base_state):
    """Erreur LLM → filtres vides, pas d'exception."""
    mock_extractor = MagicMock()
    mock_extractor.invoke.side_effect = Exception("LLM down")
    mock_llm.with_structured_output.return_value = mock_extractor

    result = merge_filters_node(base_state)

    assert result["sql_filters"].realisateur is None
    assert result["current_step"] == "filters_ready"


# ==============================================================================
# search_vector_node
# ==============================================================================


@patch("agents.nodes_rag.search_vector_catalog")
@patch("agents.nodes_rag.filter_films_by_criteria")
def test_search_vector_branche_directe(mock_sql, mock_faiss, base_state):
    """Branche directe : query = answer, top_k=1, pas de filtre SQL."""
    base_state.search_branch = "direct"
    base_state.answer = "Alien"
    mock_faiss.func.return_value = [MockFilmShort()]

    result = search_vector_node(base_state)

    mock_sql.func.assert_not_called()
    mock_faiss.func.assert_called_once_with(query="Alien", top_k=1, candidate_ids=None)
    assert result["current_step"] == "has_results"


@patch("agents.nodes_rag.search_vector_catalog")
@patch("agents.nodes_rag.filter_films_by_criteria")
def test_search_vector_branche_hybride(mock_sql, mock_faiss, base_state):
    """Branche hybride : query = user_query, top_k=5, filtre SQL."""
    base_state.search_branch = "hybrid"
    base_state.sql_filters = ChatFilters(realisateur="Kubrick")
    mock_sql.func.return_value = [1, 2, 3]
    mock_faiss.func.return_value = [MockFilmShort()]

    result = search_vector_node(base_state)

    mock_sql.func.assert_called_once()
    mock_faiss.func.assert_called_once_with(
        query=base_state.user_query, top_k=5, candidate_ids=[1, 2, 3]
    )
    assert result["current_step"] == "has_results"


@patch("agents.nodes_rag.search_vector_catalog")
@patch("agents.nodes_rag.filter_films_by_criteria")
def test_search_vector_pool_sql_vide_court_circuit(mock_sql, mock_faiss, base_state):
    """Pool SQL vide → court-circuit, FAISS non appelé."""
    base_state.search_branch = "hybrid"
    base_state.sql_filters = ChatFilters(realisateur="Kubrick", release_year_min=2020)
    mock_sql.func.return_value = []

    result = search_vector_node(base_state)

    mock_faiss.func.assert_not_called()
    assert result["current_step"] == "no_results"
    assert result["retrieved_movies"] == []


@patch("agents.nodes_rag.search_vector_catalog")
@patch("agents.nodes_rag.filter_films_by_criteria")
def test_search_vector_faiss_vide(mock_sql, mock_faiss, base_state):
    """FAISS retourne vide → no_results."""
    base_state.search_branch = "direct"
    base_state.answer = "FilmInexistant"
    mock_faiss.func.return_value = []

    result = search_vector_node(base_state)

    assert result["current_step"] == "no_results"
    assert result["retrieved_movies"] == []


@patch("agents.nodes_rag.search_vector_catalog")
@patch("agents.nodes_rag.filter_films_by_criteria")
def test_search_vector_sql_none_catalogue_complet(mock_sql, mock_faiss, base_state):
    """SQL retourne None → candidate_ids=None, FAISS sur catalogue complet."""
    base_state.search_branch = "hybrid"
    base_state.sql_filters = ChatFilters()
    mock_sql.func.return_value = None
    mock_faiss.func.return_value = [MockFilmShort()]

    result = search_vector_node(base_state)

    mock_faiss.func.assert_called_once_with(
        query=base_state.user_query, top_k=5, candidate_ids=None
    )
    assert result["current_step"] == "has_results"


# ==============================================================================
# hydratation_node
# ==============================================================================


@patch("agents.nodes_rag.get_films_details_by_ids")
def test_hydratation_nominale(mock_sql, base_state):
    """Film trouvé → FilmDetail dans retrieved_movies."""
    base_state.retrieved_movies = [MockFilmShort()]
    mock_sql.return_value = [MockFilmDetail()]

    result = hydratation_node(base_state)

    assert result["current_step"] == "hydrated"
    assert result["retrieved_movies"][0].title == "Alien"


@patch("agents.nodes_rag.get_films_details_by_ids")
def test_hydratation_retrieved_movies_vide(mock_sql, base_state):
    """retrieved_movies vide → no_results sans appel SQL."""
    base_state.retrieved_movies = []

    result = hydratation_node(base_state)

    mock_sql.assert_not_called()
    assert result["current_step"] == "no_results"


@patch("agents.nodes_rag.get_films_details_by_ids")
def test_hydratation_film_absent_sql(mock_sql, base_state):
    """Film présent dans FAISS mais absent en SQL → no_results."""
    base_state.retrieved_movies = [MockFilmShort(tmdb_id=9999)]
    mock_sql.return_value = []

    result = hydratation_node(base_state)

    assert result["current_step"] == "no_results"


@patch("agents.nodes_rag.get_films_details_by_ids")
def test_hydratation_utilise_premier_film_uniquement(mock_sql, base_state):
    """Seul retrieved_movies[0] est hydraté."""
    films = [MockFilmShort(tmdb_id=1), MockFilmShort(tmdb_id=2)]
    base_state.retrieved_movies = films
    mock_sql.return_value = [MockFilmDetail(tmdb_id=1)]

    hydratation_node(base_state)

    mock_sql.assert_called_once_with([1])


# ==============================================================================
# card_node
# ==============================================================================


def test_card_node_nominal(base_state):
    """Film présent → card_ready avec premier film uniquement."""
    films = [MockFilmDetail(tmdb_id=1), MockFilmDetail(tmdb_id=2)]
    base_state.retrieved_movies = films

    result = card_node(base_state)

    assert result["current_step"] == "card_ready"
    assert len(result["retrieved_movies"]) == 1
    assert result["retrieved_movies"][0].tmdb_id == 1
    assert result["last_displayed_movies_id"] == [1]


def test_card_node_retrieved_movies_vide(base_state):
    """retrieved_movies vide → no_results."""
    base_state.retrieved_movies = []

    result = card_node(base_state)

    assert result["current_step"] == "no_results"


def test_card_node_steps_append(base_state):
    """Un AgentStep est ajouté."""
    base_state.retrieved_movies = [MockFilmDetail()]

    result = card_node(base_state)

    assert any(s.step == "card" for s in result["steps"])


def test_card_node_last_displayed_movies_id(base_state):
    """last_displayed_movies_id contient l'ID du film sélectionné."""
    base_state.retrieved_movies = [MockFilmDetail(tmdb_id=348)]

    result = card_node(base_state)

    assert result["last_displayed_movies_id"] == [348]


# ==============================================================================
# validation_node
# ==============================================================================


@patch("agents.nodes_rag.structured_llm")
def test_validation_node_cas2_valid(mock_llm, base_state):
    """Film pertinent et complet → valid."""
    base_state.retrieved_movies = [MockFilmDetail()]
    mock_extractor = MagicMock()
    mock_extractor.invoke.return_value = MagicMock(
        is_relevant=True, has_missing_info=False, feedback="", corrected_title=None
    )
    mock_llm.with_structured_output.return_value = mock_extractor

    result = validation_node(base_state)

    assert result["current_step"] == "valid"


@patch("agents.nodes_rag.structured_llm")
def test_validation_node_cas3_valid_missing_synopsis(mock_llm, base_state):
    """Film pertinent mais synopsis manquant → valid_missing_synopsis."""
    base_state.retrieved_movies = [MockFilmDetail()]
    mock_extractor = MagicMock()
    mock_extractor.invoke.return_value = MagicMock(
        is_relevant=True,
        has_missing_info=True,
        feedback="Synopsis vide",
        corrected_title=None,
    )
    mock_llm.with_structured_output.return_value = mock_extractor

    result = validation_node(base_state)

    assert result["current_step"] == "valid_missing_synopsis"


@patch("agents.nodes_rag.structured_llm")
def test_validation_node_invalid_avec_corrected_title(mock_llm, base_state):
    """Film invalide avec corrected_title → answer mis à jour."""
    base_state.retrieved_movies = [MockFilmDetail()]
    base_state.retry_count = 0
    mock_extractor = MagicMock()
    mock_extractor.invoke.return_value = MagicMock(
        is_relevant=False,
        has_missing_info=False,
        feedback="Mauvais film",
        corrected_title="The Shining",
    )
    mock_llm.with_structured_output.return_value = mock_extractor

    result = validation_node(base_state)

    assert result["current_step"] == "invalid_coherence"
    assert result["answer"] == "The Shining"
    assert result["retry_count"] == 1


@patch("agents.nodes_rag.structured_llm")
def test_validation_node_invalid_titre_extrait_du_feedback(mock_llm, base_state):
    """corrected_title=None mais titre dans feedback → extrait par regex."""
    base_state.retrieved_movies = [MockFilmDetail()]
    base_state.retry_count = 0
    mock_extractor = MagicMock()
    mock_extractor.invoke.return_value = MagicMock(
        is_relevant=False,
        has_missing_info=False,
        feedback="Le bon film est 'The Shining' selon Kubrick.",
        corrected_title=None,
    )
    mock_llm.with_structured_output.return_value = mock_extractor

    result = validation_node(base_state)

    assert result["answer"] == "The Shining"


@patch("agents.nodes_rag.structured_llm")
def test_validation_node_invalid_sans_titre_corrige(mock_llm, base_state):
    """Film invalide sans titre corrigé → invalid_coherence sans answer."""
    base_state.retrieved_movies = [MockFilmDetail()]
    base_state.retry_count = 0
    mock_extractor = MagicMock()
    mock_extractor.invoke.return_value = MagicMock(
        is_relevant=False,
        has_missing_info=False,
        feedback="Film non pertinent.",
        corrected_title=None,
    )
    mock_llm.with_structured_output.return_value = mock_extractor

    result = validation_node(base_state)

    assert result["current_step"] == "invalid_coherence"
    assert result["answer"] == None


@patch("agents.nodes_rag.structured_llm")
def test_validation_node_retrieved_movies_vide(mock_llm, base_state):
    """retrieved_movies vide → invalid_coherence direct."""
    base_state.retrieved_movies = []

    result = validation_node(base_state)

    mock_llm.with_structured_output.assert_not_called()
    assert result["current_step"] == "invalid_coherence"


@patch("agents.nodes_rag.structured_llm")
def test_validation_node_fallback_erreur_llm(mock_llm, base_state):
    """Erreur LLM → fallback valid."""
    base_state.retrieved_movies = [MockFilmDetail()]
    mock_extractor = MagicMock()
    mock_extractor.invoke.side_effect = Exception("LLM down")
    mock_llm.with_structured_output.return_value = mock_extractor

    result = validation_node(base_state)

    assert result["current_step"] == "valid"


# ==============================================================================
# format_cards_node
# ==============================================================================


@patch("agents.nodes_rag.get_films_short_by_ids")
@patch("agents.nodes_rag.db_session")
def test_format_cards_nominal(mock_db, mock_get, base_state):
    """Hydratation SQL réussie → cards_ready avec last_displayed_movies_id."""
    base_state.retrieved_movies = [MockFilmShort(tmdb_id=1), MockFilmShort(tmdb_id=2)]
    mock_db.return_value.__enter__.return_value = MagicMock()
    mock_get.return_value = [MockFilmShort(tmdb_id=1), MockFilmShort(tmdb_id=2)]

    result = format_cards_node(base_state)

    assert result["current_step"] == "cards_ready"
    assert result["last_displayed_movies_id"] == [1, 2]
    assert len(result["retrieved_movies"]) == 2


@patch("agents.nodes_rag.get_films_short_by_ids")
@patch("agents.nodes_rag.db_session")
def test_format_cards_retrieved_movies_vide(mock_db, mock_get, base_state):
    """retrieved_movies vide → no_results sans appel SQL."""
    base_state.retrieved_movies = []

    result = format_cards_node(base_state)

    mock_get.assert_not_called()
    assert result["current_step"] == "no_results"


@patch("agents.nodes_rag.get_films_short_by_ids")
@patch("agents.nodes_rag.db_session")
def test_format_cards_erreur_sql(mock_db, mock_get, base_state):
    """Erreur SQL → no_results, retrieved_movies vide, pas d'exception."""
    base_state.retrieved_movies = [MockFilmShort()]
    mock_db.return_value.__enter__.side_effect = Exception("DB down")

    result = format_cards_node(base_state)

    assert result["current_step"] == "no_results"
    assert result["retrieved_movies"] == []


# ==============================================================================
# validation_film_node
# ==============================================================================


@patch("agents.nodes_rag.structured_llm")
def test_validation_film_cas2_pass_total(mock_llm, base_state):
    """Tous les films valides → valid, retrieved_movies inchangé."""
    films = [
        MockFilmShort(tmdb_id=1, title="Alien"),
        MockFilmShort(tmdb_id=2, title="The Shining"),
    ]
    base_state.retrieved_movies = films
    mock_extractor = MagicMock()
    mock_extractor.invoke.return_value = MagicMock(
        valid_titles=["Alien", "The Shining"],
        invalid_titles=[],
        feedback="Tous cohérents.",
    )
    mock_llm.with_structured_output.return_value = mock_extractor

    result = validation_film_node(base_state)

    assert result["current_step"] == "valid"
    assert len(result["retrieved_movies"]) == 2


@patch("agents.nodes_rag.structured_llm")
def test_validation_film_cas3_pass_partiel(mock_llm, base_state):
    """Certains films valides → valid_partial, liste filtrée."""
    films = [
        MockFilmShort(tmdb_id=1, title="Alien"),
        MockFilmShort(tmdb_id=2, title="Film Hors-Sujet"),
    ]
    base_state.retrieved_movies = films
    mock_extractor = MagicMock()
    mock_extractor.invoke.return_value = MagicMock(
        valid_titles=["Alien"],
        invalid_titles=["Film Hors-Sujet"],
        feedback="Un film hors-sujet.",
    )
    mock_llm.with_structured_output.return_value = mock_extractor

    result = validation_film_node(base_state)

    assert result["current_step"] == "valid_partial"
    assert len(result["retrieved_movies"]) == 1
    assert result["retrieved_movies"][0].title == "Alien"


@patch("agents.nodes_rag.structured_llm")
def test_validation_film_cas4_fail_total(mock_llm, base_state):
    """Aucun film valide → invalid_coherence, retry_count incrémenté."""
    base_state.retrieved_movies = [MockFilmShort(title="Film Hors-Sujet")]
    base_state.retry_count = 0
    mock_extractor = MagicMock()
    mock_extractor.invoke.return_value = MagicMock(
        valid_titles=[],
        invalid_titles=["Film Hors-Sujet"],
        feedback="Aucun film cohérent.",
    )
    mock_llm.with_structured_output.return_value = mock_extractor

    result = validation_film_node(base_state)

    assert result["current_step"] == "invalid_coherence"
    assert result["retry_count"] == 1


@patch("agents.nodes_rag.structured_llm")
def test_validation_film_cas1_retrieved_movies_vide(mock_llm, base_state):
    """retrieved_movies vide → invalid_coherence direct."""
    base_state.retrieved_movies = []

    result = validation_film_node(base_state)

    mock_llm.with_structured_output.assert_not_called()
    assert result["current_step"] == "invalid_coherence"


@patch("agents.nodes_rag.structured_llm")
def test_validation_film_fallback_erreur_llm(mock_llm, base_state):
    """Erreur LLM → fallback valid avec tous les films."""
    films = [MockFilmShort(title="Alien")]
    base_state.retrieved_movies = films
    mock_extractor = MagicMock()
    mock_extractor.invoke.side_effect = Exception("LLM down")
    mock_llm.with_structured_output.return_value = mock_extractor

    result = validation_film_node(base_state)

    assert result["current_step"] == "valid"
    assert len(result["retrieved_movies"]) == 1


# ==============================================================================
# load_film_node
# ==============================================================================


@patch("agents.nodes_rag.get_films_details_by_ids")
def test_load_film_cas1_ids_vides(mock_sql, base_state):
    """Aucun ID en mémoire → intent_rupture, branch=RAG."""
    base_state.last_displayed_movies_id = []

    result = load_film_node(base_state)

    mock_sql.assert_not_called()
    assert result["current_step"] == "intent_rupture"
    assert result["branch_search_wiki"] == "RAG"
    assert result["retrieved_movies"] == []


@patch("agents.nodes_rag.get_films_details_by_ids")
def test_load_film_cas2_sql_vide(mock_sql, base_state):
    """ID en mémoire mais film absent en SQL → intent_rupture."""
    base_state.last_displayed_movies_id = [999]
    mock_sql.return_value = []

    result = load_film_node(base_state)

    assert result["current_step"] == "intent_rupture"
    assert result["retrieved_movies"] == []


@patch("agents.nodes_rag.get_films_details_by_ids")
def test_load_film_cas2_erreur_sql(mock_sql, base_state):
    """Erreur SQL → intent_rupture, pas d'exception."""
    base_state.last_displayed_movies_id = [123]
    mock_sql.side_effect = Exception("DB down")

    result = load_film_node(base_state)

    assert result["current_step"] == "intent_rupture"
    assert result["retrieved_movies"] == []


@patch("agents.nodes_rag.get_films_details_by_ids")
def test_load_film_cas3_succes(mock_sql, base_state):
    """Film chargé → film_loaded, branch=DISCUSSION."""
    base_state.last_displayed_movies_id = [123]
    mock_sql.return_value = [MockFilmDetail()]

    result = load_film_node(base_state)

    assert result["current_step"] == "film_loaded"
    assert result["branch_search_wiki"] == "DISCUSSION"
    assert len(result["retrieved_movies"]) == 1
    assert result["retrieved_movies"][0].title == "Alien"


@patch("agents.nodes_rag.get_films_details_by_ids")
def test_load_film_last_displayed_none(mock_sql, base_state):
    """last_displayed_movies_id=None → traité comme liste vide."""
    base_state.last_displayed_movies_id = None

    result = load_film_node(base_state)

    mock_sql.assert_not_called()
    assert result["current_step"] == "intent_rupture"


# ==============================================================================
# verif_film_node
# ==============================================================================


@patch("agents.nodes_rag.structured_llm")
def test_verif_film_cas1_retrieved_movies_vide(mock_llm, base_state):
    """retrieved_movies vide → intent_rupture, enrich_ids vide."""
    base_state.retrieved_movies = []

    result = verif_film_node(base_state)

    mock_llm.with_structured_output.assert_not_called()
    assert result["current_step"] == "intent_rupture"
    assert result["enrich_ids"] == []


@patch("agents.nodes_rag.structured_llm")
def test_verif_film_cas2_fallback_erreur_llm(mock_llm, base_state):
    """Erreur LLM → fallback valid, enrich_ids vide."""
    base_state.retrieved_movies = [MockFilmDetail()]
    mock_extractor = MagicMock()
    mock_extractor.invoke.side_effect = Exception("LLM down")
    mock_llm.with_structured_output.return_value = mock_extractor

    result = verif_film_node(base_state)

    assert result["current_step"] == "valid"
    assert result["enrich_ids"] == []


@patch("agents.nodes_rag.structured_llm")
def test_verif_film_cas3_valid_missing_data(mock_llm, base_state):
    """Un film avec donnée manquante → valid_missing_data, enrich_ids rempli."""
    films = [MockFilmDetail(tmdb_id=123, title="Alien")]
    base_state.retrieved_movies = films
    mock_extractor = MagicMock()
    mock_extractor.invoke.return_value = MagicMock(
        sujet="synopsis",
        films_ok=[],
        films_missing=["Alien"],
        feedback="Synopsis absent.",
    )
    mock_llm.with_structured_output.return_value = mock_extractor

    result = verif_film_node(base_state)

    assert result["current_step"] == "valid_missing_data"
    assert 123 in result["enrich_ids"]


@patch("agents.nodes_rag.structured_llm")
def test_verif_film_cas4_valid_toutes_donnees(mock_llm, base_state):
    """Toutes données disponibles → valid, enrich_ids vide."""
    films = [MockFilmDetail(tmdb_id=123, title="Alien")]
    base_state.retrieved_movies = films
    mock_extractor = MagicMock()
    mock_extractor.invoke.return_value = MagicMock(
        sujet="durée",
        films_ok=["Alien"],
        films_missing=[],
        feedback="Durée disponible : 117 min.",
    )
    mock_llm.with_structured_output.return_value = mock_extractor

    result = verif_film_node(base_state)

    assert result["current_step"] == "valid"
    assert result["enrich_ids"] == []
    assert result["data_enriched"] == "Durée disponible : 117 min."


@patch("agents.nodes_rag.structured_llm")
def test_verif_film_multi_films_partiel(mock_llm, base_state):
    """Plusieurs films, certains avec données manquantes → enrich_ids partiel."""
    films = [
        MockFilmDetail(tmdb_id=1, title="Alien"),
        MockFilmDetail(tmdb_id=2, title="The Shining"),
    ]
    base_state.retrieved_movies = films
    mock_extractor = MagicMock()
    mock_extractor.invoke.return_value = MagicMock(
        sujet="synopsis",
        films_ok=["Alien"],
        films_missing=["The Shining"],
        feedback="Synopsis de The Shining absent.",
    )
    mock_llm.with_structured_output.return_value = mock_extractor

    result = verif_film_node(base_state)

    assert result["current_step"] == "valid_missing_data"
    assert result["enrich_ids"] == [2]
    assert 1 not in result["enrich_ids"]


@patch("agents.nodes_rag.structured_llm")
def test_verif_film_film_sans_attributs_optionnels(mock_llm, base_state):
    """Film avec attributs None → getattr défensif, pas d'exception."""
    film = MagicMock()
    film.tmdb_id = 42
    film.title = "Film Incomplet"
    film.realisateur = None
    film.director = None
    film.release_date = None
    film.genres = None
    film.synopsis = None
    film.tmdb_score = None
    film.imdb_score = None
    film.rotten_tomatometer = None
    film.runtime = None
    film.collection = None
    film.tagline = None
    base_state.retrieved_movies = [film]

    mock_extractor = MagicMock()
    mock_extractor.invoke.return_value = MagicMock(
        sujet="titre", films_ok=["Film Incomplet"], films_missing=[], feedback="ok"
    )
    mock_llm.with_structured_output.return_value = mock_extractor

    result = verif_film_node(base_state)

    assert result["current_step"] == "valid"


def test_validation_node_cas_4_titre_corrige_identifie(base_state):
    """
    Cas 4 : Validation Échouée du validateur mais titre trouvé.
    """
    # 1. On prépare le state pour passer l'étape de garde initiale (retrieved_movies)
    mock_film = MagicMock()
    mock_film.title = "Alien"
    base_state.retrieved_movies = [mock_film]
    base_state.user_query = "test query"
    base_state.retry_count = 0
    base_state.steps = []

    # 2. On configure TRÈS précisément le comportement du mock de résultat
    mock_validation_result = MagicMock()

    # On force à False pour ne pas entrer dans les Cas 2 et Cas 3
    mock_validation_result.is_relevant = False
    mock_validation_result.has_missing_info = False

    # On configure les attributs pour le Cas 4
    mock_validation_result.corrected_title = "The Shining"
    mock_validation_result.feedback = "Le film demandé est 'The Shining'."

    # On mocke le model_dump() car la ligne 567 l'appelle pour le logger.info
    mock_validation_result.model_dump.return_value = {
        "is_relevant": False,
        "has_missing_info": False,
        "corrected_title": "The Shining",
        "feedback": "Le film demandé est 'The Shining'.",
    }

    # 3. On injecte ce mock lors de l'appel du LLM
    with patch("agents.nodes_rag.structured_llm") as mock_llm:
        # structured_llm.with_structured_output(ValidationResult).invoke(...)
        mock_llm.with_structured_output.return_value.invoke.return_value = (
            mock_validation_result
        )

        # 4. Exécution du nœud
        result = validation_node(base_state)

        # 5. Assertions
        assert result.get("current_step") == "invalid_coherence"
        assert result.get("answer") == "The Shining"
