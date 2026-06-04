"""agents/tools/vector_tools.py
Outil (Tool) de recherche sémantique vectorielle via l'index FAISS local.

Ce module définit l'outil structuré utilisé par l'agent LangGraph pour effectuer
des recherches de similarité sur le titre et le synopsis des films. Il permet à
l'agent de comprendre le contexte, les thèmes ou les requêtes implicites de
l'utilisateur (ex: "un film d'horreur avec un clown dans les égouts"), même si les
mots exacts ne figurent pas dans la base SQL.

Fonctionnalités principales :
    - Interface directe entre l'agent décisionnel et le service global FAISS (`faiss_global_service`).
    - Vectorisation à la volée de la requête de l'utilisateur via le modèle local Ollama.
    - Récupération et filtrage des k-plus-proches voisins (Top-K) pour extraire les films
      les plus pertinents sur le plan sémantique.

Dépendances principales :
    - langchain_core.tools (tool)
    - FAISS.faiss_service (faiss_global_service)

Auteur/Responsable : Équipe Agents / Lionel
"""
