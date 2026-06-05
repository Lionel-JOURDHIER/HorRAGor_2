# database/tables/__init__.py
# Import centralisé de tous les modèles pour garantir que SQLAlchemy
# résout l'intégralité des relationships() au démarrage, dans le bon ordre.

from database.tables.base import Base
from database.tables.collections import Collection
from database.tables.film_genres import FilmGenre
from database.tables.films import Film  # après Collection et Realisateur
from database.tables.genres import Genre
from database.tables.realisateurs import Realisateur
from database.tables.scores_imdb import ScoreImdb
from database.tables.scores_rt import ScoreRt
from database.tables.scores_tmdb import ScoreTmdb

__all__ = [
    "Base",
    "Collection",
    "Realisateur",
    "Film",
    "Genre",
    "FilmGenre",
    "ScoreTmdb",
    "ScoreImdb",
    "ScoreRt",
]
