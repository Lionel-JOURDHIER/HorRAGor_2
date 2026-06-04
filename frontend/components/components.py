"""frontend/components/components.py
Composants UI réutilisables pour l'interface Streamlit de HorRAGor.

Ce module contient les composants graphiques modulaires utilisés dans l'interface
principale pour afficher les films, gérer les formulaires et l'historique de chat.

Composants disponibles :
    - display_movie_card : Affiche une carte visuelle d'un film avec affiche et détails
    - display_movie_list : Affiche une liste de films recommandés
    - create_filters_sidebar : Crée la barre latérale avec tous les filtres SQL
    - display_chat_message : Affiche un message du chat avec style personnalisé
    - display_loading_indicator : Affiche un indicateur de chargement animé
    - display_agent_status : Affiche l'état de réflexion de l'agent

Auteur : Flavie (Epic 7)
"""

import streamlit as st
from typing import Dict, List, Optional, Any


def display_movie_card(movie: Dict[str, Any], show_details: bool = True) -> None:
    """
    Affiche une carte visuelle pour un film avec son affiche et ses informations.
    
    Args:
        movie: Dictionnaire contenant les informations du film
               (titre, realisateur, annee, score_tmdb, synopsis, poster_url, etc.)
        show_details: Si True, affiche les détails complets, sinon version compacte
    """
    with st.container():
        col1, col2 = st.columns([1, 2])
        
        with col1:
            # Affichage de l'affiche du film
            if movie.get("poster_url"):
                st.image(movie["poster_url"], use_container_width=True)
            else:
                st.info("🎬 Pas d'affiche disponible")
        
        with col2:
            # Titre du film
            st.markdown(f"### {movie.get('titre', 'Titre inconnu')}")
            
            # Informations principales
            if movie.get("realisateur"):
                st.markdown(f"**🎥 Réalisateur :** {movie['realisateur']}")
            
            if movie.get("annee"):
                st.markdown(f"**📅 Année :** {movie['annee']}")
            
            if movie.get("score_tmdb") is not None:
                score = movie["score_tmdb"]
                st.markdown(f"**⭐ Score TMDB :** {score}/10")
                st.progress(score / 10)
            
            if movie.get("duree"):
                st.markdown(f"**⏱️ Durée :** {movie['duree']} minutes")
            
            if movie.get("genres"):
                genres = movie["genres"]
                if isinstance(genres, list):
                    genres_str = ", ".join(genres)
                else:
                    genres_str = genres
                st.markdown(f"**🎭 Genres :** {genres_str}")
            
            # Synopsis en mode détaillé
            if show_details and movie.get("synopsis"):
                with st.expander("📖 Synopsis"):
                    st.write(movie["synopsis"])
        
        st.divider()


def display_movie_list(movies: List[Dict[str, Any]], title: str = "🎬 Films recommandés") -> None:
    """
    Affiche une liste de films sous forme de cartes compactes.
    
    Args:
        movies: Liste de dictionnaires contenant les informations des films
        title: Titre de la section
    """
    if not movies:
        st.warning("Aucun film à afficher")
        return
    
    st.markdown(f"## {title}")
    st.markdown(f"*{len(movies)} film(s) trouvé(s)*")
    
    for idx, movie in enumerate(movies, 1):
        with st.expander(f"#{idx} - {movie.get('titre', 'Titre inconnu')} ({movie.get('annee', 'N/A')})"):
            display_movie_card(movie, show_details=True)


