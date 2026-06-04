"""app/app.py
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
"""
