"""api/main.py
Point d'entrée principal de l'API REST FastAPI pour le projet HorRAGor.

Ce module initialise l'application FastAPI, configure le cycle de vie (lifespan)
du serveur et expose les points d'accès (endpoints) HTTP consommés directement
par l'interface utilisateur.

Fonctionnalités principales :
    - Gestion du cycle de vie ('lifespan') : Déclenche le chargement initial en RAM
      de l'index FAISS et du cache de titres de Supabase au démarrage d'Uvicorn.
    - Gestion des Endpoints pour le Front : Centralisation et inclusion des routes
      REST de l'application (dialogue avec l'agent LangGraph, récupération des films).

Dépendances principales :
    - fastapi (FastAPI, Lifespan)
    - faiss.faiss_service (faiss_global_service)
    - .modules.routes (router)

Auteur/Responsable : Hanna (Epic 3)
"""

from fastapi import FastAPI

from routes import router

app = FastAPI(
    title="HorRAGor API",
    version="0.1.0"
)

app.include_router(router)