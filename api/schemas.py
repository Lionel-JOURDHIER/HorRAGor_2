"""api/schemas.py
Schémas Pydantic propres à l'authentification de l'API HorRAGor.

Les schémas partagés avec le reste du dépôt (agents, database, films, chat)
vivent dans `shared/schemas.py` — ce module ne redéfinit que ce qui n'existe
nulle part ailleurs : les modèles d'inscription, de connexion et de jetons
consommés par `api/auth_routes.py`.

Auteur/Responsable : Hanna (Epic 3)
"""

from typing import Any

from pydantic import BaseModel, Field


class UserRegister(BaseModel):
    """User registration request."""

    email: str = Field(
        min_length=3,
        max_length=255,
        pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
    )
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8, max_length=100)


class UserLogin(BaseModel):
    """User login request."""

    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=100)


class Token(BaseModel):
    """JWT token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    """Refresh token request."""

    refresh_token: str


class UserResponse(BaseModel):
    """User information response (public data only)."""

    id: int
    email: str
    username: str
    is_active: bool
    is_verified: bool
    created_at: Any  # datetime


class AuthResponse(BaseModel):
    """Complete authentication response with user info and tokens."""

    user: UserResponse
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
