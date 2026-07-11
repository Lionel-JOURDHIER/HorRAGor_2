"""agents/graph.py
Fichier de définition du StateGraph (LangGraph) pour l'agent HorRAGor v3.

Ce fichier instancie le graphe en connectant les nœuds (boîtes blanches)
aux arêtes conditionnelles (logique de routage), orchestrant ainsi les
interactions entre l'Agent RAG, l'Agent Wikipédia et l'Agent Narrateur.
"""

import sys
from pathlib import Path

from langgraph.graph import END, START, StateGraph

root_path = Path(__file__).resolve().parent.parent
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))  # pragma: no cover


import os

from agents.nodes_narrateur import narrator_node

# Imports des Nœuds depuis agents/nodes.py
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
from agents.nodes_wikipedia import (
    synthesis_node,
    wikipedia_search_node,
)

# Imports des Routeurs depuis agents/router.py
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

# Import de l'état global
from api.schemas import AgentState

os.environ["LANGGRAPH_STRICT_MSGPACK"] = "false"

# OU mieux, enregistrer les types explicitement
from langgraph.checkpoint.memory import InMemorySaver

_checkpointer = InMemorySaver()

# LOGGER
from logger import get_logger, setup_logger

setup_logger()
logger = get_logger("GRAPH")


# ==============================================================================
# WRAPPERS DE ROUTAGE (Adaptation LangGraph)
# ==============================================================================


def route_after_search_vector_wrapper(state: AgentState) -> str:
    """Dispatche la sortie de search_vector_node selon la branche active."""
    if getattr(state, "search_branch", "hybrid") == "direct":
        return route_direct_id_valid(state)
    return route_hybrid_id_valid(state)


def wrapper_route_validation_direct(state: AgentState) -> str:
    """Si la validation directe passe, évalue immédiatement le besoin de Wikipédia."""
    res = route_validation_direct(state)
    if res == "route_need_wikipedia":
        return route_need_wikipedia(state)
    return res


def wrapper_route_validation_hybrid(state: AgentState) -> str:
    """Si la validation hybride passe, évalue immédiatement le besoin de Wikipédia."""
    res = route_validation_hybrid(state)
    if res == "route_need_wikipedia":
        return route_need_wikipedia(state)
    return res


def wrapper_route_verif_film(state: AgentState) -> str:
    """Aiguille après load_film_node. Si OK, on va vérifier le film (verif_film_node)."""
    res = route_verif_film(state)
    if res == "route_need_wikipedia":
        return "verif_film_node"
    return res


def wrapper_route_return_wiki(state: AgentState) -> str:
    """Gère le retour dynamique du bloc RAG après Wikipédia."""
    res = route_return_wiki(state)

    # Debug pour voir ce qui est retourné réellement
    logger.info(f"[DEBUG] Wrapper reçoit : {res}")

    if res == "end_rag":
        if getattr(state, "search_branch", "hybrid") == "direct":
            return "card_node"
        return "format_cards_node"

    return res


# ==============================================================================
# CONSTRUCTION DU GRAPHE
# ==============================================================================


