"""
Utilitaires d'authentification pour HorRAGor.

Ce module fournit les fonctions nécessaires pour :
    - Hacher et vérifier les mots de passe (bcrypt)
    - Créer et valider les tokens JWT (access + refresh)
    - Récupérer l'utilisateur courant depuis un token
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from api.auth_config import (
    ACCESS_TOKEN_EXPIRE,
    JWT_ALGORITHM,
    JWT_SECRET_KEY,
    REFRESH_TOKEN_EXPIRE,
)
from database.connection import get_db
from database.tables.refresh_tokens import RefreshToken
from database.tables.users import User

# Configuration du hachage de mots de passe
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Configuration du bearer token
security = HTTPBearer()


# === PASSWORD HASHING ===
def hash_password(password: str) -> str:
    """
    Hash un mot de passe en utilisant bcrypt.
    
    Args:
        password: Mot de passe en clair
        
    Returns:
        Hash du mot de passe
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Vérifie qu'un mot de passe correspond à son hash.
    
    Args:
        plain_password: Mot de passe en clair
        hashed_password: Hash du mot de passe
        
    Returns:
        True si le mot de passe correspond, False sinon
    """
    return pwd_context.verify(plain_password, hashed_password)


# === JWT TOKEN CREATION ===
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Crée un access token JWT.
    
    Args:
        data: Données à inclure dans le token (user_id, email, etc.)
        expires_delta: Durée de validité personnalisée
        
    Returns:
        Token JWT encodé
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + ACCESS_TOKEN_EXPIRE
    
    to_encode.update({
        "exp": expire,
        "type": "access"
    })
    
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def create_refresh_token(user_id: int, db: Session) -> str:
    """
    Crée un refresh token et le stocke en base de données.
    
    Args:
        user_id: ID de l'utilisateur
        db: Session de base de données
        
    Returns:
        Token de rafraîchissement UUID
    """
    # Générer un UUID unique
    token = str(uuid.uuid4())
    
    # Calculer la date d'expiration
    expires_at = datetime.utcnow() + REFRESH_TOKEN_EXPIRE
    
    # Créer l'entrée en base
    refresh_token = RefreshToken(
        token=token,
        user_id=user_id,
        expires_at=expires_at
    )
    
    db.add(refresh_token)
    db.commit()
    
    return token


# === JWT TOKEN VALIDATION ===
def decode_access_token(token: str) -> dict:
    """
    Décode et valide un access token JWT.
    
    Args:
        token: Token JWT à décoder
        
    Returns:
        Payload du token
        
    Raises:
        HTTPException: Si le token est invalide ou expiré
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        
        # Vérifier le type de token
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Type de token invalide"
            )
        
        return payload
    
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré",
            headers={"WWW-Authenticate": "Bearer"}
        )


def validate_refresh_token(token: str, db: Session) -> RefreshToken:
    """
    Valide un refresh token.
    
    Args:
        token: Refresh token à valider
        db: Session de base de données
        
    Returns:
        Objet RefreshToken si valide
        
    Raises:
        HTTPException: Si le token est invalide, expiré ou révoqué
    """
    # Chercher le token en base
    refresh_token = db.query(RefreshToken).filter(
        RefreshToken.token == token
    ).first()
    
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token invalide"
        )
    
    # Vérifier s'il est révoqué
    if refresh_token.is_revoked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token révoqué"
        )
    
    # Vérifier s'il est expiré
    if refresh_token.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expiré"
        )
    
    return refresh_token


# === USER AUTHENTICATION ===
def authenticate_user(email: str, password: str, db: Session) -> Optional[User]:
    """
    Authentifie un utilisateur avec son email et mot de passe.
    
    Args:
        email: Email de l'utilisateur
        password: Mot de passe en clair
        db: Session de base de données
        
    Returns:
        Objet User si l'authentification réussit, None sinon
    """
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        return None
    
    if not verify_password(password, user.hashed_password):
        return None
    
    return user


# === DEPENDENCY: GET CURRENT USER ===
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Dépendance FastAPI pour récupérer l'utilisateur courant depuis le token.
    
    Args:
        credentials: Token Bearer
        db: Session de base de données
        
    Returns:
        Utilisateur courant
        
    Raises:
        HTTPException: Si le token est invalide ou l'utilisateur n'existe pas
    """
    token = credentials.credentials
    
    # Décoder le token
    payload = decode_access_token(token)
    
    # Récupérer l'ID utilisateur
    user_id: int = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide"
        )
    
    # Récupérer l'utilisateur en base
    user = db.query(User).filter(User.id == user_id).first()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur introuvable"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compte désactivé"
        )
    
    return user


# === REVOKE TOKENS ===
def revoke_all_user_tokens(user_id: int, db: Session) -> None:
    """
    Révoque tous les refresh tokens d'un utilisateur (déconnexion globale).
    
    Args:
        user_id: ID de l'utilisateur
        db: Session de base de données
    """
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id,
        RefreshToken.is_revoked == False
    ).update({"is_revoked": True})
    
    db.commit()


def revoke_refresh_token(token: str, db: Session) -> None:
    """
    Révoque un refresh token spécifique.
    
    Args:
        token: Refresh token à révoquer
        db: Session de base de données
    """
    refresh_token = db.query(RefreshToken).filter(
        RefreshToken.token == token
    ).first()
    
    if refresh_token:
        refresh_token.is_revoked = True
        db.commit()
