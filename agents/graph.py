"""agents/graph.py
Module d'assemblage et de compilation du graphe de workflow (LangGraph).

Ce fichier est le cœur décisionnel de l'agent. Il définit l'architecture du
graphe d'état (StateGraph), crée les nœuds de traitement (LLM, appels d'outils,
mise en forme) et configure les transitions conditionnelles (Conditional Edges)
pour orienter dynamiquement la réflexion selon la demande de l'utilisateur.

Architecture du flux (Workflow) :
    1. Entrée / Routage : Analyse de la requête pour aiguiller vers le bon nœud.
    2. Exécution des Outils : Appels ciblés de 'sql_tools', 'vector_tools'
       ou 'wiki_tools' pour rassembler le contexte nécessaire.
    3. Synthèse et RAG : Fusion des données récupérées, génération de la réponse
       finale par le LLM et structuration du JSON des 5 films.

Le graphe compilé ici est directement importé par les routes de l'API pour
exécuter les sessions de chat.

Dépendances principales :
    - langgraph.graph (StateGraph, START, END)
    - langchain_ollama (ChatOllama ou OllamaLLM pour le raisonnement local)
    - .state (AgentState)
    - .prompts (Gabarits d'instructions)
    - .tools (sql_tools, vector_tools, wiki_tools)

Auteur/Responsable : Équipe Agents / Hanna (Intégration API)
"""

"""agents/graph.py
Module d'assemblage et de compilation du graphe d'agents HorRAGor.

Ce fichier orchestre la cinématique globale du système :
1. Analyse de l'intention (Router)
2. Aiguillage conditionnel (Processus A ou B)
3. Exécution et agrégation des résultats.
"""
import sys
from pathlib import Path

from langgraph.graph import END, START, StateGraph

root_path = Path(__file__).resolve().parent.parent
if str(root_path) not in sys.path:  # pragma: no cover
    sys.path.insert(0, str(root_path))


from agents.nodes import (
    direct_movie_detail_node,
    filter_and_search_hybrid_node,
    route_after_title_check,
    route_after_validation,
    title_router_node,
    validation_node,
    wikipedia_enrich_node,
)
from agents.state import AgentState

# 1. Initialisation du graphe avec l'état partagé de l'agent
workflow = StateGraph(AgentState)

# 2. Enregistrement de tous les nœuds de calcul et décision
workflow.add_node("title_router", title_router_node)
workflow.add_node("direct_movie_detail", direct_movie_detail_node)
workflow.add_node("filter_and_search_hybrid", filter_and_search_hybrid_node)
workflow.add_node("validator", validation_node)
workflow.add_node("wikipedia_enrich", wikipedia_enrich_node)

# ==============================================================================
# CONFIGURATION DES TRANSITIONS (EDGES)
# ==============================================================================

# Point d'entrée obligatoire du graphe
workflow.add_edge(START, "title_router")

# --- FLUX ALLER (Aiguillage initial) ---
# Analyse la requête et oriente soit vers la recherche directe soit par critères
workflow.add_conditional_edges(
    "title_router",
    route_after_title_check,
    {
        "direct_movie_detail": "direct_movie_detail",
        "filter_and_search_hybrid": "filter_and_search_hybrid",
    },
)

# --- CONVERGENCE VERS LE VALIDATEUR ---
# Les deux branches métiers envoient leur réponse générée vers le nœud d'évaluation
workflow.add_edge("direct_movie_detail", "validator")
workflow.add_edge("filter_and_search_hybrid", "validator")

# --- FLUX DE RETOUR ET CORRECTION LOCALISÉE ---
# Le validateur examine state.current_step et route le flux selon les règles métier
workflow.add_conditional_edges(
    "validator",
    route_after_validation,
    {
        "go_to_end": END,  # Cas nominal (Réponse parfaite) OU aucun film trouvé
        "enrich_with_wiki": "wikipedia_enrich",  # Réponse OK mais synopsis absent (Besoin de Wikipédia)
        "retry_direct": "direct_movie_detail",  # Règle 1 : Boucle locale de régénération sur branche Titre
        "retry_hybrid": "filter_and_search_hybrid",  # Règle 2 : Boucle locale de régénération sur branche Critères
    },
)

# --- FINITION WIKIPÉDIA ---
# Une fois enrichi par l'outil externe, on coupe court et on termine le graphe
workflow.add_edge("wikipedia_enrich", END)

# ==============================================================================
# COMPILATION DU GRAPHE
# ==============================================================================
graph = workflow.compile()

# On récupère le code texte au format Mermaid
mermaid_code = graph.get_graph().draw_mermaid()

# On l'écrit dans un fichier .mmd
with open("graph.mmd", "w", encoding="utf-8") as f:
    f.write(mermaid_code)

graph_image = graph.get_graph().draw_mermaid_png()
with open("HorRAGor_graph.png", "wb") as f:
    f.write(graph_image)
    print("✅ Graphe enregistré sous 'HorRAGor_graph.png'")
