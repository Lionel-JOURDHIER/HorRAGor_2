"""
models/films.py
────────────────
Table centrale. FK vers collections, realisateurs.
Relations 1-1 vers scores_tmdb, scores_imdb, scores_rt.
Relation N-N vers genres via film_genres.
"""

from sqlalchemy import (
    BigInteger,
    Column,
    Date,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from tables.base import Base


class Film(Base):
    """
    Main entity representing a movie.

    This table centralizes movie metadata, financial figures, and serves as
    the pivot for directors, collections, genres, and external ratings.
    """

    __tablename__ = "films"

    # --- Primary Key ---
    tmdb_id = Column(Integer, primary_key=True, autoincrement=False)

    # --- Foreign Keys ---
    # SET NULL on delete ensures we keep the film even if the director/collection is removed
    director_id = Column(
        Integer,
        ForeignKey("realisateurs.director_id", ondelete="SET NULL"),
        nullable=True,
    )
    id_collection = Column(
        Integer,
        ForeignKey("collections.tmdb_collection_id", ondelete="SET NULL"),
        nullable=True,
    )

    # --- Alternative Identifiers ---
    imdb_id = Column(String(10), unique=True, nullable=True)
    id_tertiaire = Column(String(255), unique=True, nullable=True)

    # --- Main Metadata ---
    title = Column(String(200), nullable=False)
    original_title = Column(String(200), nullable=True)
    original_language = Column(String(2), nullable=True)
    release_date = Column(Date, nullable=True)
    status = Column(String(15), nullable=True)
    runtime = Column(SmallInteger, nullable=True)
    overview = Column(Text, nullable=True)
    tagline = Column(String(260), nullable=True)
    poster_path = Column(String(100), nullable=True)

    # --- Financial Data ---
    # BigInteger is mandatory for global box office figures
    budget = Column(BigInteger, nullable=True)
    revenue = Column(BigInteger, nullable=True)

    # --- Relationships ---
    # Many-to-One
    realisateur = relationship("Realisateur", back_populates="films")
    collection = relationship("Collection", back_populates="films")

    # Many-to-Many through association table
    film_genres = relationship(
        "FilmGenre", back_populates="film", cascade="all, delete-orphan"
    )

    # One-to-One relationships (uselist=False)
    score_tmdb = relationship(
        "ScoreTmdb", back_populates="film", uselist=False, cascade="all, delete-orphan"
    )
    score_imdb = relationship(
        "ScoreImdb", back_populates="film", uselist=False, cascade="all, delete-orphan"
    )
    score_rt = relationship(
        "ScoreRt", back_populates="film", uselist=False, cascade="all, delete-orphan"
    )
