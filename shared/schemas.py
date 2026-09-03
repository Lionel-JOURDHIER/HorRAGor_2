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
from typing import Annotated, Any

from pydantic import BaseModel, Field, field_validator


# CLASSES GENERAL -----------------------------------------------------------
class HealthResponse(BaseModel):
    """API health status response."""

    status: str = "ok"


class ErrorResponse(BaseModel):
    """Standard API error response model."""

    error: str
    details: str | None = None


# CLASSES FILMS -----------------------------------------------------------


class DirectorsResponse(BaseModel):
    """List of available movie directors."""

    directors: list[str]


class GenresResponse(BaseModel):
    """List of available movie genres."""

    genres: list[str]


class FilmShort(BaseModel):
    """Compact movie representation used in recommendations and search results."""

    tmdb_id: int
    title: str
    release_date: date | None = None
    genres: list[str] = Field(default_factory=list)
    tmdb_score: float | None = None
    similarity_score: float | None = None
    poster_url: str | None = None
    synopsis: str | None = None
    judge_feedback: str | None = None


class FilmSearchResponse(BaseModel):
    """Movie search results."""

    results: list[FilmShort] = Field(default_factory=list)


class FilmDetail(BaseModel):
    """Detailed movie information returned by the movie endpoint."""

    tmdb_id: int
    title: str

    original_title: str | None = None
    original_language: str | None = None

    realisateur: str | None = None
    release_date: date | None = None
    runtime: int | None = None
    status: str | None = None
    synopsis: str | None = None
    tagline: str | None = None
    director: str | None = None
    genres: list[str] = Field(default_factory=list)
    poster_url: str | None = None
    backdrop_url: str | None = None
    budget: int | None = None
    revenue: int | None = None

    tmdb_score: float | None = None
    tmdb_vote_count: int | None = None
    imdb_score: float | None = None
    imdb_vote_count: int | None = None
    rotten_tomatometer: int | None = None
    rotten_audience_score: int | None = None

    aggregated_score: float | None = None

    collection: str | None = None
    judge_feedback: str | None = None


class FilmFilterRequest(BaseModel):
    tmdb_id: int | None = None
    realisateur: str | None = None

    genres_included: list[str] | None = None
    genres_excluded: list[str] | None = None

    release_year_min: int | None = None
    release_year_max: int | None = None

    tmdb_score_min: float | None = None

    runtime_min: int | None = None
    runtime_max: int | None = None


class FilmIdsRequest(BaseModel):
    tmdb_ids: list[int]


# FILTERS -----------------------------------------------------------
class ChatFilters(BaseModel):
    """Optional filters applied to a movie search request."""

    realisateur: str | None = None

    genres_included: list[str] = []
    genres_excluded: list[str] = []

    release_year_min: int | None = Field(default=None, ge=1900, le=2026)
    release_year_max: int | None = Field(default=None, ge=1900, le=2026)

    tmdb_score_min: float | None = Field(default=None, ge=0, le=10)

    runtime_min: int | None = Field(default=None, ge=1, le=685)
    runtime_max: int | None = Field(default=None, ge=1, le=685)

    @field_validator("realisateur", mode="before")
    @classmethod
    def clean_realisateur(cls, v):
        if isinstance(v, str) and v.strip().lower() in {
            "string",
            "",
            "null",
            "none",
            "n/a",
        }:
            return None
        return v


# AGENT -----------------------------------------------------------------------
class AgentStep(BaseModel):
    """Execution step produced by the ReAct workflow."""

    step: str
    status: str


def keep_or_update_list(
    current: list[int] | None, update: list[int] | None
) -> list[int] | None:
    """
    Reducer LangGraph : Conserve l'ancienne liste si la mise à jour est vide ou None,
    sinon remplace par la nouvelle liste d'IDs.
    """
    # Si le nœud actuel ne renvoie rien ou une liste vide, on garde la mémoire du tour précédent
    if update is None or (isinstance(update, list) and len(update) == 0):
        return current if current is not None else []
    # Sinon, un nœud a décidé d'écraser la mémoire avec de nouveaux films affichés
    return update


class AgentState(BaseModel):
    """Shared state exchanged between LangGraph nodes."""

    user_query: str

    # Filtres entrants du front-end à fusionner
    initial_filters: ChatFilters = Field(default_factory=ChatFilters)

    # Suivi de l'exécution
    current_step: str | None = None
    steps: list[AgentStep] = Field(default_factory=list)

    # Données intermédiaires et filtres mergés
    sql_filters: ChatFilters = Field(default_factory=ChatFilters)
    candidate_ids: list[int] | None = None

    # Données de sortie pour les réponses finales
    retrieved_movies: list[Any] = Field(
        default_factory=list
    )  # Contiendra FilmShort ou FilmDetail
    answer: str | None = None
    search_branch: str | None = None
    retry_count: int = 0
    last_displayed_movies_id: Annotated[list[int] | None, keep_or_update_list] = Field(
        default_factory=list
    )
    intent: str | None = None
    branch_search_wiki: str = Field(
        default="RAG"
    )  # posé par search_vector_node / load_film_node
    enrich_ids: list[int] = Field(default_factory=list)  # posé par verif_film_node
    data_enrich: dict[int, Any] = Field(
        default_factory=dict
    )  # posé par wikipedia_search_node
    data_enriched: str | None = None
    judge_feedback: str | None = None


# CHAT REQUESTS RESPONSE --------------------------------------------------
class ChatRequest(BaseModel):
    """User query sent to the conversational agent."""

    message: str = Field(min_length=1, max_length=2000)
    filters: ChatFilters | None = None
    session_id: str | None = Field(
        default=None,
        description="L'identifiant unique de la session/conversation pour maintenir la mémoire (géré par le client)",
        examples=["c9b4e1a2-8b45-4cde-a012-3456789abcdef"],
    )


class ChatStatusResponse(BaseModel):
    """Current execution status of the conversational agent."""

    status: str
    steps: list[AgentStep] = Field(default_factory=list)


class ChatResponse(BaseModel):
    """Final response generated by the conversational agent."""

    answer: str
    steps: list[AgentStep] = Field(default_factory=list)
    recommendations: list[FilmShort] = Field(default_factory=list)
    film: FilmDetail | None = None


class WikipediaResponse(BaseModel):
    """Movie information retrieved from Wikipedia."""

    title: str
    synopsis: str
    source_url: str | None = None
    source: str = "wikipedia"


class WikipediaRequest(BaseModel):
    """Wikipedia lookup request."""

    tmdb_id: int
