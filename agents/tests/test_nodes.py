"""tests/test_nodes.py"""

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage

from agents.nodes import (
    direct_movie_detail_node,
    filter_and_search_hybrid_node,
    route_after_title_check,
    title_router_node,
    validation_node,
)
from agents.state import AgentState, AgentStep
from api.schemas import ChatFilters

# --- Fixtures & Objets factices pour les tests ---


@pytest.fixture
def base_state():
    return AgentState(user_query="test query", initial_filters=ChatFilters())


class MockFilmShort:
    def __init__(self):
        self.tmdb_id = 123
        self.title = "Test Film"
        self.release_date = "2020-01-01"
        self.genres = ["Horror"]
        self.tmdb_score = 8.0


class MockFilmDetail:
    def __init__(self):
        self.title = "Test Film Complete"
        self.original_title = "Test Film"
        self.realisateur = "John Doe"
        self.director = "John Doe"
        self.release_date = "2020-01-01"
        self.runtime = 120
        self.genres = ["Horror"]
        self.synopsis = "A scary movie."
        self.tagline = "Be afraid."
        self.tmdb_score = 8.0
        self.imdb_score = 7.5
        self.rotten_tomatometer = 90
        self.rotten_audience_score = 85
        self.aggregated_score = 8.0
        self.collection = None


# --- Tests des Nodes ---


def test_route_after_title_check(base_state):
    """Vérifie l'aiguillage selon l'état actuel[cite: 2]."""
    base_state.current_step = "has_title"
    assert route_after_title_check(base_state) == "direct_movie_detail"

    base_state.current_step = "something_else"
    assert route_after_title_check(base_state) == "filter_and_search_hybrid"


@patch("agents.nodes.llm")
def test_title_router_node_found(mock_llm, base_state):
    """Test title_router_node avec un titre détecté[cite: 2]."""
    mock_llm.invoke.return_value = AIMessage(content="Alien")

    result = title_router_node(base_state)
    assert result["current_step"] == "has_title"
    assert result["answer"] == "Alien"


@patch("agents.nodes.llm")
def test_title_router_node_not_found(mock_llm, base_state):
    """Test title_router_node sans titre détecté[cite: 2]."""
    mock_llm.invoke.return_value = AIMessage(content="")

    result = title_router_node(base_state)
    assert result["current_step"] == "no_title"


def test_validation_node_empty_query():
    """Vérifie que validation_node intercepte les requêtes vides[cite: 2]."""
    state = AgentState(user_query="   ")
    result = validation_node(state)
    assert result["current_step"] == "no_title"


def test_validation_node_valid_query(base_state):
    """Vérifie que validation_node laisse passer une requête valide[cite: 2]."""
    base_state.current_step = "has_title"
    result = validation_node(base_state)
    # L'état renvoyé doit juste mettre à jour les étapes, pas d'écrasement de current_step[cite: 2]
    assert "current_step" not in result


@patch("agents.nodes.search_vector_catalog.func")
@patch("agents.nodes.llm")
def test_direct_movie_detail_node_no_vector_result(mock_llm, mock_search, base_state):
    """Test le cas où FAISS ne renvoie aucun film[cite: 2]."""
    mock_search.return_value = []
    mock_llm.invoke.return_value = AIMessage(content="Aucun film")
    base_state.answer = "Inconnu"

    result = direct_movie_detail_node(base_state)
    assert result["current_step"] == "completed"
    assert "Aucun film" in result["answer"]


@patch("agents.nodes.search_vector_catalog.func")
@patch("agents.nodes.get_film_details_by_id")
@patch("agents.nodes.db_session")
@patch("agents.nodes.llm")
def test_direct_movie_detail_node_no_db_result(
    mock_llm, mock_db_session, mock_get_detail, mock_search, base_state
):
    """Test le cas où le film existe dans FAISS mais pas en BDD[cite: 2]."""
    mock_search.return_value = [MockFilmShort()]
    mock_db_session.return_value.__enter__.return_value = MagicMock()
    mock_get_detail.return_value = None
    mock_llm.invoke.return_value = AIMessage(content="Aucun film")
    base_state.answer = "Alien"

    result = direct_movie_detail_node(base_state)
    assert result["current_step"] == "completed"


@patch("agents.nodes.search_vector_catalog.func")
@patch("agents.nodes.get_film_details_by_id")
@patch("agents.nodes.db_session")
@patch("agents.nodes.llm")
def test_direct_movie_detail_node_success(
    mock_llm, mock_db_session, mock_get_detail, mock_search, base_state
):
    """Test le chemin de succès complet pour le détail d'un film[cite: 2]."""
    mock_search.return_value = [MockFilmShort()]
    mock_get_detail.return_value = MockFilmDetail()
    mock_db_session.return_value.__enter__.return_value = MagicMock()
    mock_llm.invoke.return_value = AIMessage(content="Voici la fiche...")

    result = direct_movie_detail_node(base_state)
    assert result["current_step"] == "completed"
    assert result["answer"] == "Voici la fiche..."
    assert len(result["retrieved_movies"]) == 1


def test_filter_and_search_hybrid_node_restrictive(base_state):
    """Test l'hybride où le SQL filtre absolument tout."""
    # Utilisation de 'with patch' pour garantir l'isolation parfaite des mocks
    with (
        patch("agents.nodes.structured_llm") as mock_structured,
        patch("agents.nodes.filter_films_by_criteria.func") as mock_sql,
        patch("agents.nodes.search_vector_catalog.func") as mock_search,
        patch("agents.nodes.llm") as mock_llm,
    ):
        # Configuration de l'extracteur JSON
        mock_extractor = MagicMock()
        mock_extractor.invoke.return_value = ChatFilters()
        mock_structured.with_structured_output.return_value = mock_extractor

        # Simulation d'un retour SQL vide
        mock_sql.return_value = []
        mock_llm.invoke.return_value = AIMessage(content="Aucun film")

        # Exécution du nœud
        result = filter_and_search_hybrid_node(base_state)

        # Vérifications
        assert result["retrieved_movies"] == []
        mock_search.assert_not_called()


