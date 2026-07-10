"""
Routes d'authentification pour HorRAGor.

Ce module expose les endpoints de gestion d'authentification :
    - POST /auth/register : Créer un nouveau compte utilisateur
    - POST /auth/login : Se connecter et obtenir des tokens JWT
    - POST /auth/refresh : Rafraîchir un access token avec un refresh token
    - POST /auth/logout : Se déconnecter (révoquer le refresh token)
    - GET /auth/me : Obtenir les informations de l'utilisateur courant

Auteur : Flavie (Epic 10)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.auth_utils import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    get_current_user,
    hash_password,
    revoke_all_user_tokens,
    revoke_refresh_token,
    validate_refresh_token,
)
from api.schemas import (
    AuthResponse,
    ErrorResponse,
    Token,
    TokenRefresh,
    UserLogin,
    UserRegister,
    UserResponse,
)
from database.connection import get_db
from database.tables.users import User
from logger import get_logger, setup_logger

setup_logger()
logger = get_logger("AUTH_ROUTES")

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse},
        409: {"model": ErrorResponse}
    }
)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """
    Créer un nouveau compte utilisateur.
    
    Retourne l'utilisateur créé avec ses tokens JWT.
    """
    logger.info(f"Tentative d'inscription : {user_data.email}")
    
    try:
        # Vérifier si l'email existe déjà
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            logger.warning(f"Email déjà utilisé : {user_data.email}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Un compte avec cet email existe déjà"
            )
        
        # Vérifier si le username existe déjà
        existing_username = db.query(User).filter(User.username == user_data.username).first()
        if existing_username:
            logger.warning(f"Username déjà utilisé : {user_data.username}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ce nom d'utilisateur est déjà pris"
            )
        
        # Créer le nouvel utilisateur
        new_user = User(
            email=user_data.email,
            username=user_data.username,
            hashed_password=hash_password(user_data.password)
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        logger.info(f"Utilisateur créé avec succès : {new_user.id} - {new_user.email}")
        
        # Créer les tokens
        access_token = create_access_token(data={"sub": new_user.id, "email": new_user.email})
        refresh_token = create_refresh_token(new_user.id, db)
        
        return AuthResponse(
            user=UserResponse(
                id=new_user.id,
                email=new_user.email,
                username=new_user.username,
                is_active=new_user.is_active,
                is_verified=new_user.is_verified,
                created_at=new_user.created_at
            ),
            access_token=access_token,
            refresh_token=refresh_token
        )
    
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Erreur d'intégrité lors de l'inscription : {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Erreur lors de la création du compte"
        )


@router.post(
    "/login",
    response_model=AuthResponse,
    responses={401: {"model": ErrorResponse}}
)
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Se connecter avec email et mot de passe.
    
    Retourne l'utilisateur et ses tokens JWT.
    """
    logger.info(f"Tentative de connexion : {credentials.email}")
    
    # Authentifier l'utilisateur
    user = authenticate_user(credentials.email, credentials.password, db)
    
    if not user:
        logger.warning(f"Échec de connexion : {credentials.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect"
        )
    
    logger.info(f"Connexion réussie : {user.id} - {user.email}")
    
    # Créer les tokens
    access_token = create_access_token(data={"sub": user.id, "email": user.email})
    refresh_token = create_refresh_token(user.id, db)
    
    return AuthResponse(
        user=UserResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            is_active=user.is_active,
            is_verified=user.is_verified,
            created_at=user.created_at
        ),
        access_token=access_token,
        refresh_token=refresh_token
    )


@router.post(
    "/refresh",
    response_model=Token,
    responses={401: {"model": ErrorResponse}}
)
async def refresh_token(token_data: TokenRefresh, db: Session = Depends(get_db)):
    """
    Rafraîchir un access token avec un refresh token.
    
    Retourne un nouveau access token et refresh token.
    """
    logger.info("Tentative de rafraîchissement de token")
    
    # Valider le refresh token
    refresh_token_obj = validate_refresh_token(token_data.refresh_token, db)
    
    # Récupérer l'utilisateur
    user = db.query(User).filter(User.id == refresh_token_obj.user_id).first()
    
    if not user or not user.is_active:
        logger.warning(f"Utilisateur introuvable ou inactif : {refresh_token_obj.user_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur introuvable ou inactif"
        )
    
    logger.info(f"Token rafraîchi pour : {user.id} - {user.email}")
    
    # Révoquer l'ancien refresh token
    revoke_refresh_token(token_data.refresh_token, db)
    
    # Créer de nouveaux tokens
    access_token = create_access_token(data={"sub": user.id, "email": user.email})
    new_refresh_token = create_refresh_token(user.id, db)
    
    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={401: {"model": ErrorResponse}}
)
async def logout(
    token_data: TokenRefresh,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Se déconnecter en révoquant le refresh token.
    """
    logger.info(f"Déconnexion de : {current_user.id} - {current_user.email}")
    
    # Révoquer le refresh token
    revoke_refresh_token(token_data.refresh_token, db)
    
    return None


@router.post(
    "/logout-all",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={401: {"model": ErrorResponse}}
)
async def logout_all(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Se déconnecter de tous les appareils en révoquant tous les refresh tokens.
    """
    logger.info(f"Déconnexion globale de : {current_user.id} - {current_user.email}")
    
    # Révoquer tous les refresh tokens de l'utilisateur
    revoke_all_user_tokens(current_user.id, db)
    
    return None


@router.get(
    "/me",
    response_model=UserResponse,
    responses={401: {"model": ErrorResponse}}
)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Obtenir les informations de l'utilisateur courant.
    """
    logger.info(f"Récupération du profil : {current_user.id} - {current_user.email}")
    
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at
    )
