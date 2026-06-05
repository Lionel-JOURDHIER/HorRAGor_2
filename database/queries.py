"""database/queries.py
Module d'extraction de données complexes et de mapping ORM via SQLAlchemy 2.0.

Ce fichier centralise les requêtes de lecture de la base de données Supabase.
Il implémente une fonction de jointure multi-tables basée sur le Modèle Physique
des Données (MPD) Merise afin de consolider l'ensemble des attributs requis par
la couche d'interface de l'API.

Fonctionnalités principales :
    - Extraction unifiée d'un film et de ses métadonnées riches via jointures
      externes (Score TMDB, Score IMDb, Score Rotten Tomatoes, Réalisateur, Collection).
    - Résolution de la relation de type "plusieurs-à-plusieurs" (Many-to-Many)
      entre la table 'FILMS' et 'GENRES' à travers la table pivot 'FILMGENRE'.
    - Calcul dynamique d'un score critique agrégé et normalisé sur une base 100.
    - Mapping automatique et validation de type stricte vers le schéma Pydantic
      'FilmDetail' utilisé par les endpoints de l'API.

Dépendances principales :
    - sqlalchemy (select)
    - sqlalchemy.orm (Session)
    - tables (Fichiers de modèles modulaires éclatés par entité)
    - api.schemas (FilmDetail)

Auteur/Responsable : Lionel (Epic 1 & 2)
"""

import sys
from pathlib import Path
from typing import Optional

from connection import get_db
from sqlalchemy import select
from sqlalchemy.orm import Session

# --- CONFIGURATION DES CHEMINS (KISS & DRY) ---
database_path = Path(__file__).resolve().parent
root_path = database_path.parent

if str(root_path) not in sys.path:
    sys.path.append(str(root_path))

# --- IMPORTS DE TES MODULES (API & TABLES) ---
from tables.collections import Collection
from tables.film_genres import FilmGenre
from tables.films import Film
from tables.genres import Genre
from tables.realisateurs import Realisateur
from tables.scores_imdb import ScoreImdb
from tables.scores_rt import ScoreRt
from tables.scores_tmdb import ScoreTmdb

from api.schemas import FilmDetail


def get_film_details_by_id(session: Session, tmdb_id: int) -> Optional[FilmDetail]:
    """
    Récupère l'ensemble des détails d'un film en joignant les tables du MPD
    via SQLAlchemy pur et mappe le résultat vers le schéma Pydantic FilmDetail.
    """

    # 1. Construction du select avec toutes les jointures externes de ton MPD
    statement = (
        select(Film, ScoreTmdb, ScoreImdb, ScoreRt, Realisateur, Collection)
        .outerjoin(ScoreTmdb, Film.tmdb_id == ScoreTmdb.tmdb_id)
        .outerjoin(ScoreImdb, Film.imdb_id == ScoreImdb.tconst)
        .outerjoin(ScoreRt, Film.id_tertiaire == ScoreRt.id_tertiaire)
        .outerjoin(Realisateur, Film.director_id == Realisateur.director_id)
        .outerjoin(Collection, Film.id_collection == Collection.tmdb_collection_id)
        .where(Film.tmdb_id == tmdb_id)
    )

    # Exécution native SQLAlchemy (renvoie un tuple des objets ou None)
    result = session.execute(statement).first()
    if not result:
        return None

    film, s_tmdb, s_imdb, s_rt, real, coll = result

    # 2. Récupération des genres associés via la table pivot FilmGenre
    genres_stmt = (
        select(Genre.genre_name)
        .join(FilmGenre, Genre.id_genre == FilmGenre.id_genre)
        .where(FilmGenre.tmdb_id == tmdb_id)
    )
    # .scalars().all() extrait directement les chaînes de caractères de la base
    genres_list = list(session.execute(genres_stmt).scalars().all())

    # 3. Calcul du score agrégé (normalisé sur 100)
    scores = []
    if s_tmdb and s_tmdb.vote_average:
        scores.append(float(s_tmdb.vote_average) * 10)
    if s_imdb and s_imdb.average_rating:
        scores.append(float(s_imdb.average_rating) * 10)
    if s_rt and s_rt.rt_tomatometer:
        scores.append(float(s_rt.rt_tomatometer))

    aggregated = sum(scores) / len(scores) if scores else None

    # 4. Instanciation du schéma Pydantic de l'API
    return FilmDetail(
        tmdb_id=film.tmdb_id,
        title=film.title,
        original_title=film.original_title,
        original_language=film.original_language,
        realisateur=real.name if real else None,
        release_date=film.release_date,
        runtime=film.runtime,
        status=film.status,
        synopsis=film.overview,  # 'overview' en base -> 'synopsis' dans l'API
        tagline=film.tagline,
        director=real.name if real else None,
        genres=genres_list,
        poster_url=f"{film.poster_path}" if film.poster_path else None,
        budget=film.budget,
        revenue=film.revenue,
        tmdb_score=float(s_tmdb.vote_average)
        if s_tmdb and s_tmdb.vote_average
        else None,
        tmdb_vote_count=s_tmdb.vote_count if s_tmdb else None,
        imdb_score=float(s_imdb.average_rating)
        if s_imdb and s_imdb.average_rating
        else None,
        imdb_vote_count=s_imdb.num_votes if s_imdb else None,
        rotten_tomatometer=s_rt.rt_tomatometer if s_rt else None,
        rotten_audience_score=s_rt.rt_audience_score if s_rt else None,
        aggregated_score=aggregated,
        collection=coll.collection_name if coll else None,
    )


# --- Zone de Test Multi-Tables ---
if __name__ == "__main__":
    db_gen = get_db()
    session = next(db_gen)

    # ID extrait de ton log précédent pour tester en direct
    test_id = 898555

    try:
        print(
            f"🚀 Test d'extraction Merise complet (SQLAlchemy Pur) pour l'ID: {test_id}..."
        )
        details = get_film_details_by_id(session, test_id)

        if details:
            print(f"✅ Jointure et validation Pydantic réussies pour : {details.title}")
            print(details.model_dump_json(indent=2))
        else:
            print(f"⚠️ Film {test_id} introuvable dans Supabase.")

    except Exception as e:
        print(f"❌ Erreur lors du test d'extraction : {e}")
    finally:
        session.close()