def test_filter_and_search_hybrid_node_success_and_year_swap(base_state):
    """Test le succès et l'inversion de l'année min/max."""
    with (
        patch("agents.nodes.structured_llm") as mock_structured,
        patch("agents.nodes.filter_films_by_criteria.func") as mock_sql,
        patch("agents.nodes.search_vector_catalog.func") as mock_search,
        patch("agents.nodes.llm") as mock_llm,
    ):
        # Configuration de l'extracteur JSON avec des dates inversées
        mock_extractor = MagicMock()
        mock_extractor.invoke.return_value = ChatFilters(
            release_year_min=2020, release_year_max=1990
        )
        mock_structured.with_structured_output.return_value = mock_extractor

        # Simulation des retours BDD et FAISS
        mock_sql.return_value = [1, 2, 3]
        mock_search.return_value = [MockFilmShort()]
        mock_llm.invoke.return_value = AIMessage(content="Voici les recos")

        # Exécution du nœud
        result = filter_and_search_hybrid_node(base_state)

        # Vérifications de la logique interne
        assert result["sql_filters"].release_year_min == 1990
        assert result["sql_filters"].release_year_max == 2020
        assert result["current_step"] == "completed"
        assert len(result["retrieved_movies"]) == 1


# --- Fixture locale si elle n'est pas déjà dans ton fichier ---
@pytest.fixture
def base_state_hybrid():
    """Fournit un état initial avec un filtre pré-existant pour tester le merge."""
    return AgentState(
        user_query="Un film de science-fiction des années 90",
        initial_filters=ChatFilters(genres_excluded=["Comedy"]),
        steps=[AgentStep(step="start", status="init")],
    )


# ==============================================================================
# TESTS CIBLÉS POUR LES LIGNES ROUGES
# ==============================================================================


def test_hybrid_node_full_red_lines_coverage(base_state_hybrid):
    """
    Cible : Les steps, l'extraction LLM, le merge des dictionnaires,
    l'inversion des années, et les appels SQL/FAISS.
    """
    with (
        patch("agents.nodes.structured_llm") as mock_structured,
        patch("agents.nodes.filter_films_by_criteria.func") as mock_sql,
        patch("agents.nodes.search_vector_catalog.func") as mock_search,
        patch("agents.nodes.llm") as mock_llm,
    ):
        # 1. Force l'extracteur à renvoyer des dates inversées et un nouveau critère
        mock_extractor = MagicMock()
        mock_extractor.invoke.return_value = ChatFilters(
            release_year_min=2000,
            release_year_max=1990,  # 🔴 Cible la condition d'inversion des années
            realisateur="Steven Spielberg",
        )
        mock_structured.with_structured_output.return_value = mock_extractor

        # 2. Simule un retour SQL positif (🔴 cible candidate_ids = ...)
        mock_sql.return_value = [1, 2, 3]

        # 3. Simule un retour FAISS (🔴 cible recommendations = ...)
        mock_search.return_value = [MockFilmShort()]

        # 4. Simule la réponse finale
        mock_llm.invoke.return_value = AIMessage(content="Voici la recommandation.")

        # --- EXÉCUTION ---
        result = filter_and_search_hybrid_node(base_state_hybrid)

        # --- VÉRIFICATIONS DES LIGNES ROUGES ---

        # Vérifie que les steps ont bien été "appended" (🔴 cible steps.append...)
        step_names = [s.step for s in result["steps"]]
        assert "filter_extraction" in step_names
        assert "sql_filtering" in step_names
        assert "vector_recommendations" in step_names
        assert "generation" in step_names

        # Vérifie le Merge des filtres (🔴 cible la boucle for key, value in extracted...)
        assert (
            result["sql_filters"].realisateur == "Steven Spielberg"
        )  # Ajouté par le LLM
        assert result["sql_filters"].genres_excluded == [
            "Comedy"
        ]  # Conservé depuis initial_filters

        # Vérifie l'inversion des années (🔴 cible la condition release_year_min > release_year_max)
        assert result["sql_filters"].release_year_min == 1990
        assert result["sql_filters"].release_year_max == 2000

        # Vérifie les appels aux outils
        mock_sql.assert_called_once()
        mock_search.assert_called_once()


def test_hybrid_node_empty_sql_short_circuit(base_state_hybrid):
    """
    Cible : Le cas où SQL ne renvoie rien, ce qui génère une liste vide
    et évite de planter FAISS.
    """
    with (
        patch("agents.nodes.structured_llm") as mock_structured,
        patch("agents.nodes.filter_films_by_criteria.func") as mock_sql,
        patch("agents.nodes.search_vector_catalog.func") as mock_search,
        patch("agents.nodes.llm") as mock_llm,
    ):
        # Extraction standard
        mock_extractor = MagicMock()
        mock_extractor.invoke.return_value = ChatFilters()
        mock_structured.with_structured_output.return_value = mock_extractor

        # 🔴 Simule un filtre SQL ultra-restrictif (aucun ID trouvé)
        mock_sql.return_value = []

        mock_llm.invoke.return_value = AIMessage(content="Aucun film.")

        # --- EXÉCUTION ---
        result = filter_and_search_hybrid_node(base_state_hybrid)

        # --- VÉRIFICATIONS ---
        # FAISS ne doit absolument pas être appelé si SQL = []
        mock_search.assert_not_called()
        assert result["retrieved_movies"] == []
