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
"""agents/graph.py"""

from langgraph.graph import END, StateGraph

from agents.nodes import (
    direct_movie_detail_node,
    filter_and_search_hybrid_node,
    route_after_title_check,
    title_router_node,
    validation_node,
)
from agents.state import AgentState

workflow = StateGraph(AgentState)

# Enregistrement des nœuds
workflow.add_node("title_router", title_router_node)
workflow.add_node("validator", validation_node)
workflow.add_node("direct_movie_detail", direct_movie_detail_node)
workflow.add_node("filter_and_search_hybrid", filter_and_search_hybrid_node)

# Point d'entrée
workflow.set_entry_point("title_router")

# title_router → validator (toujours, pas de conditional ici)
workflow.add_edge("title_router", "validator")

# validator → conditional → nœud métier
workflow.add_conditional_edges(
    "validator",
    route_after_title_check,
    {
        "direct_movie_detail": "direct_movie_detail",
        "filter_and_search_hybrid": "filter_and_search_hybrid",
    },
)

# Fin de cycle
workflow.add_edge("direct_movie_detail", END)
workflow.add_edge("filter_and_search_hybrid", END)

graph = workflow.compile()
