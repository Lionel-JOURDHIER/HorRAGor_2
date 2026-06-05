"""
models/film_genres.py
──────────────────────
Table d'association FILMS ↔ GENRES (relation N-N).
PK surrogate id_film_genre (INT AUTO_INCREMENT).
"""

from sqlalchemy import Column, ForeignKey, Integer, SmallInteger
from sqlalchemy.orm import relationship
from tables.base import Base


class FilmGenre(Base):
    """
    Association table linking Films and Genres (Many-to-Many).

    This model acts as a bridge between the 'films' and 'genres' tables,
    enforcing referential integrity through foreign keys and cascades.
    """

    __tablename__ = "film_genres"

    # Primary key
    id_film_genre = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign key to Film
    tmdb_id = Column(Integer, ForeignKey("films.tmdb_id", ondelete="CASCADE"))

    # Foreign key to Genre
    id_genre = Column(
        SmallInteger,
        ForeignKey("genres.id_genre", ondelete="CASCADE"),
        index=True,
    )

    # Simplified relationship mapping
    film = relationship("Film", back_populates="film_genres")
    genre = relationship("Genre", back_populates="film_genres")
