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
from typing import List, Optional

import faiss
import numpy as np
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


# Seuil empirique : en dessous, sous-index FAISS ; au dessus, post-filtre oversample
SMALL_POOL_THRESHOLD = 500


def _search_in_pool(
    query_vector: list,
    candidate_ids: List[int],
    top_k: int,
    exclude_id: Optional[int] = None,
) -> list[tuple[int, float]]:
    """
    Stratégie adaptive de recherche FAISS sur un pool restreint.

    - Pool petit (< SMALL_POOL_THRESHOLD) : sous-index FAISS temporaire.
      Recherche exacte et précise, coût O(n) acceptable sur petit volume.
    - Pool large (>= SMALL_POOL_THRESHOLD) : recherche globale + post-filtre.
      Evite la reconstruction coûteuse d'un index sur un grand volume.

    Args:
        query_vector: Vecteur de la requête (dim 1024).
        candidate_ids: Pool d'IDs tmdb pré-filtrés par SQL.
        top_k: Nombre de résultats attendus.
        exclude_id: tmdb_id à exclure du résultat (film source pour search_similar).

    Returns:
        Liste de tuples (tmdb_id, distance) triée par pertinence FAISS.
    """
    candidate_set = set(candidate_ids)
    if exclude_id:
        candidate_set.discard(exclude_id)

    if len(candidate_set) < SMALL_POOL_THRESHOLD:
        # --- Stratégie petit pool : sous-index temporaire ---
        sub_index = faiss.IndexFlatL2(faiss_global_service.dimension)
        sub_mapping = {}  # {local_faiss_id: tmdb_id}

        for local_id, tmdb_id in enumerate(candidate_set):
            vector = faiss_global_service.get_vector_by_id(tmdb_id)
            if vector:
                sub_index.add(np.array([vector], dtype="float32"))
                sub_mapping[local_id] = tmdb_id

        if sub_index.ntotal == 0:
            return []

        actual_k = min(top_k, sub_index.ntotal)
        D, I = sub_index.search(np.array([query_vector], dtype="float32"), actual_k)

        return [
            (sub_mapping[faiss_id], float(dist))
            for dist, faiss_id in zip(D[0], I[0])
            if faiss_id in sub_mapping
        ]

    else:
        # --- Stratégie grand pool : recherche globale + post-filtre ---
        oversample_k = min(top_k * 10, len(candidate_set))
        faiss_results = faiss_global_service.search(
            query_vector=query_vector, k=oversample_k
        )
        return [
            (tmdb_id, dist)
            for tmdb_id, dist in faiss_results
            if tmdb_id in candidate_set
        ][:top_k]


@tool
def search_vector_catalog(
    query: str,
    top_k: int = 5,
    candidate_ids: Optional[List[int]] = None,
) -> List[FilmShort]:
    """
    Recherche les films les plus pertinents sémantiquement.

    Si candidate_ids est fourni (issu de filter_films_by_criteria),
    la recherche FAISS est restreinte à ce pool via stratégie adaptive.
    Sinon, recherche sur le catalogue complet.
    """
    try:
        query_vector = OLLAMA_CLIENT_EMBEDD.embed_query(query)

        if candidate_ids:
            faiss_results = _search_in_pool(
                query_vector=query_vector,
                candidate_ids=candidate_ids,
                top_k=top_k,
            )
        else:
            faiss_results = faiss_global_service.search(
                query_vector=query_vector, k=top_k
            )

        if not faiss_results:
            return []

        ordered_ids = [int(res[0]) for res in faiss_results]
        distance_map = {int(res[0]): res[1] for res in faiss_results}

        with get_db() as session:
            films: List[FilmShort] = get_films_short_by_ids(session, ordered_ids)

        for film in films:
            film.similarity_score = _convert_distance_to_similarity_score(
                distance_map[film.tmdb_id]
            )

        return films

    except Exception as e:
        print(f"DEBUG: Erreur dans search_vector_catalog : {e}")
        return []


