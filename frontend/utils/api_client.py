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
    - send_chat_query : Envoie une requête au chatbot avec filtres (synchrone)
    - send_chat_query_streaming : Envoie une requête au chatbot en mode streaming SSE
    - get_chat_history : Récupère l'historique de conversation persisté de l'utilisateur
    - get_wikipedia_info : Récupère des informations depuis Wikipedia

Auteur : Flavie (Epic 7)
"""

import json
import os
from typing import Any, Dict, List, Optional

import httpx
import requests
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


def get_database_api_url() -> str:
    """Récupère l'URL de l'API Database, séparée de l'API IA."""
    return os.getenv("DATABASE_API_URL", "http://localhost:8001")


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
        # Timeout augmenté à 30s pour permettre le chargement FAISS au démarrage
        response = requests.get(f"{api_url}/health", timeout=30)
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
    # Validation de l'ID
    if film_id <= 0:
        print(f"ID de film invalide: {film_id}")
        return None

    api_url = get_database_api_url()
    try:
        response = requests.get(f"{api_url}/db/film/{film_id}", timeout=10)
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
    api_url = get_database_api_url()
    try:
        response = requests.get(f"{api_url}/db/list_real", timeout=10)
        response.raise_for_status()
        data = response.json()
        # L'API retourne {"directors": [...]}
        return data.get("directors", []) if isinstance(data, dict) else data
    except (requests.exceptions.RequestException, ValueError) as e:
        print(f"Erreur lors de la récupération des réalisateurs: {e}")
        return []


def get_genres() -> List[str]:
    """
    Récupère la liste de tous les genres cinématographiques.

    Returns:
        Liste des genres
    """
    api_url = get_database_api_url()
    try:
        response = requests.get(f"{api_url}/db/list_genre", timeout=10)
        response.raise_for_status()
        data = response.json()
        # L'API retourne {"genres": [...]}
        return data.get("genres", []) if isinstance(data, dict) else data
    except (requests.exceptions.RequestException, ValueError) as e:
        print(f"Erreur lors de la récupération des genres: {e}")
        return []


