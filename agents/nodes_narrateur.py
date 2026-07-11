"""agents/nodes.py
Module de définition des nœuds (Nodes) du graphe de l'agent LangGraph HorRAGor v3.

Ce fichier contient exclusivement les boîtes blanches applicatives. Chaque nœud reçoit
l'état actuel ('AgentState'), exécute son traitement isolé et retourne les modifications
à fusionner dans l'état global, en respectant scrupuleusement les cibles du router.py.

Nœuds principaux à implémenter :
    - node_classifier : Interroge le LLM avec le prompt de classification pour
      déterminer l'intention de l'utilisateur.
    - node_extractor : Extrait les entités et critères de filtrage (réalisateur, genre).
    - node_sql_query / node_vector_search : Appellent respectivement les outils SQL
      ou FAISS pour récupérer les données de films pertinents.
    - node_wikipedia_enrich : Complète les synopsis manquants si nécessaire.
    - node_rag_synthesizer : Fusionne le contexte, génère la réponse textuelle finale
      et structure le top 5 des films pour le front-end.

Dépendances principales :
    - .state (AgentState)
    - .prompts (Gabarits d'instructions)
    - .tools (sql_tools, vector_tools, wiki_tools)
    - langchain_ollama (Instance locale du LLM)

Auteur/Responsable : Équipe Agents
"""

import sys
from pathlib import Path
from typing import Any, Dict

from langchain_core.messages import HumanMessage, SystemMessage

root_path = Path(__file__).resolve().parent.parent
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))  # pragma: no cover

from agents.config import llm_narrateur
from agents.prompts import (
    NARRATOR_PERSONA_PROMPT,
)
from api.schemas import AgentStep

# LOGGER ------------------------------------------------------
from logger import get_logger, setup_logger

setup_logger()
logger = get_logger("NODES")

# ==============================================================================
# PHASE 5 : NARRATION (LA PLUME GOTHIQUE)
# ==============================================================================


