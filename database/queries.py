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
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.connection import get_db

# --- CONFIGURATION DES CHEMINS (KISS & DRY) ---
database_path = Path(__file__).resolve().parent
root_path = database_path.parent

if str(root_path) not in sys.path:
    sys.path.append(str(root_path))  # pragma: no cover

from api.schemas import DirectorsResponse, FilmDetail, FilmShort, GenresResponse
from database.tables.collections import Collection
from database.tables.film_genres import FilmGenre
from database.tables.films import Film
from database.tables.genres import Genre
from database.tables.realisateurs import Realisateur
from database.tables.scores_imdb import ScoreImdb
from database.tables.scores_rt import ScoreRt
from database.tables.scores_tmdb import ScoreTmdb


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


def get_all_directors(session: Session) -> DirectorsResponse:
    """
    Récupère la liste unique de tous les réalisateurs disponibles en base,
    triée par ordre alphabétique.
    """
    statement = (
        select(Realisateur.name)
        .where(Realisateur.name != None)
        .distinct()
        .order_by(Realisateur.name)
    )
    directors_list = list(session.execute(statement).scalars().all())

    return DirectorsResponse(directors=directors_list)


def get_all_genres(session: Session) -> GenresResponse:
    """
    Récupère la liste unique de tous les genres de films disponibles en base,
    triée par ordre alphabétique.
    """
    statement = (
        select(Genre.genre_name)
        .where(Genre.genre_name != None)
        .distinct()
        .order_by(Genre.genre_name)
    )
    genres_list = list(session.execute(statement).scalars().all())

    return GenresResponse(genres=genres_list)


def get_films_short_by_ids(session: Session, tmdb_ids: List[int]) -> List[FilmShort]:
    """
    Récupère les informations compactes (FilmShort) pour une liste d'identifiants TMDB.
    Utile pour afficher rapidement les résultats d'une recherche vectorielle FAISS.
    """
    if not tmdb_ids:
        return []

    # 1. Requête principale pour récupérer les films et leurs scores TMDB
    statement = (
        select(Film, ScoreTmdb)
        .outerjoin(ScoreTmdb, Film.tmdb_id == ScoreTmdb.tmdb_id)
        .where(Film.tmdb_id.in_(tmdb_ids))
    )

    records = session.execute(statement).all()
    if not records:
        return []

    # 2. Récupération groupée de tous les genres pour ces films (évite le N+1 query)
    genres_statement = (
        select(FilmGenre.tmdb_id, Genre.genre_name)
        .join(Genre, FilmGenre.id_genre == Genre.id_genre)
        .where(FilmGenre.tmdb_id.in_(tmdb_ids))
    )
    genres_records = session.execute(genres_statement).all()

    # Cartographie des genres par ID de film : {tmdb_id: [genre1, genre2, ...]}
    genres_by_film = {}
    for t_id, g_name in genres_records:
        genres_by_film.setdefault(t_id, []).append(g_name)

    # 3. Construction de la liste finale triée selon l'ordre initial des IDs demandés (pertinence FAISS)
    films_map = {}
    for film, score_tmdb in records:
        films_map[film.tmdb_id] = FilmShort(
            tmdb_id=film.tmdb_id,
            title=film.title,
            release_date=film.release_date,
            genres=genres_by_film.get(film.tmdb_id, []),
            tmdb_score=float(score_tmdb.vote_average)
            if score_tmdb and score_tmdb.vote_average
            else None,
            poster_url=f"{film.poster_path}" if film.poster_path else None,
            synopsis=film.overview,
        )

    # On réordonne pour respecter scrupuleusement le classement de FAISS
    return [films_map[t_id] for t_id in tmdb_ids if t_id in films_map]


# --- Zone de Test Multi-Tables ---
if __name__ == "__main__":
    db_gen = get_db()
    session = next(db_gen)

    test_id = 898555

    try:
        print(
            f"🚀 1. Test de get_film_details_by_id() (Détails complets) pour l'ID: {test_id}..."
        )
        details = get_film_details_by_id(session, test_id)
        if details:
            print(f"✅ Film détaillé trouvé : {details.title}")
            print(details.model_dump_json(indent=2))
        else:
            print(f"⚠️ Film détaillé {test_id} introuvable.")

        print("\n📁 2. Test de get_all_genres() (Liste globale)...")
        genres_resp = get_all_genres(session)
        print(
            f"✅ {len(genres_resp.genres)} genres récupérés. Exemple : {genres_resp.genres[:3]}"
        )

        print("\n🎬 3. Test de get_all_directors() (Liste globale)...")
        directors_resp = get_all_directors(session)
        print(
            f"✅ {len(directors_resp.directors)} réalisateurs récupérés. Exemple : {directors_resp.directors[:3]}"
        )

        print(
            f"\n📇 4. Test de get_films_short_by_ids() (Format Court / Retour FAISS) pour l'ID: {test_id}..."
        )
        shorts = get_films_short_by_ids(session, [test_id])
        if shorts:
            print("✅ Film court structuré avec succès :")
            print(shorts[0].model_dump_json(indent=2))
        else:
            print(f"⚠️ Aucun film court retourné pour l'ID {test_id}.")

    except Exception as e:
        print(f"❌ Erreur générale lors des tests d'extraction : {e}")
    finally:
        session.close()
