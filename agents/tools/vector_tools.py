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

import sys
from pathlib import Path
from typing import List

from langchain_core.tools import tool

# --- CONFIGURATION DES CHEMINS (KISS & DRY) ---
root_path = Path(__file__).resolve().parents[2]

if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

# Imports relatifs à la racine du projet
from database.connection import SessionLocal
from database.faiss_service import faiss_global_service
from database.populate import OLLAMA_CLIENT_EMBEDD


@tool
def search_vector_catalog(query: str, top_k: int = 5) -> List[int]:
    """
    Recherche des films dans le catalogue en utilisant une similarité sémantique (vecteurs).
    """
    try:
        # 1. Vectorisation locale de la requête à la volée
        query_vector = OLLAMA_CLIENT_EMBEDD.embed_query(query)

        # 2. Recherche directe dans l'index global déjà chargé en RAM au démarrage
        tmdb_ids = faiss_global_service.search(query_vector=query_vector, k=top_k)

        return tmdb_ids if tmdb_ids else []

    except Exception:
        # Résilience de l'agent : évite de bloquer le graphe en cas de timeout Ollama
        return []


if __name__ == "__main__":
    print("🚀 Démarrage du test autonome de l'outil vector_tools...")

    try:
        # 1. Ouverture d'une session de base de données éphémère
        with SessionLocal() as session:
            print(
                "🔄 Chargement et construction de l'index FAISS global depuis Supabase (RAM)..."
            )
            faiss_global_service.build_index(session)

        # 2. Vérification que l'index a bien été alimenté
        if faiss_global_service.index.ntotal > 0:
            query_test = "un film de science-fiction avec des robots et de l'intelligence artificielle"
            print(f"\n🔍 Envoi de la requête sémantique : '{query_test}'")

            # 3. Appel de ton outil LangGraph structuré
            # Note : On utilise .invoke() car c'est un outil décoré avec @tool
            matching_ids = search_vector_catalog.invoke(
                {"query": query_test, "top_k": 3}
            )

            print("✅ Outil exécuté avec succès !")
            print(f"🎬 IDs TMDB les plus pertinents trouvés : {matching_ids}")
        else:
            print(
                "⚠️ L'index FAISS est vide. Vérifie le contenu de ta table FilmEmbedding."
            )

    except Exception as e:
        print(f"❌ Une erreur est survenue lors du test : {e}")
