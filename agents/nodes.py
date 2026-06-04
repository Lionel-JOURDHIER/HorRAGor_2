"""agents/nodes.py
Module de définition des nœuds (Nodes) du graphe de l'agent LangGraph.

Ce fichier contient les fonctions Python autonomes qui représentent les étapes de
calcul et de décision du graphe. Chaque nœud reçoit l'état actuel ('AgentState'),
exécute une action spécifique (appel LLM, orchestration d'outils, formatage de données),
puis retourne les mises à jour à appliquer à l'état.

Nœuds principaux à implémenter :
    - node_classifier : Interroge le LLM avec le prompt de classification pour
      déterminer l'intention de l'utilisateur.
    - node_extractor : Extrait les entités et critères de filtrage (réalisateur, genre).
    - node_sql_query / node_vector_search : Appellent respectivement les outils SQL
      ou FAISS pour récupérer les données de films pertinents.
    - node_wikipedia_enrich : Complète les synopsis manquants si nécessaire.
    - node_rag_synthesizer : Fusionne le contexte, génère la réponse textuelle finale
      et structure le top 5 des films pour le front-end.

Dépendances principales :
    - .state (AgentState)
    - .prompts (Gabarits d'instructions)
    - .tools (sql_tools, vector_tools, wiki_tools)
    - langchain_ollama (Instance locale du LLM)

Auteur/Responsable : Équipe Agents
"""
