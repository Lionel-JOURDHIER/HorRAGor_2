"""api/routes.py
Module de définition des routes HTTP (endpoints) de l'API HorRAGor.

Ce fichier regroupe l'ensemble des points d'accès REST gérés par l'APIRouter de
FastAPI. Il fait l'interface entre les requêtes HTTP envoyées par le front-end
Streamlit et la logique métier (base de données Supabase, agent LangGraph
et outils de recherche).

Endpoints exposés :
    - GET /health : Vérification de la santé de l'API et de la disponibilité du système.
    - GET /film/{id} : Récupère les informations complètes d'un film de la base de données via son ID.
    - GET /list_real : Récupère la liste complète de tous les réalisateurs disponibles.
    - GET /list_genre : Récupère la liste complète de tous les genres cinématographiques.
    - POST /chat : Point d'entrée de la requête utilisateur. Gère le streaming asynchrone
                  pour renvoyer l'état d'avancement de la réflexion, le texte final du LLM,
                  et le JSON des 5 films recommandés (Réalisateur, Année, score TMDB).
    - GET /wikipedia : Récupère le synopsis et les informations complémentaires directement sur Wikipédia.

Dépendances principales :
    - fastapi (APIRouter, Depends, HTTPException)
    - agents.graph (workflow / graphe de l'agent)
    - .schemas (Modèles Pydantic de validation pour chaque endpoint)

Auteur/Responsable : Hanna (Epic 3)
"""
