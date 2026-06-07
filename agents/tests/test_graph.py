"""tests/test_graph.py"""

from langgraph.graph.state import CompiledStateGraph

# Import des éléments définis dans agents/graph.py[cite: 1]
from agents.graph import graph, workflow
from agents.nodes import route_after_title_check
from agents.state import AgentState


def test_graph_compilation():
    """Vérifie que le graphe est bien compilé et est une instance de CompiledStateGraph[cite: 1]."""
    assert isinstance(graph, CompiledStateGraph)


def test_graph_nodes():
    """Vérifie que tous les nœuds métier sont bien enregistrés dans le workflow[cite: 1]."""
    nodes = workflow.nodes
    assert "title_router" in nodes
    assert "validator" in nodes
    assert "direct_movie_detail" in nodes
    assert "filter_and_search_hybrid" in nodes


def test_conditional_routing():
    """Test la fonction de routage utilisée par l'arête conditionnelle[cite: 1, 2]."""
    # Cas 1: Titre présent
    state_has_title = AgentState(user_query="Alien", current_step="has_title")
    assert route_after_title_check(state_has_title) == "direct_movie_detail"

    # Cas 2: Pas de titre (mode hybride)[cite: 2]
    state_no_title = AgentState(user_query="horreur", current_step="no_title")
    assert route_after_title_check(state_no_title) == "filter_and_search_hybrid"
