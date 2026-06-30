"""frontend/components/components.py
Composants UI réutilisables pour l'interface Streamlit de HorRAGor.

Ce module contient les composants graphiques modulaires utilisés dans l'interface
principale pour afficher les films, gérer les formulaires et l'historique de chat.

Composants disponibles :
    - normalize_movie_data : Adapte les données API au format frontend
    - display_movie_card : Affiche une carte visuelle d'un film avec affiche et détails
    - display_movie_list : Affiche une liste de films recommandés
    - create_filters_sidebar : Crée la barre latérale avec tous les filtres SQL
    - display_chat_message : Affiche un message du chat avec style personnalisé
    - display_loading_indicator : Affiche un indicateur de chargement animé
    - display_agent_status : Affiche l'état de réflexion de l'agent

Auteur : Flavie (Epic 7)
"""

from datetime import date
from typing import Any, Dict, List, Optional

import streamlit as st


def normalize_movie_data(movie: Dict[str, Any]) -> Dict[str, Any]:
    """
    Adapte les données d'un film provenant de l'API au format attendu par le frontend.

    Mapping API -> Frontend :
    - title -> titre
    - release_date -> annee
    - runtime -> duree
    - tmdb_score -> score_tmdb (inchangé)

    Args:
        movie: Données du film au format API

    Returns:
        Données du film au format frontend
    """
    normalized = movie.copy()

    # Mapper title -> titre
    if "title" in normalized:
        normalized["titre"] = normalized.pop("title")

    # Mapper release_date -> annee (extraire l'année)
    if "release_date" in normalized and normalized["release_date"]:
        release_date = normalized["release_date"]
        if isinstance(release_date, str):
            # Format ISO: "2020-01-15" -> 2020
            normalized["annee"] = int(release_date.split("-")[0])
        elif isinstance(release_date, date):
            normalized["annee"] = release_date.year
        normalized.pop("release_date", None)

    # Mapper runtime -> duree
    if "runtime" in normalized:
        normalized["duree"] = normalized.pop("runtime")

    # Mapper director -> realisateur si présent
    if "director" in normalized and not normalized.get("realisateur"):
        normalized["realisateur"] = normalized.pop("director")

    return normalized


