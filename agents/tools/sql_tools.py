"""agents/tools/sql_tools.py
Outil (Tool) de pré-filtrage SQL pour la recherche de films.

Ce module définit l'outil structuré utilisé par l'agent LangGraph pour réduire
le pool de films candidats via des filtres métier avant la recherche sémantique
FAISS. Le résultat (List[int]) est conçu pour être passé directement à
search_vector_catalog comme pool restreint.

Stratégie de pré-filtrage :
    - Tous les filtres sont optionnels et combinables librement.
    - Si aucun filtre n'est fourni, retourne None (signal pour l'agent
      de lancer FAISS sur le catalogue complet).
    - Si les filtres sont trop restrictifs (0 résultats), retourne None
      avec un warning pour que l'agent ignore les filtres et lance FAISS
      sur le catalogue complet.

Contrat de retour :
    - List[int] : Liste des tmdb_ids éligibles, passée à vector_tools.
    - None : Aucun filtre actif ou pool vide — FAISS tourne sans restriction.

Dépendances principales :
    - langchain_core.tools (tool)
    - sqlalchemy (select, and_, extract)
    - database.connection (db_session)
    - database.tables (Film, FilmGenre, Genre, Realisateur)

Auteur/Responsable : Lionel
"""

import sys
import time
from pathlib import Path
from typing import List, Optional

from langchain_core.tools import tool
from sqlalchemy import and_, exists, extract, select
from sqlalchemy.orm import Session

# Définit la racine du projet comme étant 2 dossiers au-dessus (agents/tools/ -> agents/ -> racine)
root_path = Path(__file__).resolve().parents[2]
if str(root_path) not in sys.path:  # pragma: no cover
    sys.path.insert(0, str(root_path))

from database.connection import db_session
from database.tables.collections import Collection  # noqa: F401
from database.tables.film_genres import FilmGenre
from database.tables.films import Film
from database.tables.genres import Genre
from database.tables.realisateurs import Realisateur


def _build_filtered_ids(
    session: Session,
    realisateur: Optional[str] = None,
    genres_included: Optional[List[str]] = None,
    genres_excluded: Optional[List[str]] = None,
    release_year_min: Optional[int] = None,
    release_year_max: Optional[int] = None,
    tmdb_score_min: Optional[float] = None,
    runtime_min: Optional[int] = None,
    runtime_max: Optional[int] = None,
) -> Optional[List[int]]:
    """
    Construit et exécute la requête SQL de pré-filtrage.

    Args:
        session:            Session SQLAlchemy active.
        realisateur:        Nom partiel du réalisateur (ILIKE). Optionnel.
        genres_included:    Liste de genres à inclure (AND entre chaque). Optionnel.
        genres_excluded:    Liste de genres à exclure. Optionnel.
        release_year_min:   Année de sortie minimale. Optionnel.
        release_year_max:   Année de sortie maximale. Optionnel.
        tmdb_score_min:     Score TMDB minimum (0-10). Optionnel.
        runtime_min:        Durée minimale en minutes. Optionnel.
        runtime_max:        Durée maximale en minutes. Optionnel.

    Returns:
        List[int] | None
    """
    filters_active = any(
        [
            realisateur,
            genres_included,
            genres_excluded,
            release_year_min,
            release_year_max,
            tmdb_score_min,
            runtime_min,
            runtime_max,
        ]
    )
    if not filters_active:
        return None

    statement = select(Film.tmdb_id).distinct()
    conditions = []

    # --- Réalisateur ---
    if realisateur:
        statement = statement.join(
            Realisateur, Film.director_id == Realisateur.director_id
        )
        conditions.append(Realisateur.name.ilike(f"%{realisateur}%"))

    # --- Genres inclus : OR sémantique via EXISTS ---
    # (un film correspond dès qu'il a AU MOINS UN des genres demandés)
    if genres_included:
        genres_included_subq = (
            select(FilmGenre.tmdb_id)
            .join(Genre, FilmGenre.id_genre == Genre.id_genre)
            .where(
                and_(
                    FilmGenre.tmdb_id == Film.tmdb_id,
                    Genre.genre_name.in_(genres_included),
                )
            )
        )
        conditions.append(exists(genres_included_subq))

    # --- Genres exclus : NOT EXISTS pour chaque genre à exclure ---
    if genres_excluded:
        for genre in genres_excluded:
            subq = (
                select(FilmGenre.tmdb_id)
                .join(Genre, FilmGenre.id_genre == Genre.id_genre)
                .where(
                    and_(
                        FilmGenre.tmdb_id == Film.tmdb_id,
                        Genre.genre_name == genre,
                    )
                )
            )
            conditions.append(~exists(subq))

    # --- Durée ---
    if runtime_min is not None:
        conditions.append(Film.runtime >= runtime_min)
    if runtime_max is not None:
        conditions.append(Film.runtime <= runtime_max)

    # --- Année de sortie ---
    if release_year_min is not None:
        conditions.append(extract("year", Film.release_date) >= release_year_min)
    if release_year_max is not None:
        conditions.append(extract("year", Film.release_date) <= release_year_max)

    # --- Score TMDB minimum ---
    if tmdb_score_min is not None:
        from database.tables.scores_tmdb import ScoreTmdb

        statement = statement.join(ScoreTmdb, Film.tmdb_id == ScoreTmdb.tmdb_id)
        conditions.append(ScoreTmdb.vote_average >= tmdb_score_min)

    if conditions:
        statement = statement.where(and_(*conditions))

    ids = list(session.execute(statement).scalars().all())

    if not ids:
        print("⚠️ Pool vide après filtrage — renvois d'une liste vide.")
        return []

    print(f"✅ Pré-filtrage SQL : {len(ids)} films éligibles.")
    return ids