def narrator_node(state: Any) -> Dict[str, Any]:
    """
    Étape finale : L'Écrivain Gothique.
    Isole le LLM de la plomberie technique pour emballer les données brutes,
    les résultats de recherche RAG, ou les messages d'erreur/chitchat
    dans une atmosphère terrifiante et immersive, avec une limite stricte de tokens.
    """
    logger.info("[narrator_node] La plume gothique s'éveille pour l'habillage final.")
    steps = list(getattr(state, "steps", []))

    # 1. Extraction des variables clés de l'état pour la contextualisation
    intent = getattr(state, "intent", "RECHERCHE")
    current_step = getattr(state, "current_step", "")
    data_enriched = getattr(state, "data_enriched", "")
    user_query = getattr(state, "user_query", "")
    retrieved_movies = getattr(state, "retrieved_movies", [])
    last_displayed_movies_id = getattr(state, "last_displayed_movies_id", [])
    logger.info(
        f"[format_cards_node] Chargement de la liste des films affichés : {last_displayed_movies_id}"
    )
    # 2. Construction du contexte de narration selon le cas de redirection

    # Cas A : Court-circuit Chitchat ou Politesse
    if intent == "CHITCHAT":
        logger.info(
            f"[Narrator_node] Le narrateur engage une conversation CHITCHAT avec {user_query}"
        )
        narration_context = (
            f"L'utilisateur engage une conversation légère ou une salutation : '{user_query}'. "
            "Accueille-le ou réponds-lui en restant ancré dans ton manoir poussiéreux, "
            "avec une courtoisie glaciale et une ambiance de crypte."
        )

    # Cas B : Aucun film trouvé au départ ou Échec définitif des filtres/recherches (FAIL)
    elif (
        intent == "AUCUN_FILM_TROUVE"
        or current_step == "invalid_coherence"
        or not retrieved_movies
    ):
        logger.info(
            f"[Narrator_node] Le narrateur engage une conversation AUCUN_FILM_TROUVE avec {user_query}"
        )
        narration_context = (
            f"Le système a échoué à trouver des films correspondant à la demande : '{user_query}'. "
            "Exprime tes profonds regrets avec une mélancolie dramatique. Dis-lui que le brouillard "
            "a englouti les archives ou que les cryptes restent scellées face à cette requête. "
            "Invite-le à reformuler sa demande avant que la bougie ne s'éteigne."
        )

    # Cas C : Fin de la branche RECHERCHE nominale (Cartes prêtes à l'envoi)
    elif current_step in ["card_ready", "cards_ready"]:
        titles = [getattr(f, "title", "Film inconnu") for f in retrieved_movies]
        logger.info(
            f"[Narrator_node] Le narrateur engage une conversation RECHERCHE parlant de {titles}"
        )
        narration_context = (
            f"La recherche RAG a extrait avec succès le(s) film(s) suivant(s) : {titles}.\n"
            "Ces films vont être affichés sous forme de parchemins/cartes à l'écran. "
            f"La requête initiale était : '{user_query}'.\n"
            "Rédige une introduction ou une transition narrative sombre et théâtrale pour présenter "
            "ces reliques cinématographiques à l'utilisateur. Ne liste pas manuellement tous les détails "
            "des films car les cartes s'en chargent, mais prépare psychologiquement l'utilisateur à les découvrir."
        )

    # Cas D : Clôture nominale d'une DISCUSSION (Bypass ou après synthèse)
    else:
        # Création d'un résumé structuré des films pour le contexte du narrateur

        logger.info(
            f"[Narrator_node] Le narrateur engage une conversation DISCUSSION l:\n"
            f"--- SYNTHÈSE ADDITIONNELLE ---\n{data_enriched}\n------------------\n"
            f"Question de l'interlocuteur : '{user_query}'.\n"
        )

        # LE CORRECTIF : Si aucune synthèse n'est fournie, on la génère nous-mêmes
        if not data_enriched and getattr(state, "retrieved_movies", None):
            fallback_details = []
            for film in state.retrieved_movies:
                # Extraction sécurisée des attributs (selon votre MockFilmDetail)
                film_detail = (
                    f"Titre : {getattr(film, 'title', 'Non disponible')}\n"
                    f"Réalisateur : {getattr(film, 'director', getattr(film, 'realisateur', 'Non disponible'))}\n"
                    f"Date de sortie : {getattr(film, 'release_date', 'Non disponible')}\n"
                    f"Genres : {', '.join(film.genres) if getattr(film, 'genres', None) else 'Non disponible'}\n"
                    f"Synopsis : {getattr(film, 'synopsis', None) or 'Non disponible'}\n"
                    f"Score TMDB : {getattr(film, 'tmdb_score', 'Non disponible')}\n"
                    f"Score IMDb : {getattr(film, 'imdb_score', 'Non disponible')}\n"
                    f"Score RT : {getattr(film, 'rotten_tomatometer', 'Non disponible')}\n"
                    f"Durée : {getattr(film, 'runtime', 'Non disponible')} min\n"
                    f"Collection : {getattr(film, 'collection', 'Non disponible')}\n"
                    f"Tagline : {getattr(film, 'tagline', 'Non disponible')}\n"
                )
                fallback_details.append(film_detail)
            data_enriched = "\n".join(fallback_details)

        narration_context = (
            f"Réponse factuelle à transmettre : {data_enriched}\n\n"
            f"Question : '{user_query}'.\n"
            "Transmets cette réponse précise dans ton style gothique. "
            "Ne modifie aucun fait. Maximum 2 phrases."
        )

    # 3. Préparation du Prompt Système avec le gabarit importé
    gothic_prompt = NARRATOR_PERSONA_PROMPT.replace(
        "__NARRATION_CONTEXT__", narration_context
    )

    # 4. Invocation du modèle de narration configuré
    try:
        response = llm_narrateur.invoke(
            [SystemMessage(content=gothic_prompt), HumanMessage(content=user_query)]
        )
        final_narrative = response.content
        # NETTOYAGE : Suppression des balises si elles sont présentes
        final_narrative = (
            final_narrative.replace("<reponse_gothique>", "")
            .replace("</reponse_gothique>", "")
            .strip()
        )

        status = "Narration gothique générée avec succès et nettoyée."
        logger.info(f"[narrator_node] {status}")
    except Exception as e:
        logger.error(
            f"[narrator_node] Échec de la plume gothique : {e}. Fallback textuel."
        )
        final_narrative = (
            data_enriched or "Le silence des tombes s'abat sur votre demande..."
        )
        status = "Échec narrator_node — Fallback textuel appliqué."

    # Enregistrement de l'étape
    # Assurez-vous que la classe AgentStep correspond bien à ce qui est défini dans votre state.py
    steps.append(AgentStep(step="narrator", status=status))

    # # 5. Mise à jour de la mémoire de session (front-end)
    # last_displayed = (
    #     [
    #         getattr(f, "tmdb_id", None)
    #         for f in retrieved_movies
    #         if getattr(f, "tmdb_id", None)
    #     ]
    #     if retrieved_movies
    #     else last_displayed_movies_id
    # )
    logger.info(f"[narrator_node] Réussite de la génération : {final_narrative}")
    return {
        "answer": final_narrative,
        "current_step": "completed",
        "last_displayed_movies_id": last_displayed_movies_id,
        "retrieved_movies": retrieved_movies,
        "steps": steps,
    }
