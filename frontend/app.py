"""frontend/app.py
Application Web Front-End Streamlit - Interface Utilisateur de HorRAGor.

Ce module est le point d'entrée de l'interface graphique conçue par Flavie.

Fonctionnalités principales :
    - Formulaire de Préférences Globales : Implémente les sélections physiques
      pour enrichir toutes les demandes :
        * Sélecteur du Réalisateur (alimenté par '/list_réal').
        * Double sélecteur de Genres : "Genres à conserver" et "Genres non souhaités" (via '/list_genre').
        * Sliders de filtres : Double slide date de sortie (1900-2026), Simple slide score TMDB (0-10),
          et Double slide durée du film (1-685 min).
    - Interface de Chat & Streaming : Envoie conjointement le texte du prompt et les filtres
      du formulaire à l'endpoint `/chat`, puis affiche l'état de réflexion, la carte d'identité du film et le Top 5 final.

Dépendances principales :
    - streamlit (st.sidebar, st.slider, st.multiselect, st.chat_input)
    - requests

Auteur : Flavie (Epic 7)
"""

import streamlit as st
from utils.api_client import (
    get_api_url,
    check_health,
    send_chat_query,
    get_film_by_id
)
from components.components import (
    create_filters_sidebar,
    display_chat_message,
    display_movie_card,
    display_movie_list,
    display_agent_status
)