def send_chat_query(
    prompt: str, filters: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
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
        - answer: Texte généré par le LLM
        - recommendations: Liste des films recommandés
        - steps: Liste des étapes de l'agent
        Ou None si erreur
    """
    # Validation du prompt
    if not prompt or not prompt.strip():
        print("Le message ne peut pas être vide")
        return None

    api_url = get_api_url()

    # Adapter les filtres au format API
    api_filters = None
    if filters:
        api_filters = {
            "realisateur": filters.get("realisateur"),
            "genres_included": filters.get("genres_inclus", []),
            "genres_excluded": filters.get("genres_exclus", []),
            "release_year_min": filters.get("date_sortie_min"),
            "release_year_max": filters.get("date_sortie_max"),
            "tmdb_score_min": filters.get("score_tmdb_min"),
            "runtime_min": filters.get("duree_min"),
            "runtime_max": filters.get("duree_max"),
        }
        # Retirer les clés None
        api_filters = {k: v for k, v in api_filters.items() if v is not None}

    # Préparer le payload avec le format API
    payload = {"message": prompt, "filters": api_filters}

    try:
        final_event = None
        with httpx.Client(timeout=None) as client:
            with client.stream(
                "POST", f"{api_url}/chat/response_stream", json=payload
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    event = json.loads(line[6:])
                    if "answer" in event:
                        final_event = event
                    if event.get("type") == "done":
                        break

        if final_event is None:
            return None

        # Adapter la réponse API au format attendu par le frontend
        films = final_event.get("recommendations", [])
        if not films and final_event.get("film"):
            films = [final_event["film"]]
        return {
            "status": "success",
            "reponse_texte": final_event.get("answer", ""),
            "films_recommandes": films,
            "etats_agent": final_event.get("steps", []),
        }
    except (requests.exceptions.Timeout, httpx.TimeoutException):
        return {
            "status": "error",
            "message_erreur": "La requête a pris trop de temps. L'agent est peut-être surchargé.",
        }
    except (requests.exceptions.RequestException, httpx.RequestError) as e:
        return {
            "status": "error",
            "message_erreur": f"Erreur de communication avec l'API: {str(e)}",
        }


def get_chat_history(access_token: str) -> List[Dict[str, Any]]:
    """
    Récupère l'historique de conversation persisté de l'utilisateur connecté.

    Args:
        access_token: Access token JWT de l'utilisateur connecté.

    Returns:
        Messages {"role", "content", "films"?} dans l'ordre chronologique,
        au format attendu par `st.session_state.messages`. Liste vide si
        l'utilisateur n'a pas encore de conversation ou si l'appel échoue.
    """
    api_url = get_api_url()
    headers = {"Authorization": f"Bearer {access_token}"}

    try:
        response = requests.get(
            f"{api_url}/chat/history", headers=headers, timeout=10
        )
        response.raise_for_status()
        return response.json().get("history", [])
    except requests.exceptions.RequestException:
        return []


def send_chat_query_streaming(
    prompt: str, access_token: str, filters: Optional[Dict[str, Any]] = None
):
    """
    Envoie une requête au chatbot en mode streaming pour recevoir les mises à jour
    de l'état de réflexion de l'agent en temps réel via Server-Sent Events (SSE).

    Cette fonction utilise httpx pour consommer l'endpoint /chat/response_stream.
    Elle yield progressivement :
    - Les étapes intermédiaires avec {"node": ..., "step": {...}}
    - La réponse finale avec {"answer": ..., "steps": [...], "recommendations": [...]}
    - L'événement de fin {"type": "done"}

    Args:
        prompt: Question ou requête de l'utilisateur
        access_token: Access token JWT de l'utilisateur connecté (endpoint
            protégé — la mémoire de conversation est indexée par utilisateur)
        filters: Dictionnaire optionnel contenant les filtres SQL

    Yields:
        Dictionnaires contenant les états intermédiaires et la réponse finale.
        {"error": ...} si le token est absent ou rejeté (401).

    Exemple d'utilisation:
        for event in send_chat_query_streaming("Film d'horreur", token, filters):
            if "step" in event:
                print(f"Étape: {event['step']}")
            elif "answer" in event:
                print(f"Réponse: {event['answer']}")
            elif event.get("type") == "done":
                break
    """
    api_url = get_api_url()

    # Adapter les filtres au format API (même format que send_chat_query)
    api_filters = None
    if filters:
        api_filters = {
            "realisateur": filters.get("realisateur"),
            "genres_included": filters.get("genres_inclus", []),
            "genres_excluded": filters.get("genres_exclus", []),
            "release_year_min": filters.get("date_sortie_min"),
            "release_year_max": filters.get("date_sortie_max"),
            "tmdb_score_min": filters.get("score_tmdb_min"),
            "runtime_min": filters.get("duree_min"),
            "runtime_max": filters.get("duree_max"),
        }
        api_filters = {k: v for k, v in api_filters.items() if v is not None}

    payload = {"message": prompt, "filters": api_filters}
    headers = {"Authorization": f"Bearer {access_token}"}

    try:
        # Utiliser httpx pour le streaming SSE (plus robuste que requests)
        with httpx.Client(timeout=None) as client:
            with client.stream(
                "POST", f"{api_url}/chat/response_stream", json=payload, headers=headers
            ) as response:
                response.raise_for_status()
                
                for line in response.iter_lines():
                    # Ignorer les lignes vides ou sans préfixe "data: "
                    if not line or not line.startswith("data: "):
                        continue

                    # Parser l'événement SSE
                    event = json.loads(line[6:])
                    yield event
                    
                    # Arrêter si c'est l'événement de fin
                    if event.get("type") == "done":
                        break

    except httpx.RequestError as e:
        yield {"error": f"Erreur de connexion: {str(e)}"}
    except Exception as e:
        yield {"error": f"Erreur de streaming: {str(e)}"}


def get_wikipedia_info(tmdb_id: int) -> Optional[Dict[str, Any]]:
    """
    Récupère les informations détaillées d'un film depuis Wikipedia.

    Args:
        tmdb_id: ID TMDB du film

    Returns:
        Dictionnaire contenant le synopsis et informations Wikipedia ou None
    """
    api_url = get_api_url()
    try:
        response = requests.get(f"{api_url}/wikipedia/{tmdb_id}", timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Erreur lors de la récupération Wikipedia pour TMDB ID {tmdb_id}: {e}")
        return None
