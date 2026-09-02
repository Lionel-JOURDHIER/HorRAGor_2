from unittest.mock import MagicMock, mock_open, patch

from langgraph.graph.state import CompiledStateGraph

# Import des éléments définis dans agents/graph.py
from agents.graph import (
    graph,
    route_after_search_vector_wrapper,
    wrapper_route_return_wiki,
    wrapper_route_validation_direct,
    wrapper_route_validation_hybrid,
    wrapper_route_verif_film,
)
from shared.schemas import AgentState


def test_graph_compilation_and_nodes():
    """Vérifie la compilation et la présence de tous les nœuds de la v3."""
    # On utilise mock_open() pour intercepter proprement les écritures des fichiers Mermaid
    with (
        patch("builtins.open", mock_open()),
        patch("langgraph.graph.state.CompiledStateGraph.get_graph") as mock_get_graph,
    ):
        mock_graph_obj = MagicMock()
        mock_graph_obj.draw_mermaid.return_value = "mermaid code"
        mock_graph_obj.draw_mermaid_png.return_value = b"png bytes"
        mock_get_graph.return_value = mock_graph_obj

        # Appel de la fonction de construction du graphe
        app = graph()

        assert isinstance(app, CompiledStateGraph)

        # Récupération du builder de graphe pour inspecter les nœuds enregistrés
        nodes = app.builder.nodes
        assert "intent_classifier_node" in nodes
        assert "title_router_node" in nodes
        assert "merge_filters_node" in nodes
        assert "search_vector_node" in nodes
        assert "hydratation_node" in nodes
        assert "validation_node" in nodes
        assert "validation_film_node" in nodes
        assert "format_cards_node" in nodes
        assert "card_node" in nodes
        assert "load_film_node" in nodes
        assert "verif_film_node" in nodes
        assert "wikipedia_search_node" in nodes
        assert "synthesis_node" in nodes
        assert "narrator_node" in nodes


# ==============================================================================
# TESTS DES WRAPPERS DE ROUTAGE LOCAUX
# ==============================================================================


def test_route_after_search_vector_wrapper():
    """Couvre les branches de route_after_search_vector_wrapper selon la branche active."""
    state_direct = AgentState(user_query="test")
    state_direct.search_branch = "direct"

    state_hybrid = AgentState(user_query="test")
    state_hybrid.search_branch = "hybrid"

    with (
        patch("agents.graph.route_direct_id_valid", return_value="direct_ok") as m_dir,
        patch("agents.graph.route_hybrid_id_valid", return_value="hybrid_ok") as m_hyb,
    ):
        assert route_after_search_vector_wrapper(state_direct) == "direct_ok"
        assert route_after_search_vector_wrapper(state_hybrid) == "hybrid_ok"


def test_wrapper_route_validation_direct():
    """Couvre le passage par Wikipédia ou la route directe alternative."""
    state = AgentState(user_query="test")

    with (
        patch(
            "agents.graph.route_validation_direct", return_value="route_need_wikipedia"
        ),
        patch(
            "agents.graph.route_need_wikipedia", return_value="wikipedia_search_node"
        ),
    ):
        assert wrapper_route_validation_direct(state) == "wikipedia_search_node"

    with patch("agents.graph.route_validation_direct", return_value="card_node"):
        assert wrapper_route_validation_direct(state) == "card_node"


def test_wrapper_route_validation_hybrid():
    """Couvre le passage par Wikipédia ou la route hybride alternative."""
    state = AgentState(user_query="test")

    with (
        patch(
            "agents.graph.route_validation_hybrid", return_value="route_need_wikipedia"
        ),
        patch(
            "agents.graph.route_need_wikipedia", return_value="wikipedia_search_node"
        ),
    ):
        assert wrapper_route_validation_hybrid(state) == "wikipedia_search_node"

    with patch(
        "agents.graph.route_validation_hybrid", return_value="format_cards_node"
    ):
        assert wrapper_route_validation_hybrid(state) == "format_cards_node"


def test_wrapper_route_verif_film():
    """Couvre l'aiguillage après le chargement du film."""
    state = AgentState(user_query="test")

    with patch("agents.graph.route_verif_film", return_value="route_need_wikipedia"):
        assert wrapper_route_verif_film(state) == "verif_film_node"

    with patch("agents.graph.route_verif_film", return_value="merge_filters_node"):
        assert wrapper_route_verif_film(state) == "merge_filters_node"


def test_wrapper_route_return_wiki():
    """Couvre la gestion du retour Wikipédia (direct vs hybride vs autre)."""
    state_direct = AgentState(user_query="test")
    state_direct.search_branch = "direct"

    state_hybrid = AgentState(user_query="test")
    state_hybrid.search_branch = "hybrid"

    # Cas où Wikipédia retourne "end_rag"
    with patch("agents.graph.route_return_wiki", return_value="end_rag"):
        assert wrapper_route_return_wiki(state_direct) == "card_node"
        assert wrapper_route_return_wiki(state_hybrid) == "format_cards_node"

    # Cas où Wikipédia retourne une autre instruction
    with patch("agents.graph.route_return_wiki", return_value="narrator_node"):
        assert wrapper_route_return_wiki(state_direct) == "narrator_node"
