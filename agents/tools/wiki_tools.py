"""agents/tools/wiki_tools.py
Outil (Tool) de recherche documentaire et d'enrichissement via l'API Wikipédia.

Ce module définit l'outil mis à la disposition de l'agent LangGraph pour
effectuer des recherches externes sur l'encyclopédie Wikipédia. Il intervient
principalement lorsque les informations de la table locale (comme le synopsis)
sont absentes ou incomplètes, permettant ainsi d'enrichir le contexte du LLM
et d'alimenter l'endpoint '/wikipedia'.

Fonctionnalités principales :
    - Recommandation étendue : Recherche dynamique de pages Wikipédia basées sur le titre d'un film.
    - Parsing propre : Extraction et nettoyage textuel du résumé principal (synopsis)
      pour éviter d'injecter du code HTML ou des caractères parasites dans le prompt.

Dépendances principales :
    - langchain_core.tools (tool)
    - wikipedia (ou requests pour l'interrogation directe de l'API MediaWiki)

Auteur/Responsable : Équipe Agents
"""
