"""agents/tools/sql_tools.py
Outil (Tool) de recherche et d'interrogation de la base de données SQL Supabase.

Ce module définit les outils structurés mis à la disposition de l'agent LangGraph
pour lui permettre d'exécuter des requêtes directes et ciblées sur la base de données
PostgreSQL. Il permet à l'agent de répondre de manière déterministe à des questions
factuelles nécessitant des filtres précis (ex: compter les films d'un réalisateur,
filtrer par année ou lister des statistiques).

Fonctionnalités principales :
    - Exécution de requêtes SQL sécurisées via SQLAlchemy en mode lecture seule.
    - Extraction de métadonnées précises pour alimenter le contexte du LLM (réalisateurs,
      durées, scores TMDB).
    - Formatage des résultats bruts de la base sous forme textuelle propre et assimilable
      directement par les nœuds de décision du graphe.

Dépendances principales :
    - langchain_core.tools (tool)
    - sqlalchemy (select, text)
    - FAISS.connection (SessionLocal)

Auteur/Responsable : Équipe Agents / Lionel
"""
