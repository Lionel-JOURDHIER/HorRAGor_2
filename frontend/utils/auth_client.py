"""
Module de gestion de l'authentification frontend pour HorRAGor.

Fonctions d'interaction avec l'API d'authentification :
    - login_user : Se connecter avec email/password
    - register_user : Créer un nouveau compte
    - refresh_access_token : Rafraîchir l'access token
    - logout_user : Se déconnecter
    - get_current_user : Récupérer les infos de l'utilisateur connecté
"""

import requests
from typing import Optional, Dict, Any
from utils.api_client import get_api_url

def login_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Authentifie un utilisateur avec email et mot de passe.
    
    Args:
        email: Email de l'utilisateur
        password: Mot de passe
        
    Returns:
        Dictionnaire contenant user, access_token, refresh_token si succès
        None en cas d'échec
    """
    try:
        response = requests.post(
            f"{get_api_url()}/auth/login",
            json={"email": email, "password": password},
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return None
    
    except Exception as e:
        print(f"Erreur lors de la connexion : {e}")
        return None


def register_user(email: str, username: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Crée un nouveau compte utilisateur.
    
    Args:
        email: Email de l'utilisateur
        username: Nom d'utilisateur
        password: Mot de passe
        
    Returns:
        Dictionnaire contenant user, access_token, refresh_token si succès
        None en cas d'échec
    """
    try:
        response = requests.post(
            f"{get_api_url()}/auth/register",
            json={"email": email, "username": username, "password": password},
            timeout=10
        )
        
        if response.status_code == 201:
            return response.json()
        else:
            return None
    
    except Exception as e:
        print(f"Erreur lors de l'inscription : {e}")
        return None


def refresh_access_token(refresh_token: str) -> Optional[Dict[str, str]]:
    """
    Rafraîchit l'access token avec un refresh token.
    
    Args:
        refresh_token: Refresh token valide
        
    Returns:
        Dictionnaire contenant access_token et refresh_token si succès
        None en cas d'échec
    """
    try:
        response = requests.post(
            f"{get_api_url()}/auth/refresh",
            json={"refresh_token": refresh_token},
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return None
    
    except Exception as e:
        print(f"Erreur lors du rafraîchissement : {e}")
        return None


def logout_user(refresh_token: str, access_token: str) -> bool:
    """
    Déconnecte l'utilisateur en révoquant le refresh token.
    
    Args:
        refresh_token: Refresh token à révoquer
        access_token: Access token pour l'authentification
        
    Returns:
        True si la déconnexion a réussi, False sinon
    """
    try:
        response = requests.post(
            f"{get_api_url()}/auth/logout",
            json={"refresh_token": refresh_token},
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10
        )
        
        return response.status_code == 204
    
    except Exception as e:
        print(f"Erreur lors de la déconnexion : {e}")
        return False


def get_current_user(access_token: str) -> Optional[Dict[str, Any]]:
    """
    Récupère les informations de l'utilisateur courant.
    
    Args:
        access_token: Access token valide
        
    Returns:
        Dictionnaire contenant les infos utilisateur si succès
        None en cas d'échec
    """
    try:
        response = requests.get(
            f"{get_api_url()}/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return None
    
    except Exception as e:
        print(f"Erreur lors de la récupération du profil : {e}")
        return None
