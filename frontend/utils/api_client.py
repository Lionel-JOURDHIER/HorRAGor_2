"""frontend/utils/api_client.py
Module de communication avec l'API FastAPI HorRAGor.

Ce module encapsule toutes les interactions HTTP avec le back-end FastAPI.
Il garantit un découplage strict entre l'interface Streamlit et la logique métier.

Fonctions disponibles :
    - get_api_url : Récupère l'URL de l'API depuis les variables d'environnement
    - check_health : Vérifie la santé de l'API
    - get_film_by_id : Récupère les détails d'un film par son ID
    - get_realisateurs : Récupère la liste des réalisateurs
    - get_genres : Récupère la liste des genres
    - send_chat_query : Envoie une requête au chatbot avec filtres
    - get_wikipedia_info : Récupère des informations depuis Wikipedia

Auteur : Flavie (Epic 7)
"""

import os
import requests
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()


def get_api_url() -> str:
    """
    Récupère l'URL de l'API depuis les variables d'environnement.
    
    Returns:
        URL de l'API (par défaut: http://localhost:8000)
    """
    return os.getenv("API_URL", "http://localhost:8000")


def check_health() -> Dict[str, Any]:
    """
    Vérifie la santé de l'API.
    
    Returns:
        Dictionnaire avec le statut de l'API
        
    Raises:
        requests.exceptions.RequestException: Si l'API n'est pas accessible
    """
    api_url = get_api_url()
    try:
        response = requests.get(f"{api_url}/health", timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": str(e)}


def get_film_by_id(film_id: int) -> Optional[Dict[str, Any]]:
    """
    Récupère les informations détaillées d'un film par son ID.
    
    Args:
        film_id: Identifiant unique du film (tmdb_id)
        
    Returns:
        Dictionnaire contenant les informations du film ou None si erreur
    """
    api_url = get_api_url()
    try:
        response = requests.get(f"{api_url}/film/{film_id}", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Erreur lors de la récupération du film {film_id}: {e}")
        return None


def get_realisateurs() -> List[str]:
    """
    Récupère la liste de tous les réalisateurs disponibles.
    
    Returns:
        Liste des noms de réalisateurs
    """
    api_url = get_api_url()
    try:
        response = requests.get(f"{api_url}/list_real", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Erreur lors de la récupération des réalisateurs: {e}")
        return []


def get_genres() -> List[str]:
    """
    Récupère la liste de tous les genres cinématographiques.
    
    Returns:
        Liste des genres
    """
    api_url = get_api_url()
    try:
        response = requests.get(f"{api_url}/list_genre", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Erreur lors de la récupération des genres: {e}")
        return []


def send_chat_query(prompt: str, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Envoie une requête au chatbot avec le texte utilisateur et les filtres optionnels.
    
    Cette fonction communique avec l'endpoint POST /chat qui orchestre l'agent ReAct,
    utilise les outils (SQL, Vector, Wikipedia) et retourne une réponse validée.
    
    Args:
        prompt: Question ou requête de l'utilisateur
        filters: Dictionnaire optionnel contenant les filtres SQL :
                - realisateur: str
                - genres_inclus: List[str]
                - genres_exclus: List[str]
                - date_sortie_min: int
                - date_sortie_max: int
                - score_tmdb_min: float
                - duree_min: int
                - duree_max: int
    
    Returns:
        Dictionnaire contenant :
        - status: "success" ou "error"
        - reponse_texte: Texte généré par le LLM
        - films_recommandes: Liste des 5 films avec détails
        - etats_agent: Liste des états de réflexion (optionnel)
        - message_erreur: Message d'erreur si échec
    """
    api_url = get_api_url()
    
    # Préparer le payload
    payload = {
        "prompt": prompt,
        "filters": filters or {}
    }
    
    try:
        response = requests.post(
            f"{api_url}/chat",
            json=payload,
            timeout=60  # Timeout plus long pour l'agent
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        return {
            "status": "error",
            "message_erreur": "La requête a pris trop de temps. L'agent est peut-être surchargé."
        }
    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "message_erreur": f"Erreur de communication avec l'API: {str(e)}"
        }


def send_chat_query_streaming(prompt: str, filters: Optional[Dict[str, Any]] = None):
    """
    Envoie une requête au chatbot en mode streaming pour recevoir les mises à jour
    de l'état de réflexion de l'agent en temps réel.
    
    Args:
        prompt: Question ou requête de l'utilisateur
        filters: Dictionnaire optionnel contenant les filtres SQL
        
    Yields:
        Dictionnaires contenant les états intermédiaires et la réponse finale
    """
    api_url = get_api_url()
    
    payload = {
        "prompt": prompt,
        "filters": filters or {}
    }
    
    try:
        response = requests.post(
            f"{api_url}/chat",
            json=payload,
            stream=True,
            timeout=120
        )
        response.raise_for_status()
        
        for line in response.iter_lines():
            if line:
                # Parser les événements SSE (Server-Sent Events)
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    import json
                    data = json.loads(line_str[6:])
                    yield data
                    
    except requests.exceptions.RequestException as e:
        yield {
            "status": "error",
            "message_erreur": f"Erreur de streaming: {str(e)}"
        }


def get_wikipedia_info(film_title: str) -> Optional[Dict[str, Any]]:
    """
    Récupère les informations détaillées d'un film depuis Wikipedia.
    
    Args:
        film_title: Titre du film à rechercher
        
    Returns:
        Dictionnaire contenant le synopsis et informations Wikipedia ou None
    """
    api_url = get_api_url()
    try:
        response = requests.get(
            f"{api_url}/wikipedia",
            params={"title": film_title},
            timeout=15
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Erreur lors de la récupération Wikipedia pour {film_title}: {e}")
        return None