# Configuration de la page
st.set_page_config(
    page_title="HorRAGor - Chatbot d'Horreur",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personnalisé pour un design moderne et contrasté
st.markdown("""
<style>
    /* Import des polices Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700;800&display=swap');
    
    /* Style principal avec dégradé dynamique */
    .main {
        background: linear-gradient(135deg, #0a0e27 0%, #1a0b2e 50%, #16003b 100%);
        font-family: 'Poppins', sans-serif;
    }
    
    /* Override Streamlit default background */
    .stApp {
        background: linear-gradient(135deg, #0a0e27 0%, #1a0b2e 50%, #16003b 100%);
    }
    
    /* En-tête stylisé avec animation */
    .stTitle {
        color: #ff4757;
        text-align: center;
        font-weight: 800;
        text-shadow: 0 0 20px rgba(255, 71, 87, 0.5), 0 0 40px rgba(255, 71, 87, 0.3);
        animation: glow 2s ease-in-out infinite alternate;
    }
    
    @keyframes glow {
        from {
            text-shadow: 0 0 20px rgba(255, 71, 87, 0.5), 0 0 40px rgba(255, 71, 87, 0.3);
        }
        to {
            text-shadow: 0 0 30px rgba(255, 71, 87, 0.8), 0 0 60px rgba(255, 71, 87, 0.5);
        }
    }
    
    /* Messages du chat avec néon */
    .stChatMessage {
        background: rgba(26, 11, 46, 0.8);
        border-radius: 20px;
        padding: 20px;
        margin: 15px 0;
        border-left: 5px solid #ff4757;
        border-right: 1px solid rgba(255, 71, 87, 0.3);
        backdrop-filter: blur(15px);
        box-shadow: 0 8px 32px rgba(255, 71, 87, 0.2);
    }
    
    /* Cartes de films avec effet néon */
    .movie-card {
        background: linear-gradient(135deg, #1a0b2e 0%, #0a0e27 100%);
        border-radius: 25px;
        padding: 25px;
        margin: 20px 0;
        box-shadow: 0 10px 40px rgba(255, 71, 87, 0.3), 
                    inset 0 0 30px rgba(255, 71, 87, 0.05);
        border: 2px solid rgba(255, 71, 87, 0.5);
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    }
    
    .movie-card:hover {
        transform: translateY(-10px) scale(1.02);
        box-shadow: 0 20px 60px rgba(255, 71, 87, 0.6),
                    inset 0 0 50px rgba(255, 71, 87, 0.1);
        border-color: #ff4757;
    }
    
    /* Statistiques avec effet gradient animé */
    .stat-box {
        background: linear-gradient(135deg, #ff4757 0%, #ee5a6f 50%, #ff006e 100%);
        border-radius: 20px;
        padding: 25px;
        text-align: center;
        color: white;
        box-shadow: 0 8px 30px rgba(255, 71, 87, 0.4),
                    0 0 50px rgba(255, 71, 87, 0.2);
        margin: 10px;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    
    .stat-box::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: linear-gradient(
            45deg,
            transparent 30%,
            rgba(255, 255, 255, 0.1) 50%,
            transparent 70%
        );
        transform: rotate(45deg);
        animation: shine 3s infinite;
    }
    
    @keyframes shine {
        0% { transform: rotate(45deg) translateY(-100%); }
        100% { transform: rotate(45deg) translateY(100%); }
    }
    
    .stat-box:hover {
        transform: translateY(-5px) scale(1.05);
        box-shadow: 0 15px 50px rgba(255, 71, 87, 0.6),
                    0 0 80px rgba(255, 71, 87, 0.3);
    }
    
    /* Sidebar avec effet verre */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, rgba(26, 11, 46, 0.95) 0%, rgba(10, 14, 39, 0.95) 100%);
        backdrop-filter: blur(20px);
        border-right: 2px solid rgba(255, 71, 87, 0.3);
    }
    
    /* Boutons avec effet néon */
    .stButton>button {
        background: linear-gradient(135deg, #ff4757 0%, #ff006e 100%);
        color: white;
        border-radius: 15px;
        border: 2px solid rgba(255, 71, 87, 0.5);
        padding: 12px 30px;
        font-weight: 700;
        font-size: 1.1em;
        transition: all 0.3s ease;
        box-shadow: 0 5px 25px rgba(255, 71, 87, 0.4);
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .stButton>button:hover {
        transform: translateY(-3px) scale(1.05);
        box-shadow: 0 10px 40px rgba(255, 71, 87, 0.6),
                    0 0 30px rgba(255, 71, 87, 0.5);
        background: linear-gradient(135deg, #ff006e 0%, #ff4757 100%);
        border-color: #ff4757;
    }
    
    /* Sliders avec couleurs vives */
    .stSlider {
        padding: 15px 0;
    }
    
    .stSlider > div > div > div > div {
        background: linear-gradient(90deg, #ff4757 0%, #ff006e 100%);
    }
    
    /* Expanders avec effet néon */
    .streamlit-expanderHeader {
        background: rgba(255, 71, 87, 0.15);
        border-radius: 15px;
        font-weight: 700;
        border: 2px solid rgba(255, 71, 87, 0.3);
        padding: 15px;
        transition: all 0.3s ease;
    }
    
    .streamlit-expanderHeader:hover {
        background: rgba(255, 71, 87, 0.25);
        border-color: #ff4757;
        box-shadow: 0 5px 20px rgba(255, 71, 87, 0.3);
    }
    
    /* Input de chat avec effet brillant */
    .stChatInput {
        background: rgba(26, 11, 46, 0.8);
        border: 2px solid rgba(255, 71, 87, 0.5);
        border-radius: 15px;
        box-shadow: 0 5px 25px rgba(255, 71, 87, 0.2);
    }
    
    /* Texte amélioré */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Poppins', sans-serif;
        color: #ffffff;
    }
    
    p, span, div {
        font-family: 'Poppins', sans-serif;
    }
    
    /* Amélioration de la lisibilité */
    .stMarkdown {
        color: #ffffff;
    }
    
    /* Success/Error/Warning messages */
    .stSuccess {
        background: rgba(76, 175, 80, 0.2);
        border: 2px solid #4caf50;
        border-radius: 15px;
        box-shadow: 0 5px 20px rgba(76, 175, 80, 0.3);
    }
    
    .stError {
        background: rgba(244, 67, 54, 0.2);
        border: 2px solid #f44336;
        border-radius: 15px;
        box-shadow: 0 5px 20px rgba(244, 67, 54, 0.3);
    }
    
    .stWarning {
        background: rgba(255, 152, 0, 0.2);
        border: 2px solid #ff9800;
        border-radius: 15px;
        box-shadow: 0 5px 20px rgba(255, 152, 0, 0.3);
    }
    
    .stInfo {
        background: rgba(33, 150, 243, 0.2);
        border: 2px solid #2196f3;
        border-radius: 15px;
        box-shadow: 0 5px 20px rgba(33, 150, 243, 0.3);
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """Initialise les variables de session Streamlit."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    if "api_status" not in st.session_state:
        st.session_state.api_status = None
    
    if "total_queries" not in st.session_state:
        st.session_state.total_queries = 0
    
    if "total_films_recommended" not in st.session_state:
        st.session_state.total_films_recommended = 0
    
    if "last_query_time" not in st.session_state:
        st.session_state.last_query_time = None
    
    if "favorite_genre" not in st.session_state:
        st.session_state.favorite_genre = None
    
    if "preset_question" not in st.session_state:
        st.session_state.preset_question = None


def display_header():
    """Affiche l'en-tête de l'application avec statistiques."""
    # En-tête principal
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<h1 style="text-align: center; color: #ff4757; font-size: 4.5em; margin-bottom: 0; font-weight: 900; text-shadow: 0 0 25px rgba(255, 71, 87, 0.6);">🎬 HorRAGor</h1>', unsafe_allow_html=True)
        st.markdown('<h3 style="text-align: center; color: #ffffff; opacity: 0.95; font-weight: 600; text-shadow: 0 2px 10px rgba(0,0,0,0.5);">Votre guide intelligent dans l\'univers de l\'horreur</h3>', unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Statistiques en temps réel
    stats_col1, stats_col2, stats_col3, stats_col4 = st.columns(4)
    
    with stats_col1:
        st.markdown(f"""
        <div class="stat-box">
            <h2 style="margin: 0; font-size: 2.5em;">💬</h2>
            <h3 style="margin: 5px 0;">{st.session_state.total_queries}</h3>
            <p style="margin: 0; opacity: 0.8; font-size: 0.9em;">Requêtes</p>
        </div>
        """, unsafe_allow_html=True)
    
    with stats_col2:
        st.markdown(f"""
        <div class="stat-box">
            <h2 style="margin: 0; font-size: 2.5em;">🎥</h2>
            <h3 style="margin: 5px 0;">{st.session_state.total_films_recommended}</h3>
            <p style="margin: 0; opacity: 0.8; font-size: 0.9em;">Films recommandés</p>
        </div>
        """, unsafe_allow_html=True)
    
    with stats_col3:
        last_time = "Jamais"
        if st.session_state.last_query_time:
            import datetime
            now = datetime.datetime.now()
            delta = now - st.session_state.last_query_time
            if delta.seconds < 60:
                last_time = "À l'instant"
            elif delta.seconds < 3600:
                last_time = f"Il y a {delta.seconds // 60}min"
            else:
                last_time = f"Il y a {delta.seconds // 3600}h"
        
        st.markdown(f"""
        <div class="stat-box">
            <h2 style="margin: 0; font-size: 2.5em;">⏱️</h2>
            <h3 style="margin: 5px 0; font-size: 1.2em;">{last_time}</h3>
            <p style="margin: 0; opacity: 0.8; font-size: 0.9em;">Dernière requête</p>
        </div>
        """, unsafe_allow_html=True)
    
    with stats_col4:
        api_status = "✅ En ligne" if st.session_state.api_status else "⚠️ Hors ligne"
        status_color = "#4caf50" if st.session_state.api_status else "#ff9800"
        
        st.markdown(f"""
        <div class="stat-box" style="background: {status_color};">
            <h2 style="margin: 0; font-size: 2.5em;">🔌</h2>
            <h3 style="margin: 5px 0; font-size: 1.2em;">{api_status}</h3>
            <p style="margin: 0; opacity: 0.8; font-size: 0.9em;">Statut API</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")


def check_api_status():
    """Vérifie et affiche le statut de l'API."""
    status = check_health()
    
    if status.get("status") == "error":
        st.session_state.api_status = False
        st.error("⚠️ L'API n'est pas accessible. Vérifiez que le serveur FastAPI est démarré.")
        st.info(f"URL de l'API : {get_api_url()}")
        
        with st.expander("🔧 Instructions de démarrage"):
            st.code("""
# Dans un terminal, lancez l'API :
cd api
uvicorn main:app --reload

# Ou avec Docker :
docker-compose up
            """, language="bash")
        st.stop()
    else:
        st.session_state.api_status = True
        with st.sidebar:
            st.success("✅ API connectée")
            st.caption(f"🌐 {get_api_url()}")


def display_chat_interface(filters: dict):
    """
    Affiche l'interface de chat principale.
    
    Args:
        filters: Dictionnaire des filtres sélectionnés dans la sidebar
    """
    # Vérifier si une question préenregistrée a été cliquée
    process_preset_question = False
    if "preset_question" in st.session_state and st.session_state.preset_question:
        user_input_preset = st.session_state.preset_question
        st.session_state.preset_question = None
        process_preset_question = True
    
    # Afficher l'historique des messages
    for message in st.session_state.messages:
        role = message["role"]
        content = message["content"]
        
        if role == "user":
            display_chat_message("user", content, avatar="👤")
        else:
            display_chat_message("assistant", content, avatar="🤖")
            
            # Afficher les films si disponibles
            if "films" in message and message["films"]:
                display_movie_list(message["films"], title="")
    
    # Input utilisateur
    user_input = st.chat_input("💬 Posez votre question sur les films d'horreur...")
    
    # Traiter la question (qu'elle soit préenregistrée ou saisie)
    if user_input or process_preset_question:
        import datetime
        import time
        
        # Utiliser la question préenregistrée si disponible
        if process_preset_question:
            user_input = user_input_preset
        
        # Mettre à jour les statistiques
        st.session_state.total_queries += 1
        st.session_state.last_query_time = datetime.datetime.now()
        
        # Ajouter le message utilisateur
        st.session_state.messages.append({
            "role": "user",
            "content": user_input
        })
        display_chat_message("user", user_input, avatar="👤")
        
        # Afficher l'indicateur de chargement avec animation
        with st.spinner("🧠 L'agent HorRAGor réfléchit..."):
            # Conteneur pour les états de l'agent
            status_container = st.empty()
            progress_bar = st.progress(0)
            
            # Animation de progression
            with status_container:
                st.markdown("""
                <div style="background: linear-gradient(135deg, rgba(255, 71, 87, 0.2), rgba(255, 0, 110, 0.2)); 
                            padding: 25px; border-radius: 20px; border-left: 5px solid #ff4757;
                            box-shadow: 0 8px 30px rgba(255, 71, 87, 0.3);">
                    <h4 style="margin: 0; color: #ff4757; font-weight: 800; font-size: 1.3em;">🔍 Analyse en cours...</h4>
                    <p style="margin: 8px 0 0 0; opacity: 0.9; color: #ffffff; font-weight: 600;">L'agent analyse votre requête et recherche les meilleurs films</p>
                </div>
                """, unsafe_allow_html=True)
            
            # Simuler une progression
            for i in range(0, 30, 10):
                progress_bar.progress(i)
                time.sleep(0.1)
            
            # Envoyer la requête à l'API
            response = send_chat_query(user_input, filters)
            
            # Compléter la progression
            progress_bar.progress(100)
            time.sleep(0.2)
            
            # Effacer les conteneurs de statut
            status_container.empty()
            progress_bar.empty()
        
        # Traiter la réponse
        if response.get("status") == "error":
            error_msg = response.get("message_erreur", "Une erreur s'est produite")
            st.error(f"❌ {error_msg}")
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"Désolé, une erreur s'est produite : {error_msg}"
            })
        else:
            # Afficher la réponse texte du LLM avec animation
            reponse_texte = response.get("reponse_texte", "Aucune réponse générée")
            
            # Message de succès avec animation
            st.success("✅ Réponse générée avec succès !")
            
            display_chat_message("assistant", reponse_texte, avatar="🤖")
            
            # Afficher les états de l'agent si disponibles avec design amélioré
            if "etats_agent" in response and response["etats_agent"]:
                with st.expander("🔍 Détails de réflexion de l'agent (cliquez pour voir)", expanded=False):
                    st.markdown("""
                    <div style="background: linear-gradient(135deg, rgba(255, 71, 87, 0.15), rgba(255, 0, 110, 0.15)); 
                                padding: 20px; border-radius: 15px; margin-bottom: 20px;
                                border: 2px solid rgba(255, 71, 87, 0.3);">
                        <h4 style="margin: 0; color: #ff4757; font-weight: 800;">📊 Processus de réflexion de l'agent</h4>
                        <p style="margin: 8px 0 0 0; opacity: 0.9; color: #ffffff; font-weight: 600;">Découvrez comment l'agent a traité votre requête</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    for idx, etat in enumerate(response["etats_agent"], 1):
                        st.markdown(f"""
                        <div style="background: rgba(255, 71, 87, 0.1); padding: 18px; border-radius: 15px; margin: 15px 0; 
                                    border-left: 4px solid #ff4757; box-shadow: 0 4px 15px rgba(255, 71, 87, 0.2);">
                            <h5 style="margin: 0; color: #ff4757; font-weight: 700;">Étape {idx}</h5>
                        </div>
                        """, unsafe_allow_html=True)
                        display_agent_status(etat)
            
            # Récupérer et afficher les films recommandés
            films = response.get("films_recommandes", [])
            
            # Mettre à jour les statistiques
            st.session_state.total_films_recommended += len(films)
            
            # Ajouter le message assistant avec les films
            st.session_state.messages.append({
                "role": "assistant",
                "content": reponse_texte,
                "films": films
            })
            
            # Afficher les films avec compteur
            if films:
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #ff4757 0%, #ff006e 100%); 
                            padding: 25px; border-radius: 20px; margin: 25px 0; text-align: center;
                            box-shadow: 0 10px 40px rgba(255, 71, 87, 0.5);">
                    <h2 style="margin: 0; color: white; font-weight: 800; font-size: 2em;">🎬 {len(films)} Film(s) recommandé(s)</h2>
                    <p style="margin: 8px 0 0 0; color: white; opacity: 0.95; font-size: 1.1em; font-weight: 600;">Sélectionnés spécialement pour vous</p>
                </div>
                """, unsafe_allow_html=True)
                display_movie_list(films, title="")
            else:
                st.info("ℹ️ Aucun film ne correspond à vos critères. Essayez de modifier les filtres.")
            
            # Forcer le rafraîchissement pour afficher immédiatement
            st.rerun()


def main():
    """Fonction principale de l'application."""
    # Initialisation
    init_session_state()
    
    # En-tête
    display_header()
    
    # Vérification de l'API
    check_api_status()
    
    # Barre latérale avec filtres
    api_url = get_api_url()
    filters = create_filters_sidebar(api_url)
    
    # Interface de chat principale
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(255, 71, 87, 0.15), rgba(255, 0, 110, 0.15)); 
                padding: 25px; border-radius: 20px; margin: 25px 0;
                border: 2px solid rgba(255, 71, 87, 0.3); box-shadow: 0 5px 25px rgba(255, 71, 87, 0.3);">
        <h2 style="margin: 0; color: #ff4757; font-weight: 800;">💬 Chat Intelligent</h2>
        <p style="margin: 12px 0 0 0; opacity: 0.95; color: #ffffff; font-weight: 600;">
            Posez vos questions sur les films d'horreur et recevez des recommandations personnalisées
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Suggestions de questions si aucun message
    if not st.session_state.messages:
        st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(255, 71, 87, 0.2) 0%, rgba(255, 0, 110, 0.2) 100%); 
                    padding: 25px; border-radius: 20px; margin: 25px 0;
                    border: 2px solid rgba(255, 71, 87, 0.3);">
            <h4 style="color: #ff4757; margin-bottom: 18px; font-weight: 800;">💡 Exemples de questions :</h4>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🎭 Films d'horreur psychologique des années 80", use_container_width=True):
                st.session_state.preset_question = "Recommande-moi des films d'horreur psychologique des années 80"
                st.rerun()
            
            if st.button("🎬 Meilleurs films de John Carpenter", use_container_width=True):
                st.session_state.preset_question = "Quels sont les meilleurs films de John Carpenter ?"
                st.rerun()
        
        with col2:
            if st.button("👻 Films similaires à The Shining", use_container_width=True):
                st.session_state.preset_question = "Je cherche des films similaires à The Shining"
                st.rerun()
            
            if st.button("🇯🇵 Films d'horreur japonais bien notés", use_container_width=True):
                st.session_state.preset_question = "Montre-moi des films d'horreur japonais bien notés"
                st.rerun()
        
        st.markdown("<br>", unsafe_allow_html=True)
    
    display_chat_interface(filters)
    
    # Section d'aide en bas de page
    with st.expander("ℹ️ Comment utiliser HorRAGor ?", expanded=False):
        st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(255, 71, 87, 0.1), rgba(255, 0, 110, 0.1)); 
                    padding: 25px; border-radius: 15px;">
            <h3 style="color: #ff4757; font-weight: 800;">📖 Guide d'utilisation</h3>
            
            <div style="margin: 20px 0;">
                <h4 style="color: #ff4757; font-weight: 700;">1️⃣ Configurez vos filtres</h4>
                <p style="color: #ffffff; font-weight: 500;">Utilisez la barre latérale pour affiner vos préférences :</p>
                <ul style="color: #ffffff;">
                    <li><strong>Réalisateur</strong> : Sélectionnez votre réalisateur préféré</li>
                    <li><strong>Genres</strong> : Choisissez les genres à inclure ou exclure</li>
                    <li><strong>Date</strong> : Définissez la période de sortie</li>
                    <li><strong>Score</strong> : Fixez un score minimum sur TMDB</li>
                    <li><strong>Durée</strong> : Sélectionnez la durée souhaitée</li>
                </ul>
            </div>
            
            <div style="margin: 20px 0;">
                <h4 style="color: #ff4757; font-weight: 700;">2️⃣ Posez votre question</h4>
                <p style="color: #ffffff; font-weight: 500;">Dans la zone de chat, décrivez ce que vous recherchez. L'agent comprend :</p>
                <ul style="color: #ffffff;">
                    <li>Les demandes de recommandations spécifiques</li>
                    <li>Les recherches par réalisateur ou acteur</li>
                    <li>Les demandes de films similaires</li>
                    <li>Les questions sur les caractéristiques des films</li>
                </ul>
            </div>
            
            <div style="margin: 20px 0;">
                <h4 style="color: #ff4757; font-weight: 700;">3️⃣ L'agent ReAct travaille pour vous</h4>
                <p style="color: #ffffff; font-weight: 500;">L'agent utilise plusieurs outils intelligents :</p>
                <ul style="color: #ffffff;">
                    <li><strong>🔍 Recherche SQL</strong> : Pour filtrer par métadonnées</li>
                    <li><strong>🧠 Recherche vectorielle</strong> : Pour trouver des films similaires</li>
                    <li><strong>📚 Wikipedia</strong> : Pour enrichir les informations</li>
                </ul>
            </div>
            
            <div style="margin: 20px 0;">
                <h4 style="color: #ff4757; font-weight: 700;">4️⃣ Recevez vos recommandations</h4>
                <p style="color: #ffffff; font-weight: 500;">L'agent vous présente :</p>
                <ul style="color: #ffffff;">
                    <li>Une réponse détaillée et personnalisée</li>
                    <li>Les étapes de sa réflexion (optionnel)</li>
                    <li>Une liste de films recommandés avec toutes les infos</li>
                </ul>
            </div>
            
            <div style="background: linear-gradient(135deg, #ff4757 0%, #ff006e 100%); 
                        padding: 20px; border-radius: 15px; color: white; margin-top: 20px;
                        box-shadow: 0 5px 25px rgba(255, 71, 87, 0.4);">
                <h4 style="margin: 0; font-weight: 800;">💡 Astuce</h4>
                <p style="margin: 12px 0 0 0; font-weight: 600;">
                    Plus votre question est précise et vos filtres définis, 
                    plus les recommandations seront pertinentes !
                </p>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Footer
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.caption("🤖 Propulsé par LangGraph")
    
    with col2:
        st.caption("⚡ API FastAPI")
    
    with col3:
        st.caption("🎨 Interface Streamlit")
    
    st.markdown("""
    <div style="text-align: center; padding: 20px; opacity: 0.6;">
        <p>HorRAGor - Projet Simplon 2026</p>
        <p style="font-size: 0.8em;">Votre guide intelligent dans l'univers de l'horreur</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()

