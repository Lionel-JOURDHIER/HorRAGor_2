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
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

# CLASSES GENERAL -----------------------------------------------------------
class HealthResponse(BaseModel):
    status: str = "ok"

# CLASSES FILMS -----------------------------------------------------------
class FilmShort(BaseModel):
    tmdb_id: int
    title: str
    release_date: Optional[date] = None
    genres: List[str] = Field(default_factory=list)
    tmdb_score: Optional[float] = None
    

class FilmDetail(BaseModel):
    tmdb_id: int
    title: str

    original_title: Optional[str] = None
    original_language: Optional[str] = None

    realisateur: Optional[str] = None
    release_date: Optional[date] = None
    runtime: Optional[int] = None
    status: Optional[str] = None
    synopsis: Optional[str] = None      # FILMS.overview
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

    realisateur: Optional[str] = None

    genres_included: List[str] = []
    genres_excluded: List[str] = []

    release_year_min: Optional[int] = Field(
        default=None,
        ge=1900,
        le=2026
    )

    release_year_max: Optional[int] = Field(
        default=None,
        ge=1900,
        le=2026
    )

    tmdb_score_min: Optional[float] = Field(
        default=None,
        ge=0,
        le=10
    )

    runtime_min: Optional[int] = Field(
        default=None,
        ge=1,
        le=685
    )

    runtime_max: Optional[int] = Field(
        default=None,
        ge=1,
        le=685
    )

# REQUESTS RESPONSE -----------------------------------------------------------
class ChatRequest(BaseModel):

    message: str = Field(
        min_length=1,
        max_length=2000
    )

    filters: Optional[ChatFilters] = None

class AgentStep(BaseModel):

    step: str

    status: str

class ChatResponse(BaseModel):

    answer: str

    steps: List[AgentStep] = []

    recommendations: List[FilmShort] = []

class WikipediaResponse(BaseModel):

    title: str

    synopsis: str

    source: str = "wikipedia"