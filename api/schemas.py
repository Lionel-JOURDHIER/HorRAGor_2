"""api/schemas.py
Module de définition des schémas de données Pydantic pour l'API HorRAGor.

Ce fichier centralise les modèles de validation (Data Transfer Objects) utilisés
pour sécuriser, typer et documenter les entrées et les sorties de chaque endpoint
de l'API. Il garantit la conformité des échanges entre le front Streamlit et le back.

Modèles de validation inclus :
    - Réponse Film : Modèle sérialisant les détails d'un film pour `/film/{id}`.
    - Réponses Listes : Structures pour les listes de réalisateurs (`/list_réal`) et de genres (`/list_genre`).
    - Requête Chat : Validation du prompt textuel envoyé par l'utilisateur pour `/chat`.
    - Réponses Chat (Streaming/JSON) : Modèles pour suivre l'état d'avancement de la réflexion du LLM,
      le texte final généré, et la structure stricte du top 5 des films recommandés
      (contenant obligatoirement : Réalisateur, Année et Score TMDB).
    - Réponse Wikipédia : Format d'encapsulation du synopsis extrait pour `/wikipedia`.
    - ChatQueryParams / ChatPayload : Structure stricte pour recevoir la demande utilisateur.
      Contient le prompt textuel ET le dictionnaire des filtres du formulaire :
        * realisateur: Optional[str]
        * genres_incluts: List[str]
        * genres_excluts: List[str]
        * date_sortie_min / max: int (1900 à 2026)
        * score_tmdb_min: float (0 à 10)
        * duree_min / max: int (1 à 685)
Dépendances principales :
    - pydantic (BaseModel, Field)
    - typing (Optional, List, Dict)

Auteur/Responsable : Hanna (Epic 3)
"""

# IMPORT
from datetime import date
from typing import Any, List, Optional

from pydantic import BaseModel, Field


# CLASSES GENERAL -----------------------------------------------------------
class HealthResponse(BaseModel):
    """API health status response."""

    status: str = "ok"


class ErrorResponse(BaseModel):
    """Standard API error response model."""

    error: str
    details: Optional[str] = None


# CLASSES FILMS -----------------------------------------------------------


class DirectorsResponse(BaseModel):
    """List of available movie directors."""

    directors: List[str]


class GenresResponse(BaseModel):
    """List of available movie genres."""

    genres: List[str]


class FilmShort(BaseModel):
    """Compact movie representation used in recommendations and search results."""

    tmdb_id: int
    title: str
    release_date: Optional[date] = None
    genres: List[str] = Field(default_factory=list)
    tmdb_score: Optional[float] = None
    similarity_score: Optional[float] = None
    poster_url: Optional[str] = None


class FilmSearchResponse(BaseModel):
    """Movie search results."""

    results: List[FilmShort] = Field(default_factory=list)


class FilmDetail(BaseModel):
    """Detailed movie information returned by the movie endpoint."""

    tmdb_id: int
    title: str

    original_title: Optional[str] = None
    original_language: Optional[str] = None

    realisateur: Optional[str] = None
    release_date: Optional[date] = None
    runtime: Optional[int] = None
    status: Optional[str] = None
    synopsis: Optional[str] = None
    tagline: Optional[str] = None
    director: Optional[str] = None
    genres: List[str] = Field(default_factory=list)
    poster_url: Optional[str] = None
    backdrop_url: Optional[str] = None
    budget: Optional[int] = None
    revenue: Optional[int] = None

    tmdb_score: Optional[float] = None
    tmdb_vote_count: Optional[int] = None
    imdb_score: Optional[float] = None
    imdb_vote_count: Optional[int] = None
    rotten_tomatometer: Optional[int] = None
    rotten_audience_score: Optional[int] = None

    aggregated_score: Optional[float] = None

    collection: Optional[str] = None


# FILTERS -----------------------------------------------------------
class ChatFilters(BaseModel):
    """Optional filters applied to a movie search request."""

    realisateur: Optional[str] = None

    genres_included: List[str] = []
    genres_excluded: List[str] = []

    release_year_min: Optional[int] = Field(default=None, ge=1900, le=2026)
    release_year_max: Optional[int] = Field(default=None, ge=1900, le=2026)

    tmdb_score_min: Optional[float] = Field(default=None, ge=0, le=10)

    runtime_min: Optional[int] = Field(default=None, ge=1, le=685)
    runtime_max: Optional[int] = Field(default=None, ge=1, le=685)


# AGENT -----------------------------------------------------------------------
class AgentStep(BaseModel):
    """Execution step produced by the ReAct workflow."""

    step: str
    status: str


class AgentState(BaseModel):
    """Shared state exchanged between LangGraph nodes."""

    user_query: str

    # Filtres entrants du front-end à fusionner
    initial_filters: ChatFilters = Field(default_factory=ChatFilters)

    # Suivi de l'exécution
    current_step: Optional[str] = None
    steps: List[AgentStep] = Field(default_factory=list)

    # Données intermédiaires et filtres mergés
    sql_filters: ChatFilters = Field(default_factory=ChatFilters)
    candidate_ids: Optional[List[int]] = None

    # Données de sortie pour les réponses finales
    retrieved_movies: List[Any] = Field(
        default_factory=list
    )  # Contiendra FilmShort ou FilmDetail
    answer: Optional[str] = None


# CHAT REQUESTS RESPONSE --------------------------------------------------
class ChatRequest(BaseModel):
    """User query sent to the conversational agent."""

    message: str = Field(min_length=1, max_length=2000)
    filters: Optional[ChatFilters] = None


class ChatStatusResponse(BaseModel):
    """Current execution status of the conversational agent."""

    status: str
    steps: List[AgentStep] = Field(default_factory=list)


class ChatResponse(BaseModel):
    """Final response generated by the conversational agent."""

    answer: str
    steps: List[AgentStep] = Field(default_factory=list)
    recommendations: List[FilmShort] = Field(default_factory=list)


class WikipediaResponse(BaseModel):
    """Movie information retrieved from Wikipedia."""

    title: str
    synopsis: str
    source_url: Optional[str] = None
    source: str = "wikipedia"


class WikipediaRequest(BaseModel):
    """Wikipedia lookup request."""

    tmdb_id: int