def graph():
    logger.info("Initialisation de la Machine à États (HorRAGor v3) ...")
    workflow = StateGraph(AgentState)

    # 1. DÉCLARATION DES NŒUDS --------------------------------------------------

    # Phase 1: Entrée
    workflow.add_node("intent_classifier_node", intent_classifier_node)
    workflow.add_node("title_router_node", title_router_node)

    # Phase 2: Agent RAG
    workflow.add_node("merge_filters_node", merge_filters_node)
    workflow.add_node("search_vector_node", search_vector_node)
    workflow.add_node("hydratation_node", hydratation_node)
    workflow.add_node("validation_node", validation_node)
    workflow.add_node("validation_film_node", validation_film_node)
    workflow.add_node("format_cards_node", format_cards_node)
    workflow.add_node("card_node", card_node)

    # Phase 3: Branche Discussion
    workflow.add_node("load_film_node", load_film_node)
    workflow.add_node("verif_film_node", verif_film_node)

    # Phase 4: Agent Wikipédia
    workflow.add_node("wikipedia_search_node", wikipedia_search_node)
    workflow.add_node("synthesis_node", synthesis_node)

    # Phase 5: Agent Narrateur
    workflow.add_node("narrator_node", narrator_node)

    # 2. DÉCLARATION DES ARÊTES (EDGES) ------------------------------------------

    # --- Point d'entrée ---
    workflow.add_edge(START, "intent_classifier_node")

    # --- Routage Intention ---
    workflow.add_conditional_edges(
        "intent_classifier_node",
        route_by_intent,
        {
            "Load_film_node": "load_film_node",
            "route_after_title_check": "title_router_node",
            "narrator_node": "narrator_node",
        },
    )

    # --- Routage Titre ---
    workflow.add_conditional_edges(
        "title_router_node",
        route_after_title_check,
        {
            "direct_movie_detail": "search_vector_node",
            "filter_and_search_hybrid": "merge_filters_node",
        },
    )

    workflow.add_edge("merge_filters_node", "search_vector_node")

    # --- Évaluation Sortie Recherche Vectorielle ---
    workflow.add_conditional_edges(
        "search_vector_node",
        route_after_search_vector_wrapper,
        {
            "Affichage_film_unique": "hydratation_node",  # Branche Directe
            "Affichage_films": "validation_film_node",  # Branche Hybride
            "Search_vector_node": "search_vector_node",  # Retry Direct
            "Merge_filters_node": "merge_filters_node",  # Retry Hybride
            "narrator_node": "narrator_node",  # Fail global
        },
    )

    # --- Branche Directe (Processus A) ---
    workflow.add_edge("hydratation_node", "validation_node")
    workflow.add_conditional_edges(
        "validation_node",
        wrapper_route_validation_direct,
        {
            "wikipedia_search_node": "wikipedia_search_node",
            "card_node": "card_node",
            "format_cards_node": "format_cards_node",
            "synthesis_node": "synthesis_node",
            "narrator_node": "narrator_node",
            "Search_vector_node": "search_vector_node",
        },
    )

    # --- Branche Hybride (Processus B) ---
    workflow.add_conditional_edges(
        "validation_film_node",
        wrapper_route_validation_hybrid,
        {
            "wikipedia_search_node": "wikipedia_search_node",
            "card_node": "card_node",
            "format_cards_node": "format_cards_node",
            "synthesis_node": "synthesis_node",
            "narrator_node": "narrator_node",
            "Merge_filters_node": "merge_filters_node",
        },
    )

    # --- Branche Discussion (Bypass) ---
    workflow.add_conditional_edges(
        "load_film_node",
        wrapper_route_verif_film,
        {
            "route_after_title_check": "title_router_node",
            "merge_filters_node": "merge_filters_node",
            "verif_film_node": "verif_film_node",
        },
    )

    workflow.add_conditional_edges(
        "verif_film_node",
        route_need_wikipedia,
        {
            "wikipedia_search_node": "wikipedia_search_node",
            "narrator_node": "narrator_node",
        },
    )

    # --- Agent Wikipédia & Synthèse ---
    workflow.add_conditional_edges(
        "wikipedia_search_node",
        wrapper_route_return_wiki,
        {
            "card_node": "card_node",
            "format_cards_node": "format_cards_node",
            "narrator_node": "narrator_node",
            "synthesis_node": "synthesis_node",
        },
    )

    # --- Convergence vers le Narrateur et Fin ---
    workflow.add_edge("synthesis_node", "narrator_node")
    workflow.add_edge("card_node", "narrator_node")
    workflow.add_edge("format_cards_node", "narrator_node")
    workflow.add_edge("narrator_node", END)

    logger.info("Machine à États compilée avec succès.")

    # ==============================================================================
    # COMPILATION DU GRAPHE
    # ==============================================================================
    graph = workflow.compile(checkpointer=_checkpointer)

    # On récupère le code texte au format Mermaid
    mermaid_code = graph.get_graph().draw_mermaid()

    # On l'écrit dans un fichier .mmd
    with open("graph.mmd", "w", encoding="utf-8") as f:
        f.write(mermaid_code)

    graph_image = graph.get_graph().draw_mermaid_png()
    with open("HorRAGor_graph.png", "wb") as f:
        f.write(graph_image)
        print("✅ Graphe enregistré sous 'HorRAGor_graph.png'")

    return graph


if __name__ == "__main__":
    # Instanciation de l'application
    app = build_graph()