def display_movie_card(movie: Dict[str, Any], show_details: bool = True) -> None:
    """
    Affiche une carte visuelle pour un film avec son affiche et ses informations.

    Args:
        movie: Dictionnaire contenant les informations du film (format API)
        show_details: Si True, affiche les détails complets, sinon version compacte
    """
    # Normaliser les données API vers le format frontend
    movie = normalize_movie_data(movie)

    with st.container():
        # Container avec style amélioré
        st.markdown('<div class="movie-card">', unsafe_allow_html=True)

        col1, col2 = st.columns([1, 2])

        with col1:
            # Affichage de l'affiche du film avec effet néon
            if movie.get("poster_url"):
                st.markdown(
                    f"""
                <div style="position: relative; overflow: hidden; border-radius: 20px; 
                            box-shadow: 0 10px 40px rgba(255, 71, 87, 0.5), 0 0 30px rgba(255, 71, 87, 0.3);">
                    <img src="{movie["poster_url"]}" style="width: 100%; display: block; transition: all 0.4s ease;" 
                         onmouseover="this.style.transform='scale(1.08)'; this.style.filter='brightness(1.1)'" 
                         onmouseout="this.style.transform='scale(1)'; this.style.filter='brightness(1)'"/>
                </div>
                """,
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    """
                <div style="background: linear-gradient(135deg, rgba(255, 71, 87, 0.2) 0%, rgba(255, 0, 110, 0.2) 100%); 
                            padding: 60px; text-align: center; border-radius: 20px; 
                            border: 3px dashed rgba(255, 71, 87, 0.5);
                            box-shadow: 0 5px 25px rgba(255, 71, 87, 0.3);">
                    <p style="font-size: 4em; margin: 0;">🎬</p>
                    <p style="opacity: 0.9; margin: 15px 0 0 0; color: #ffffff; font-weight: 600;">Pas d'affiche disponible</p>
                </div>
                """,
                    unsafe_allow_html=True,
                )

        with col2:
            # Titre du film avec style néon
            titre = movie.get("titre", "Titre inconnu")
            annee = movie.get("annee", "N/A")
            st.markdown(
                f"""
            <h2 style="color: #ff4757; margin-bottom: 15px; font-weight: 800;
                       text-shadow: 0 0 15px rgba(255, 71, 87, 0.5);">
                {titre}
            </h2>
            <p style="color: #ffffff; opacity: 0.9; margin-top: -10px; font-size: 1.2em; font-weight: 600;">
                📅 {annee}
            </p>
            """,
                unsafe_allow_html=True,
            )

            # Informations principales avec icônes
            if movie.get("realisateur"):
                st.markdown(
                    f"""
                <div style="background: rgba(255, 71, 87, 0.2); padding: 12px; 
                            border-radius: 15px; margin: 12px 0; border-left: 4px solid #ff4757;
                            box-shadow: 0 4px 15px rgba(255, 71, 87, 0.2);">
                    <strong style="color: #ff4757; font-size: 1.1em;">🎥 Réalisateur :</strong>
                    <span style="color: #ffffff; font-weight: 600;"> {movie["realisateur"]}</span>
                </div>
                """,
                    unsafe_allow_html=True,
                )

            # Score TMDB avec barre de progression visuelle
            if movie.get("score_tmdb") is not None:
                score = movie["score_tmdb"]
                score_percentage = (score / 10) * 100

                # Couleur du score en fonction de la note
                if score >= 7:
                    color = "#4caf50"  # Vert
                elif score >= 5:
                    color = "#ff9800"  # Orange
                else:
                    color = "#f44336"  # Rouge

                st.markdown(
                    f"""
                <div style="margin: 15px 0; background: rgba(255, 71, 87, 0.1); padding: 15px; border-radius: 15px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <strong style="color: #ff4757; font-size: 1.1em;">⭐ Score TMDB</strong>
                        <span style="font-size: 1.8em; font-weight: 800; color: {color};
                                     text-shadow: 0 0 10px {color};">{score}/10</span>
                    </div>
                    <div style="background: rgba(255, 255, 255, 0.15); height: 15px; border-radius: 15px; overflow: hidden;
                                box-shadow: inset 0 2px 5px rgba(0,0,0,0.3);">
                        <div style="background: linear-gradient(90deg, {color} 0%, {color} 100%); 
                                    width: {score_percentage}%; height: 100%; 
                                    transition: width 0.5s ease;
                                    box-shadow: 0 0 15px {color};"></div>
                    </div>
                </div>
                """,
                    unsafe_allow_html=True,
                )

            # Durée du film
            if movie.get("duree"):
                duree = movie["duree"]
                heures = duree // 60
                minutes = duree % 60
                duree_str = f"{heures}h {minutes}min" if heures > 0 else f"{minutes}min"

                st.markdown(
                    f"""
                <div style="display: inline-block; background: linear-gradient(135deg, rgba(255, 71, 87, 0.2), rgba(255, 0, 110, 0.2)); 
                            padding: 10px 20px; border-radius: 25px; margin: 5px;
                            border: 2px solid rgba(255, 71, 87, 0.4);
                            box-shadow: 0 4px 15px rgba(255, 71, 87, 0.2);">
                    <strong style="color: #ff4757;">⏱️ Durée :</strong>
                    <span style="color: #ffffff; font-weight: 700;"> {duree_str}</span>
                </div>
                """,
                    unsafe_allow_html=True,
                )

            # Genres avec tags stylisés
            if movie.get("genres"):
                genres = movie["genres"]
                if isinstance(genres, list):
                    st.markdown('<div style="margin: 15px 0;">', unsafe_allow_html=True)
                    st.markdown(
                        '<strong style="color: #ff4757; font-size: 1.1em;">🎭 Genres :</strong>',
                        unsafe_allow_html=True,
                    )

                    genres_html = ""
                    for genre in genres:
                        genres_html += f"""
                        <span style="display: inline-block; background: linear-gradient(135deg, #ff4757 0%, #ff006e 100%); 
                                     color: white; padding: 8px 18px; border-radius: 25px; margin: 5px; 
                                     font-size: 0.95em; font-weight: 700; 
                                     box-shadow: 0 4px 15px rgba(255, 71, 87, 0.4);
                                     border: 2px solid rgba(255, 255, 255, 0.2);
                                     transition: transform 0.2s ease;">
                            {genre}
                        </span>
                        """
                    st.markdown(genres_html, unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)
                else:
                    st.markdown(
                        f"""
                    <div style="margin: 10px 0;">
                        <strong style="color: #ff4757; font-size: 1.1em;">🎭 Genres :</strong> 
                        <span style="color: #ffffff; font-weight: 600;">{genres}</span>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )

            # Synopsis en mode détaillé avec expander stylisé
            if show_details and movie.get("synopsis"):
                with st.expander("📖 Synopsis", expanded=False):
                    st.markdown(
                        f"""
                    <div style="background: linear-gradient(135deg, rgba(255, 71, 87, 0.1), rgba(255, 0, 110, 0.1)); 
                                padding: 20px; border-radius: 15px; line-height: 1.8;
                                border-left: 4px solid #ff4757; color: #ffffff; font-weight: 500;">
                        {movie["synopsis"]}
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )

        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)


