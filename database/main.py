"""
database/main.py

Point d'entrée de l'API Database HorRAGor.

Cette API expose uniquement les accès aux données :
- films
- genres
- réalisateurs
- health check

Aucune logique IA :
- pas de LangGraph
- pas de LLM
- pas de FAISS
- pas de génération
"""

from fastapi import FastAPI

from database.routes_db import router

from logger import get_logger, setup_logger


setup_logger()

logger = get_logger("DATABASE_API")


app = FastAPI(
    title="HorRAGor Database API",
    version="0.1.0",
    description="""
API dédiée uniquement à l'accès aux données HorRAGor.

Responsabilités:
- lecture PostgreSQL/Supabase
- récupération des films
- récupération des métadonnées
- validation des réponses
"""
)


app.include_router(
    router,
    prefix="/db",
)


@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Database API started")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("🛑 Database API stopped")