def create_filters_sidebar(api_url: str) -> Dict[str, Any]:
    """
    Crée la barre latérale avec tous les filtres de recherche SQL.
    
    Args:
        api_url: URL de base de l'API pour récupérer les listes
        
    Returns:
        Dictionnaire contenant tous les filtres sélectionnés
    """
    import requests
    
    with st.sidebar:
        st.title("🔍 Filtres de recherche")
        st.markdown("---")
        
        filters = {}
        
        # Filtre Réalisateur
        st.subheader("🎥 Réalisateur")
        try:
            response = requests.get(f"{api_url}/list_real", timeout=5)
            if response.status_code == 200:
                realisateurs = response.json()
                selected_real = st.selectbox(
                    "Choisir un réalisateur",
                    options=["Tous"] + realisateurs,
                    index=0
                )
                if selected_real != "Tous":
                    filters["realisateur"] = selected_real
            else:
                st.warning("Impossible de charger les réalisateurs")
        except Exception as e:
            st.error(f"Erreur : {e}")
        
        st.markdown("---")
        
        # Filtres Genres
        st.subheader("🎭 Genres")
        try:
            response = requests.get(f"{api_url}/list_genre", timeout=5)
            if response.status_code == 200:
                genres = response.json()
                
                genres_inclus = st.multiselect(
                    "Genres à conserver",
                    options=genres,
                    default=[]
                )
                if genres_inclus:
                    filters["genres_inclus"] = genres_inclus
                
                genres_exclus = st.multiselect(
                    "Genres non souhaités",
                    options=genres,
                    default=[]
                )
                if genres_exclus:
                    filters["genres_exclus"] = genres_exclus
            else:
                st.warning("Impossible de charger les genres")
        except Exception as e:
            st.error(f"Erreur : {e}")
        
        st.markdown("---")
        
        # Filtre Date de sortie
        st.subheader("📅 Date de sortie")
        date_range = st.slider(
            "Plage de dates",
            min_value=1900,
            max_value=2026,
            value=(1980, 2026),
            step=1
        )
        filters["date_sortie_min"] = date_range[0]
        filters["date_sortie_max"] = date_range[1]
        
        st.markdown("---")
        
        # Filtre Score TMDB
        st.subheader("⭐ Score TMDB")
        score_min = st.slider(
            "Score minimum",
            min_value=0.0,
            max_value=10.0,
            value=5.0,
            step=0.5
        )
        filters["score_tmdb_min"] = score_min
        
        st.markdown("---")
        
        # Filtre Durée
        st.subheader("⏱️ Durée du film")
        duree_range = st.slider(
            "Durée en minutes",
            min_value=1,
            max_value=685,
            value=(60, 180),
            step=5
        )
        filters["duree_min"] = duree_range[0]
        filters["duree_max"] = duree_range[1]
        
        st.markdown("---")
        
        # Bouton reset
        if st.button("🔄 Réinitialiser les filtres"):
            st.rerun()
        
        return filters


def display_chat_message(role: str, content: str, avatar: Optional[str] = None) -> None:
    """
    Affiche un message dans le chat avec style personnalisé.
    
    Args:
        role: "user" ou "assistant"
        content: Contenu du message
        avatar: Emoji ou URL pour l'avatar
    """
    if avatar is None:
        avatar = "👤" if role == "user" else "🤖"
    
    with st.chat_message(role, avatar=avatar):
        st.markdown(content)


def display_loading_indicator(message: str = "L'agent réfléchit...") -> None:
    """
    Affiche un indicateur de chargement avec message personnalisé.
    
    Args:
        message: Message à afficher pendant le chargement
    """
    with st.spinner(message):
        st.markdown("🧠 **Analyse en cours...**")


def display_agent_status(status: Dict[str, Any]) -> None:
    """
    Affiche l'état de réflexion de l'agent ReAct.
    
    Args:
        status: Dictionnaire contenant l'état actuel de l'agent
                (étape, tool utilisé, progression, etc.)
    """
    if not status:
        return
    
    with st.expander("🔍 État de réflexion de l'agent", expanded=True):
        # Étape en cours
        if status.get("etape"):
            st.markdown(f"**Étape :** {status['etape']}")
        
        # Tool utilisé
        if status.get("tool"):
            st.markdown(f"**Outil utilisé :** {status['tool']}")
        
        # Pensée de l'agent
        if status.get("pensee"):
            st.info(f"💭 {status['pensee']}")
        
        # Progression
        if status.get("progression") is not None:
            progression = status["progression"]
            st.progress(progression / 100)
            st.caption(f"{progression}% complété")
        
        # Résultat intermédiaire
        if status.get("resultat"):
            with st.container():
                st.markdown("**Résultat intermédiaire :**")
                st.json(status["resultat"])
