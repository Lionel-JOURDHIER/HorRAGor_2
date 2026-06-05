"""
models/genres.py
─────────────────
PK : id_genre (SMALLINT, AUTO_INCREMENT)
Note : le CSV genres.csv ne contient pas id_genre — il sera généré
       automatiquement à l'ingestion (range 1-19, cohérent avec film_genres.csv).
"""

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from tables.base import Base


class Genre(Base):
    """
    Lookup table for movie genres.

    Stores unique genre names with optimized storage using SmallInteger.
    Maintains a many-to-many relationship with films through FilmGenre.
    """

    __tablename__ = "genres"

    # Primary key
    id_genre = Column(Integer, primary_key=True, autoincrement=True)

    # Genre name restricted to 50 characters, must be unique
    genre_name = Column(String(50), nullable=False, unique=True)

    # Inverse relationship to the association table
    # Using string reference "FilmGenre" to avoid import issues
    film_genres = relationship("FilmGenre", back_populates="genre")
