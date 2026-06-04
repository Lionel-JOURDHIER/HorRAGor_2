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
