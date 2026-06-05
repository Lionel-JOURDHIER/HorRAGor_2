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

import math
import sys
import time
from pathlib import Path
from typing import List

from langchain_core.tools import tool

# --- CONFIGURATION DES CHEMINS (KISS & DRY) ---
root_path = Path(__file__).resolve().parents[2]

if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

# Imports relatifs à la racine du projet
from api.schemas import FilmShort
from database.connection import get_db
from database.faiss_service import faiss_global_service
from database.populate import OLLAMA_CLIENT_EMBEDD
from database.queries import get_films_short_by_ids


def _convert_distance_to_similarity_score(distance: float) -> int:
    """
    Convertit la distance L2 de FAISS en un score de similarité sur 100.
    Distance 0.0 -> Score 100
    """
    # Utilisation de l'exponentielle négative pour une décroissance fluide
    similarity = math.exp(-distance) * 100

    # Sécurité pour rester dans les bornes [0, 100] et conversion en entier
    return max(0, min(100, round(similarity)))


@tool
def search_vector_catalog(query: str, top_k: int = 5) -> List[FilmShort]:
    """Recherche les films les plus pertinents sémantiquement et renvoie leurs détails complets."""
    try:
        # 1. Embed + recherche FAISS → [(tmdb_id, distance), ...]
        query_vector = OLLAMA_CLIENT_EMBEDD.embed_query(query)
        faiss_results = faiss_global_service.search(query_vector=query_vector, k=top_k)

        if not faiss_results:
            return []

        # 2. On extrait les IDs dans l'ordre de pertinence FAISS
        ordered_ids = [int(res[0]) for res in faiss_results]
        distance_map = {int(res[0]): res[1] for res in faiss_results}

        # 3. Hydratation SQL correcte via la query existante (genres + score TMDB, sans N+1)
        session = next(get_db())
        try:
            films: List[FilmShort] = get_films_short_by_ids(session, ordered_ids)
        finally:
            session.close()

        # 4. On injecte le similarity_score (responsabilité du tool, pas de la query)
        for film in films:
            film.similarity_score = _convert_distance_to_similarity_score(
                distance_map[film.tmdb_id]
            )

        return films  # Déjà ordonné par get_films_short_by_ids selon ordered_ids

    except Exception as e:
        print(f"DEBUG: Erreur dans search_vector_catalog : {e}")
        return []


@tool
def search_similar_movies_by_id(movie_id: int, top_k: int = 5) -> List[FilmShort]:
    """Recherche les films les plus similaires à un film donné via son ID TMDB."""
    try:
        # 1. Récupération du vecteur de référence depuis l'index FAISS en RAM
        query_vector = faiss_global_service.get_vector_by_id(movie_id)
        if not query_vector:
            return []

        # 2. Recherche vectorielle (k+1 pour pouvoir exclure le film source)
        faiss_results = faiss_global_service.search(
            query_vector=query_vector, k=top_k + 1
        )

        # 3. Filtrage du film source + troncature au top_k
        filtered = [
            (tmdb_id, dist) for tmdb_id, dist in faiss_results if tmdb_id != movie_id
        ][:top_k]

        if not filtered:
            return []

        # 4. Hydratation SQL correcte via la query existante
        ordered_ids = [int(res[0]) for res in filtered]
        distance_map = {int(res[0]): res[1] for res in filtered}

        session = next(get_db())
        try:
            films: List[FilmShort] = get_films_short_by_ids(session, ordered_ids)
        finally:
            session.close()

        # 5. Injection du similarity_score
        for film in films:
            film.similarity_score = _convert_distance_to_similarity_score(
                distance_map[film.tmdb_id]
            )

        return films  # Déjà ordonné par get_films_short_by_ids selon ordered_ids

    except Exception as e:
        print(f"DEBUG: Erreur dans search_similar_movies_by_id : {e}")
        return []


# --- BLOC DE TEST ET DE VERIFICATION DES SCORES ---
if __name__ == "__main__":
    from database.connection import get_db

    print("==================================================")
    print("🚀 TEST DES OUTILS AVEC HYDRATATION (FilmShort)")
    print("==================================================")

    # Démarrage de l'index (seule fois) — session propre via get_db()
    session = next(get_db())
    try:
        faiss_global_service.build_index(session)
    finally:
        session.close()

    print("\n⚡ REQUÊTES RUNTIME (Hydratation SQL incluse)")
    print("--------------------------------------------------")

    # --- TEST 1 : Recherche textuelle ---
    queries = [
        "un thriller psychologique avec un twist final",
        "une comédie romantique dans les années 90",
    ]

    results = []
    for i, q in enumerate(queries, 1):
        start = time.perf_counter()
        results = search_vector_catalog.invoke({"query": q, "top_k": 5})
        end = time.perf_counter()

        print(f"\n💬 Test Texte {i}: '{q}'")
        print(f"   DEBUG type: {type(results)} | valeur brute: {results}")
        if not results:
            print("   ⚠️ AUCUN RÉSULTAT RETOURNÉ PAR L'OUTIL")
        else:
            for res in results:
                print(f"   -> {res.title} | Score: {res.similarity_score}/100")
        print(f"   ⏱️ Latence totale : {(end - start) * 1000:.2f} ms")

    # --- TEST 2 : Recherche similaire par ID ---
    if results:
        target_id = results[0].tmdb_id
        print(
            f"\n🆔 Test ID : Recherche similaire pour le film '{results[0].title}' (ID: {target_id})"
        )

        sim_ids = [target_id, results[1].tmdb_id] if len(results) > 1 else [target_id]

        for sim_id in sim_ids:
            start = time.perf_counter()
            similar = search_similar_movies_by_id.invoke(
                {"movie_id": sim_id, "top_k": 5}
            )
            end = time.perf_counter()

            print(f"\n   -> Similaires à {sim_id}:")
            print(f"      DEBUG type: {type(similar)} | valeur brute: {similar}")
            if not similar:
                print("      ⚠️ AUCUN RÉSULTAT")
            else:
                for item in similar:
                    print(f"      🔹 {item.title} | Score: {item.similarity_score}/100")
            print(f"      ⏱️ Latence : {(end - start) * 1000:.2f} ms")

    print("\n==================================================")