@tool
def search_similar_movies_by_id(
    movie_id: int,
    top_k: int = 5,
    candidate_ids: Optional[List[int]] = None,
) -> List[FilmShort]:
    """
    Recherche les films les plus similaires à un film donné via son ID TMDB.

    Si candidate_ids est fourni (issu de filter_films_by_criteria),
    la recherche FAISS est restreinte à ce pool via stratégie adaptive.
    Sinon, recherche sur le catalogue complet.
    """
    try:
        query_vector = faiss_global_service.get_vector_by_id(movie_id)
        if not query_vector:
            return []

        if candidate_ids:
            faiss_results = _search_in_pool(
                query_vector=query_vector,
                candidate_ids=candidate_ids,
                top_k=top_k,
                exclude_id=movie_id,
            )
        else:
            faiss_results = faiss_global_service.search(
                query_vector=query_vector, k=top_k + 1
            )
            faiss_results = [
                (tmdb_id, dist)
                for tmdb_id, dist in faiss_results
                if tmdb_id != movie_id
            ][:top_k]

        if not faiss_results:
            return []

        ordered_ids = [int(res[0]) for res in faiss_results]
        distance_map = {int(res[0]): res[1] for res in faiss_results}

        with get_db() as session:
            films: List[FilmShort] = get_films_short_by_ids(session, ordered_ids)

        for film in films:
            film.similarity_score = _convert_distance_to_similarity_score(
                distance_map[film.tmdb_id]
            )

        return films

    except Exception as e:
        print(f"DEBUG: Erreur dans search_similar_movies_by_id : {e}")
        return []


# --- BLOC DE TEST ET DE VERIFICATION DES SCORES ---
if __name__ == "__main__":
    from agents.tools.sql_tools import filter_films_by_criteria
    from database.connection import get_db

    print("==================================================")
    print("🚀 TEST VECTOR TOOLS — STRATÉGIE ADAPTIVE")
    print("==================================================")

    # Démarrage de l'index FAISS (seule fois)
    with get_db() as session:
        faiss_global_service.build_index(session)

    # Helper d'affichage des résultats
    def print_results(
        label: str,
        results: List[FilmShort],
        latence_ms: float,
        pool_size: Optional[int] = None,
    ):
        strategie = (
            "📦 Sous-index FAISS (petit pool)"
            if pool_size is not None and pool_size < SMALL_POOL_THRESHOLD
            else "🌐 Catalogue complet"
            if pool_size is None
            else "🔍 Post-filtre oversample (grand pool)"
        )
        print(f"\n{'─' * 50}")
        print(f"🧪 {label}")
        print(f"   Stratégie : {strategie}")
        if pool_size is not None:
            print(f"   Pool SQL   : {pool_size} films")
        if not results:
            print("   ⚠️  AUCUN RÉSULTAT")
        else:
            for res in results:
                print(
                    f"   🎬 [{res.tmdb_id}] {res.title} | Score similarité : {res.similarity_score}/100 | TMDB : {res.tmdb_score}"
                )
        print(f"   ⏱️  Latence : {latence_ms:.2f} ms")

    # ─────────────────────────────────────────────
    # SCÉNARIO 1 — Sans filtres (catalogue complet)
    # ─────────────────────────────────────────────
    print("\n\n📌 SCÉNARIO 1 — Sans filtres (catalogue complet)")
    query = "un film d'horreur avec une maison hantée"

    start = time.perf_counter()
    results = search_vector_catalog.func(query=query, top_k=5, candidate_ids=None)
    end = time.perf_counter()

    print_results(
        label=f'search_vector_catalog — "{query}"',
        results=results,
        latence_ms=(end - start) * 1000,
        pool_size=None,
    )

    # ─────────────────────────────────────────────
    # SCÉNARIO 2 — Petit pool : réalisateur précis
    # ─────────────────────────────────────────────
    print("\n\n📌 SCÉNARIO 2 — Petit pool < 500 (réalisateur précis)")
    query = "un film d'horreur dans un hotel'"

    candidate_ids = filter_films_by_criteria.func(realisateur="Kubrick")
    pool_size = len(candidate_ids) if candidate_ids else 0
    print(f"   Pool SQL récupéré : {pool_size} films")

    start = time.perf_counter()
    results = search_vector_catalog.func(
        query=query, top_k=5, candidate_ids=candidate_ids
    )
    end = time.perf_counter()

    print_results(
        label=f'search_vector_catalog — "{query}" | réalisateur=Kubrick',
        results=results,
        latence_ms=(end - start) * 1000,
        pool_size=pool_size,
    )

    # ─────────────────────────────────────────────
    # SCÉNARIO 3 — Grand pool : genre
    # ─────────────────────────────────────────────
    print("\n\n📌 SCÉNARIO 3 — Grand pool > 500 (genre)")
    query = "un film d'horreur avec un tueur masqué"

    candidate_ids = filter_films_by_criteria.func(genre="Thriller")
    pool_size = len(candidate_ids) if candidate_ids else 0
    print(f"   Pool SQL récupéré : {pool_size} films")

    start = time.perf_counter()
    results = search_vector_catalog.func(
        query=query, top_k=5, candidate_ids=candidate_ids
    )
    end = time.perf_counter()

    print_results(
        label=f'search_vector_catalog — "{query}" | genre=Thriller',
        results=results,
        latence_ms=(end - start) * 1000,
        pool_size=pool_size,
    )

    print("\n\n==================================================")
    print("✅ FIN DES TESTS")
    print("==================================================")