def display_movie_list(
    movies: List[Dict[str, Any]], title: str = "🎬 Films recommandés"
) -> None:
    """
    Affiche une liste de films sous forme de cartes compactes.

    Args:
        movies: Liste de dictionnaires contenant les informations des films (format API)
        title: Titre de la section
    """
    if not movies:
        st.markdown(
            """
        <div style="background: linear-gradient(135deg, rgba(255, 152, 0, 0.2), rgba(255, 193, 7, 0.2)); 
                    padding: 25px; border-radius: 20px; 
                    text-align: center; border: 3px dashed rgba(255, 152, 0, 0.5);
                    box-shadow: 0 5px 25px rgba(255, 152, 0, 0.3);">
            <h3 style="margin: 0; color: #ff9800; font-weight: 700; font-size: 1.5em;">⚠️ Aucun film à afficher</h3>
            <p style="margin: 15px 0 0 0; opacity: 0.9; color: #ffffff; font-weight: 600;">Essayez de modifier vos filtres ou votre requête</p>
        </div>
        """,
            unsafe_allow_html=True,
        )
        return

    if title:
        st.markdown(f"## {title}")

    # En-tête avec compteur animé
    st.markdown(
        f"""
    <div style="background: linear-gradient(135deg, rgba(255, 71, 87, 0.2), rgba(255, 0, 110, 0.2)); 
                padding: 20px; border-radius: 15px; margin-bottom: 25px;
                border: 2px solid rgba(255, 71, 87, 0.4);
                box-shadow: 0 5px 25px rgba(255, 71, 87, 0.3);">
        <p style="margin: 0; font-size: 1.2em; color: #ffffff; font-weight: 700;">
            <strong style="color: #ff4757;">🎯 {len(movies)} film(s) trouvé(s)</strong> 
            correspondant à vos critères
        </p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # Affichage des films avec numérotation
    for idx, movie in enumerate(movies, 1):
        # Normaliser pour l'affichage
        normalized_movie = normalize_movie_data(movie)
        titre = normalized_movie.get("titre", "Titre inconnu")
        annee = normalized_movie.get("annee", "N/A")
        score = normalized_movie.get("score_tmdb", 0)

        # Icône de médaille pour le top 3
        medal = ""
        if idx == 1:
            medal = "🥇"
        elif idx == 2:
            medal = "🥈"
        elif idx == 3:
            medal = "🥉"
        else:
            medal = f"#{idx}"

        # Expander avec titre enrichi
        with st.expander(
            f"{medal} {titre} ({annee}) - ⭐ {score}/10", expanded=(idx == 1)
        ):
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
        st.markdown(
            """
        <div style="background: linear-gradient(135deg, #ff4757 0%, #ff006e 100%); 
                    padding: 25px; border-radius: 20px; text-align: center; margin-bottom: 25px;
                    box-shadow: 0 8px 30px rgba(255, 71, 87, 0.4);">
            <h2 style="margin: 0; color: white; font-weight: 800; text-shadow: 0 2px 10px rgba(0,0,0,0.3);">🔍 Filtres</h2>
            <p style="margin: 5px 0 0 0; color: white; opacity: 0.95; font-size: 1em; font-weight: 600;">
                Affinez votre recherche
            </p>
        </div>
        """,
            unsafe_allow_html=True,
        )

        filters = {}

        # Filtre Réalisateur
        st.markdown(
            """
        <div style="background: rgba(255, 71, 87, 0.2); padding: 12px; border-radius: 15px; margin-bottom: 15px;
                    border: 2px solid rgba(255, 71, 87, 0.4); box-shadow: 0 4px 15px rgba(255, 71, 87, 0.2);">
            <h4 style="margin: 0; color: #ff4757; font-weight: 700;">🎥 Réalisateur</h4>
        </div>
        """,
            unsafe_allow_html=True,
        )

        try:
            response = requests.get(f"{api_url}/list_real", timeout=5)
            if response.status_code == 200:
                data = response.json()
                realisateurs = data.get("directors", [])
                selected_real = st.selectbox(
                    "Choisir un réalisateur",
                    options=["Tous"] + realisateurs,
                    index=0,
                    help="Filtrer les films par réalisateur spécifique",
                )
                if selected_real != "Tous":
                    filters["realisateur"] = selected_real
                    st.success(f"✓ Réalisateur : {selected_real}")
            else:
                st.warning("⚠️ Impossible de charger les réalisateurs")
        except Exception as e:
            st.error(f"❌ Erreur : {e}")

        st.markdown("---")

        # Filtres Genres
        st.markdown(
            """
        <div style="background: rgba(255, 71, 87, 0.2); padding: 12px; border-radius: 15px; margin-bottom: 15px;
                    border: 2px solid rgba(255, 71, 87, 0.4); box-shadow: 0 4px 15px rgba(255, 71, 87, 0.2);">
            <h4 style="margin: 0; color: #ff4757; font-weight: 700;">🎭 Genres</h4>
        </div>
        """,
            unsafe_allow_html=True,
        )

        try:
            response = requests.get(f"{api_url}/list_genre", timeout=5)
            if response.status_code == 200:
                data = response.json()
                genres = data.get("genres", [])

                genres_inclus = st.multiselect(
                    "✅ Genres à conserver",
                    options=genres,
                    default=[],
                    help="Sélectionnez les genres que vous souhaitez voir",
                )
                if genres_inclus:
                    filters["genres_inclus"] = genres_inclus
                    st.success(f"✓ {len(genres_inclus)} genre(s) sélectionné(s)")

                genres_exclus = st.multiselect(
                    "❌ Genres non souhaités",
                    options=genres,
                    default=[],
                    help="Sélectionnez les genres à exclure",
                )
                if genres_exclus:
                    filters["genres_exclus"] = genres_exclus
                    st.info(f"ⓘ {len(genres_exclus)} genre(s) exclu(s)")
            else:
                st.warning("⚠️ Impossible de charger les genres")
        except Exception as e:
            st.error(f"❌ Erreur : {e}")

        st.markdown("---")

        # Filtre Date de sortie
        st.markdown(
            """
        <div style="background: rgba(255, 71, 87, 0.2); padding: 12px; border-radius: 15px; margin-bottom: 15px;
                    border: 2px solid rgba(255, 71, 87, 0.4); box-shadow: 0 4px 15px rgba(255, 71, 87, 0.2);">
            <h4 style="margin: 0; color: #ff4757; font-weight: 700;">📅 Date de sortie</h4>
        </div>
        """,
            unsafe_allow_html=True,
        )

        date_range = st.slider(
            "Plage de dates",
            min_value=1900,
            max_value=2026,
            value=(1980, 2026),
            step=1,
            help="Sélectionnez la période de sortie des films",
        )
        filters["date_sortie_min"] = date_range[0]
        filters["date_sortie_max"] = date_range[1]

        if date_range[0] != 1900 or date_range[1] != 2026:
            st.success(f"✓ Période : {date_range[0]} - {date_range[1]}")

        st.markdown("---")

        # Filtre Score TMDB
        st.markdown(
            """
        <div style="background: rgba(255, 71, 87, 0.2); padding: 12px; border-radius: 15px; margin-bottom: 15px;
                    border: 2px solid rgba(255, 71, 87, 0.4); box-shadow: 0 4px 15px rgba(255, 71, 87, 0.2);">
            <h4 style="margin: 0; color: #ff4757; font-weight: 700;">⭐ Score TMDB</h4>
        </div>
        """,
            unsafe_allow_html=True,
        )

        score_min = st.slider(
            "Score minimum",
            min_value=0.0,
            max_value=10.0,
            value=5.0,
            step=0.5,
            help="Score minimum sur TMDB (The Movie Database)",
        )
        filters["score_tmdb_min"] = score_min

        if score_min > 0:
            st.success(f"✓ Score min : {score_min}/10")

        st.markdown("---")

        # Filtre Durée
        st.markdown(
            """
        <div style="background: rgba(255, 71, 87, 0.2); padding: 12px; border-radius: 15px; margin-bottom: 15px;
                    border: 2px solid rgba(255, 71, 87, 0.4); box-shadow: 0 4px 15px rgba(255, 71, 87, 0.2);">
            <h4 style="margin: 0; color: #ff4757; font-weight: 700;">⏱️ Durée du film</h4>
        </div>
        """,
            unsafe_allow_html=True,
        )

        duree_range = st.slider(
            "Durée en minutes",
            min_value=1,
            max_value=685,
            value=(60, 180),
            step=5,
            help="Sélectionnez la durée minimale et maximale du film",
        )
        filters["duree_min"] = duree_range[0]
        filters["duree_max"] = duree_range[1]

        # Conversion en heures pour affichage
        duree_min_h = (
            f"{duree_range[0] // 60}h{duree_range[0] % 60:02d}"
            if duree_range[0] >= 60
            else f"{duree_range[0]}min"
        )
        duree_max_h = (
            f"{duree_range[1] // 60}h{duree_range[1] % 60:02d}"
            if duree_range[1] >= 60
            else f"{duree_range[1]}min"
        )

        if duree_range[0] != 1 or duree_range[1] != 685:
            st.success(f"✓ Durée : {duree_min_h} - {duree_max_h}")

        st.markdown("---")

        # Résumé des filtres actifs
        nb_filtres = sum(
            [
                1 if filters.get("realisateur") else 0,
                1 if filters.get("genres_inclus") else 0,
                1 if filters.get("genres_exclus") else 0,
                1
                if (
                    filters.get("date_sortie_min") != 1900
                    or filters.get("date_sortie_max") != 2026
                )
                else 0,
                1 if filters.get("score_tmdb_min") > 0 else 0,
                1
                if (filters.get("duree_min") != 1 or filters.get("duree_max") != 685)
                else 0,
            ]
        )

        if nb_filtres > 0:
            st.markdown(
                f"""
            <div style="background: linear-gradient(135deg, #4caf50 0%, #45a049 100%); 
                        padding: 18px; border-radius: 15px; text-align: center; margin-bottom: 15px;
                        box-shadow: 0 5px 25px rgba(76, 175, 80, 0.4);">
                <h4 style="margin: 0; color: white; font-weight: 700;">✓ {nb_filtres} filtre(s) actif(s)</h4>
            </div>
            """,
                unsafe_allow_html=True,
            )
        else:
            st.info("ℹ️ Aucun filtre actif")

        # Bouton reset avec style amélioré
        if st.button("🔄 Réinitialiser tous les filtres", use_container_width=True):
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
    Affiche l'état de réflexion de l'agent ReAct de manière visuelle et intuitive.

    Supporte deux formats :
    1. Format API simple : {"step": str, "status": str}
    2. Format frontend étendu : {"etape": str, "tool": str, "pensee": str, "progression": int, "resultat": any}

    Args:
        status: Dictionnaire contenant l'état actuel de l'agent
    """
    if not status:
        return

    # Container avec style
    st.markdown(
        '<div style="background: rgba(255, 107, 107, 0.05); padding: 15px; border-radius: 10px; margin: 10px 0;">',
        unsafe_allow_html=True,
    )

    # Format API simple
    if "step" in status:
        step_text = status["step"]

        # Déterminer l'icône en fonction de l'étape
        icon = "🤔"
        if "search" in step_text.lower() or "recherche" in step_text.lower():
            icon = "🔍"
        elif "sql" in step_text.lower() or "database" in step_text.lower():
            icon = "💾"
        elif "vector" in step_text.lower() or "similar" in step_text.lower():
            icon = "🧠"
        elif "wiki" in step_text.lower():
            icon = "📚"
        elif "final" in step_text.lower() or "answer" in step_text.lower():
            icon = "✅"

        st.markdown(
            f"""
        <div style="display: flex; align-items: center; gap: 10px;">
            <span style="font-size: 1.5em;">{icon}</span>
            <strong style="color: #ff4757; font-weight: 700;">Étape :</strong>
            <span>{step_text}</span>
        </div>
        """,
            unsafe_allow_html=True,
        )

        if "status" in status:
            status_value = status["status"]
            status_emoji = "✅" if status_value == "success" else "⏳"
            status_color = "#4caf50" if status_value == "success" else "#ff9800"

            st.markdown(
                f"""
            <div style="display: inline-block; background: {status_color}22; 
                        padding: 5px 15px; border-radius: 15px; margin-top: 10px;">
                <strong style="color: {status_color};">{status_emoji} {status_value}</strong>
            </div>
            """,
                unsafe_allow_html=True,
            )

    # Format frontend étendu (rétrocompatibilité)
    if status.get("etape"):
        st.markdown(
            f"""
        <div style="margin: 10px 0;">
            <strong style="color: #ff4757; font-weight: 700;">📍 Étape :</strong> {status["etape"]}
        </div>
        """,
            unsafe_allow_html=True,
        )

    # Tool utilisé
    if status.get("tool"):
        tool = status["tool"]

        # Icône pour chaque outil
        tool_icons = {"sql": "💾", "vector": "🧠", "wiki": "📚", "search": "🔍"}

        tool_icon = "🔧"
        for key, icon in tool_icons.items():
            if key in tool.lower():
                tool_icon = icon
                break

        st.markdown(
            f"""
        <div style="background: rgba(255, 107, 107, 0.1); padding: 10px; 
                    border-radius: 8px; margin: 10px 0; display: inline-block;">
            <strong style="color: #ff4757; font-weight: 700;">{tool_icon} Outil utilisé :</strong> {tool}
        </div>
        """,
            unsafe_allow_html=True,
        )

    # Pensée de l'agent
    if status.get("pensee"):
        st.markdown(
            """
        <div style="background: rgba(100, 149, 237, 0.1); padding: 15px; 
                    border-radius: 10px; margin: 10px 0; border-left: 3px solid #6495ED;">
            <strong style="color: #6495ED;">💭 Réflexion de l'agent :</strong>
        </div>
        """,
            unsafe_allow_html=True,
        )
        st.info(status["pensee"])

    # Progression
    if status.get("progression") is not None:
        progression = status["progression"]

        # Couleur de la barre en fonction de la progression
        if progression < 33:
            color = "#ff4757"
        elif progression < 66:
            color = "#ff9800"
        else:
            color = "#4caf50"

        st.markdown(
            f"""
        <div style="margin: 10px 0;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                <strong style="color: #ff4757; font-weight: 700;">Progression</strong>
                <strong style="color: {color};">{progression}%</strong>
            </div>
            <div style="background: rgba(255, 255, 255, 0.1); height: 10px; border-radius: 10px; overflow: hidden;">
                <div style="background: {color}; width: {progression}%; height: 100%; 
                            transition: width 0.5s ease;"></div>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    # Résultat intermédiaire
    if status.get("resultat"):
        with st.expander("📊 Résultat intermédiaire", expanded=False):
            st.markdown(
                """
            <div style="background: rgba(255, 107, 107, 0.05); padding: 10px; border-radius: 8px;">
            """,
                unsafe_allow_html=True,
            )
            st.json(status["resultat"])
            st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
