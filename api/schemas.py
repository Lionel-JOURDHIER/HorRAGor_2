"""api/schemas.py
Module de définition des schémas de données Pydantic pour l'API HorRAGor.

Ce fichier centralise les modèles de validation (Data Transfer Objects) utilisés
pour sécuriser, typer et documenter les entrées et les sorties de chaque endpoint
de l'API. Il garantit la conformité des échanges entre le front Streamlit et le back.

Modèles de validation inclus :
    - Réponse Film : Modèle sérialisant les détails d'un film pour `/film/{id}`.
    - Réponses Listes : Structures pour les listes de réalisateurs (`/list_réal`) et de genres (`/list_genre`).
    - Requête Chat : Validation du prompt textuel envoyé par l'utilisateur pour `/chat`.
    - Réponses Chat (Streaming/JSON) : Modèles pour suivre l'état d'avancement de la réflexion du LLM,
      le texte final généré, et la structure stricte du top 5 des films recommandés
      (contenant obligatoirement : Réalisateur, Année et Score TMDB).
    - Réponse Wikipédia : Format d'encapsulation du synopsis extrait pour `/wikipedia`.
    - ChatQueryParams / ChatPayload : Structure stricte pour recevoir la demande utilisateur.
      Contient le prompt textuel ET le dictionnaire des filtres du formulaire :
        * realisateur: Optional[str]
        * genres_incluts: List[str]
        * genres_excluts: List[str]
        * date_sortie_min / max: int (1900 à 2026)
        * score_tmdb_min: float (0 à 10)
        * duree_min / max: int (1 à 685)
Dépendances principales :
    - pydantic (BaseModel, Field)
    - typing (Optional, List, Dict)

Auteur/Responsable : Hanna (Epic 3)
"""
