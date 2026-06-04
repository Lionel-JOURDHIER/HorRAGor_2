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


def init_session_state():
    """Initialise les variables de session Streamlit."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    if "api_status" not in st.session_state:
        st.session_state.api_status = None


def display_header():
    """Affiche l'en-tête de l'application."""
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.title("🎬 HorRAGor")
        st.markdown("### *Votre guide intelligent dans l'univers de l'horreur*")
        st.markdown("---")


def check_api_status():
    """Vérifie et affiche le statut de l'API."""
    status = check_health()
    
    if status.get("status") == "error":
        st.error("⚠️ L'API n'est pas accessible. Vérifiez que le serveur FastAPI est démarré.")
        st.info(f"URL de l'API : {get_api_url()}")
        st.stop()
    else:
        with st.sidebar:
            st.success("✅ API connectée")


def display_chat_interface(filters: dict):
    """
    Affiche l'interface de chat principale.
    
    Args:
        filters: Dictionnaire des filtres sélectionnés dans la sidebar
    """
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
                display_movie_list(message["films"], title="🎬 Films recommandés")
    
    # Input utilisateur
    user_input = st.chat_input("Posez votre question sur les films d'horreur...")
    
    if user_input:
        # Ajouter le message utilisateur
        st.session_state.messages.append({
            "role": "user",
            "content": user_input
        })
        display_chat_message("user", user_input, avatar="👤")
        
        # Afficher l'indicateur de chargement
        with st.spinner("🧠 L'agent HorRAGor réfléchit..."):
            # Conteneur pour les états de l'agent
            status_container = st.empty()
            
            # Afficher un message de statut
            with status_container:
                st.info("🔍 Analyse de votre requête en cours...")
            
            # Envoyer la requête à l'API
            response = send_chat_query(user_input, filters)
            
            # Effacer le conteneur de statut
            status_container.empty()
        
        # Traiter la réponse
        if response.get("status") == "error":
            error_msg = response.get("message_erreur", "Une erreur s'est produite")
            st.error(f"❌ {error_msg}")
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"Désolé, une erreur s'est produite : {error_msg}"
            })
        else:
            # Afficher la réponse texte du LLM
            reponse_texte = response.get("reponse_texte", "Aucune réponse générée")
            display_chat_message("assistant", reponse_texte, avatar="🤖")
            
            # Afficher les états de l'agent si disponibles
            if "etats_agent" in response and response["etats_agent"]:
                with st.expander("🔍 Détails de réflexion de l'agent"):
                    for idx, etat in enumerate(response["etats_agent"], 1):
                        st.markdown(f"**Étape {idx}:**")
                        display_agent_status(etat)
                        st.markdown("---")
            
            # Récupérer et afficher les films recommandés
            films = response.get("films_recommandes", [])
            
            # Ajouter le message assistant avec les films
            st.session_state.messages.append({
                "role": "assistant",
                "content": reponse_texte,
                "films": films
            })
            
            # Afficher les films
            if films:
                display_movie_list(films, title="🎬 Films recommandés")
            
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
    
    # Afficher les filtres actifs dans la sidebar
    with st.sidebar:
        st.markdown("---")
        st.subheader("📋 Filtres actifs")
        if filters:
            for key, value in filters.items():
                st.caption(f"**{key}:** {value}")
        else:
            st.caption("Aucun filtre actif")
    
    # Interface de chat principale
    st.markdown("## 💬 Chat")
    st.markdown("*Posez vos questions sur les films d'horreur et recevez des recommandations personnalisées*")
    
    display_chat_interface(filters)
    
    # Section d'aide en bas de page
    with st.expander("ℹ️ Comment utiliser HorRAGor ?"):
        st.markdown("""
        ### Guide d'utilisation
        
        1. **Utilisez les filtres** dans la barre latérale pour affiner vos préférences
        2. **Posez votre question** dans la zone de chat
        3. **L'agent ReAct** analysera votre demande et utilisera les outils appropriés :
           - 🔍 Recherche SQL pour les métadonnées
           - 🧠 Recherche vectorielle pour les films similaires
           - 📚 Wikipedia pour enrichir les informations
        4. **Recevez des recommandations** personnalisées avec détails
        
        ### Exemples de questions
        - "Recommande-moi des films d'horreur psychologique des années 80"
        - "Quels sont les meilleurs films de John Carpenter ?"
        - "Je cherche des films similaires à The Shining"
        - "Montre-moi des films d'horreur japonais bien notés"
        """)
    
    # Footer
    st.markdown("---")
    st.caption("HorRAGor - Propulsé par LangGraph, FastAPI et Streamlit | Projet Simplon 2026")


if __name__ == "__main__":
    main()

