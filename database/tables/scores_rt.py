"""
models/scores_imdb.py
───────────────────────
PK : director_id (INT) — identifiant natif TMDB, pas d'AUTO_INCREMENT.
"""

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from tables.base import Base


class ScoreRt(Base):
    """
    Represents Rotten Tomatoes scores and consensus for a specific film.

    This model stores professional critic ratings (tomatometer) and
    audience scores, linked to a film via a tertiary identifier.

    Attributes:
        id_score_rt (int): Primary key, auto-incremented.
        id_tertiaire (str): Unique foreign key linking to the Film table.
        url_rotten (str): Unique URL of the film's Rotten Tomatoes page.
        rt_tomatometer (int): Percentage score from professional critics (0-100).
        rt_audience_score (int): Percentage score from the general audience (0-100).
        rt_critics_consensus (str): Summary text of professional critical opinion.
        film (Film): Relationship object back to the associated Film model.
    """

    __tablename__ = "score_rt"

    # Auto-incremented primary key
    id_score_rt = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign key to Film table
    # nullable=False: An RT score must be linked to an existing film
    # unique=True: Ensures a strict 1:1 relationship
    id_tertiaire = Column(
        String(200), ForeignKey("films.id_tertiaire"), nullable=False, unique=True
    )

    # url_rotten (Unique Key): Prevents duplicate RT URL entries
    url_rotten = Column(String(120), unique=True, nullable=True)

    # SmallInteger is sufficient for scores ranging from 0 to 100
    rt_tomatometer = Column(Integer)
    rt_audience_score = Column(Integer)

    # Critics consensus (VARCHAR 285 based on technical specs)
    rt_critics_consensus = Column(String(285))

    # Inverse relationship to the Film model
    film = relationship("Film", back_populates="score_rt")