@tool
def filter_films_by_criteria(
    realisateur: Optional[str] = None,
    genres_included: Optional[List[str]] = None,
    genres_excluded: Optional[List[str]] = None,
    release_year_min: Optional[int] = None,
    release_year_max: Optional[int] = None,
    tmdb_score_min: Optional[float] = None,
    runtime_min: Optional[int] = None,
    runtime_max: Optional[int] = None,
) -> Optional[List[int]]:
    """
    Pré-filtre le catalogue par critères métier et retourne les tmdb_ids éligibles.

    À utiliser AVANT search_vector_catalog pour restreindre le pool de recherche.
    Si aucun filtre n'est actif ou si le pool est vide, retourne None — l'agent
    doit alors lancer FAISS sur le catalogue complet.

    Args:
        realisateur:        Nom partiel du réalisateur (ex: "Kubrick"). Optionnel.
        genres_included:    Genres à inclure (ex: ["Horror", "Thriller"]). Optionnel.
        genres_excluded:    Genres à exclure (ex: ["Comedy"]). Optionnel.
        release_year_min:   Année de sortie minimale (ex: 1990). Optionnel.
        release_year_max:   Année de sortie maximale (ex: 2010). Optionnel.
        tmdb_score_min:     Score TMDB minimum (ex: 7.0). Optionnel.
        runtime_min:        Durée minimale en minutes. Optionnel.
        runtime_max:        Durée maximale en minutes. Optionnel.

    Returns:
        List[int] | None : tmdb_ids éligibles, ou None si pas de restriction.
    """
    with db_session() as session:
        return _build_filtered_ids(
            session=session,
            realisateur=realisateur,
            genres_included=genres_included,
            genres_excluded=genres_excluded,
            release_year_min=release_year_min,
            release_year_max=release_year_max,
            tmdb_score_min=tmdb_score_min,
            runtime_min=runtime_min,
            runtime_max=runtime_max,
        )


# --- BLOC DE TEST ---
if __name__ == "__main__":
    import time

    print("==================================================")
    print("🚀 TEST DU PRÉ-FILTRE SQL (filter_films_by_criteria)")
    print("==================================================")

    test_cases = [
        # (label, kwargs)
        ("Aucun filtre", {}),
        ("Genre inclus seul — Horror", {"genres_included": ["Horror"]}),
        (
            "Genres inclus multiples — Horror AND Thriller",
            {"genres_included": ["Horror", "Thriller"]},
        ),
        ("Genre exclus — sans Comedy", {"genres_excluded": ["Comedy"]}),
        (
            "Inclus + Exclus — Horror sans Comedy",
            {"genres_included": ["Horror"], "genres_excluded": ["Comedy"]},
        ),
        ("Réalisateur seul — Kubrick", {"realisateur": "Kubrick"}),
        ("Durée seule — 90 à 120 min", {"runtime_min": 90, "runtime_max": 120}),
        (
            "Année seule — 1990 à 2000",
            {"release_year_min": 1990, "release_year_max": 2000},
        ),
        ("Score TMDB minimum — 7.0", {"tmdb_score_min": 7.0}),
        (
            "Combinaison complète — Horror, 2000-2020, 90-130 min, score 6.0+",
            {
                "genres_included": ["Horror"],
                "genres_excluded": ["Comedy"],
                "release_year_min": 2000,
                "release_year_max": 2020,
                "runtime_min": 90,
                "runtime_max": 130,
                "tmdb_score_min": 6.0,
            },
        ),
        (
            "Filtres impossibles — Kubrick + Horror + après 2020",
            {
                "realisateur": "Kubrick",
                "genres_included": ["Horror"],
                "release_year_min": 2020,
            },
        ),
    ]

    for label, kwargs in test_cases:
        start = time.perf_counter()
        result = filter_films_by_criteria.func(**kwargs)
        end = time.perf_counter()

        count = len(result) if result else 0
        preview = result[:5] if result else "None (catalogue complet)"
        print(f"\n🧪 {label}")
        print(f"   IDs ({count}) : {preview}")
        print(f"   ⏱️  Latence : {(end - start) * 1000:.2f} ms")

    print("\n==================================================")
