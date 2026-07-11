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
from typing import Any, Dict, List, Literal, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, Field

root_path = Path(__file__).resolve().parent.parent
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))  # pragma: no cover

from agents.config import llm, structured_llm
from agents.prompts import (
    INTENTION_PROMPT,
    ROUTER_PROMPT,
    TITLE_DETECTOR_PROMPT,
)
from agents.tools.sql_tools import filter_films_by_criteria, get_films_details_by_ids
from agents.tools.vector_tools import search_vector_catalog
from api.schemas import AgentState, AgentStep, ChatFilters
from database.connection import db_session
from database.queries import get_films_short_by_ids

# LOGGER ------------------------------------------------------
from logger import get_logger, setup_logger

setup_logger()
logger = get_logger("NODES")

BASE_DIR = Path(__file__).resolve().parent.parent
FAISS_INDEX_PATH = str(BASE_DIR / "data" / "faiss_index")
CATALOG_GENRES = {
    "Action",
    "Adventure",
    "Animation",
    "Comedy",
    "Crime",
    "Documentary",
    "Drama",
    "Family",
    "Fantasy",
    "History",
    "Horror",
    "Music",
    "Mystery",
    "Romance",
    "Science Fiction",
    "Thriller",
    "TV Movie",
    "War",
    "Western",
}


class ValidationFilmListResult(BaseModel):
    valid_titles: List[str] = Field(
        description="Titres des films qui correspondent aux critères demandés."
    )
    invalid_titles: List[str] = Field(
        description="Titres des films qui ne correspondent PAS aux critères."
    )
    feedback: str = Field(description="Explication concise du choix de validation.")


class ValidationResult(BaseModel):
    is_relevant: bool = Field(
        description="True si le résultat est cohérent avec la demande."
    )
    has_missing_info: bool = Field(
        description="True si la réponse est globalement bonne mais qu'un élément crucial comme le résumé/synopsis est manquant ou vide."
    )
    feedback: str = Field(
        description="Explication concise du choix de validation ou de ce qui fait défaut."
    )
    corrected_title: Optional[str] = Field(
        default=None,
        description=(
            "Si tu identifies avec certitude le titre exact du film qui aurait dû être "
            "recherché pour répondre à la requête utilisateur, indique-le ici précisément "
            "(ex: 'The Shining'). Laisse vide si tu n'as pas de certitude suffisante."
        ),
    )


class FilmDataCheck(BaseModel):
    sujet: str = Field(
        description="Le sujet précis de la question : synopsis, réalisateur, score, budget, casting, année, collection, etc."
    )
    films_ok: List[str] = Field(
        description="Titres des films pour lesquels la donnée demandée est présente et non vide."
    )
    films_missing: List[str] = Field(
        description="Titres des films pour lesquels la donnée demandée est absente ou vide — nécessitent un enrichissement Wikipedia."
    )
    feedback: str = Field(
        description="Explication concise de ce qui est disponible ou manquant."
    )


class IntentOutput(BaseModel):
    intent: Literal["RECHERCHE", "DISCUSSION", "CHITCHAT", "AUCUN_FILM_TROUVE"] = Field(
        description="L'intention unique detectée dans le message de l'utilisateur"
    )


# ==============================================================================
# PHASE 1 : NODES (L'ENTRÉE ET LE BYPASS)
# ==============================================================================


def intent_classifier_node(state: AgentState) -> Dict[str, Any]:
    """
    Étape 0 : Analyse et classifie l'intention globale de la requête utilisateur.
    Utilise ChatPromptTemplate pour forcer Ollama à respecter les consignes système.
    """
    logger.info(
        f"[intent_classifier_node] Début de intent_classifier_node. Classification à 4 axes pour : '{state.user_query}'"
    )
    steps = list(state.steps)

    # 1. Détection de la présence d'un film en mémoire vive
    movie_ids = (
        state.last_displayed_movies_id
        if state.last_displayed_movies_id is not None
        else []
    )

    # Affichage de contrôle pour ton débug
    logger.info(
        f"[intent_classifier_node] Contenu réel de la mémoire détecté : {movie_ids}"
    )

    has_context_bool = True if len(movie_ids) > 0 else False
    has_active_context = "TRUE" if has_context_bool else "FALSE"
    logger.info(
        f"[intent_classifier_node] Statut transmis au LLM : {has_active_context}"
    )

    # 2. Remplacement des variables dans le template textuel
    prompt_system_text = INTENTION_PROMPT.replace(
        "__USER_QUERY__", state.user_query
    ).replace("__HAS_CONTEXT__", has_active_context)

    try:
        # 3. Association du schéma de sortie au LLM
        extractor = structured_llm.with_structured_output(IntentOutput)

        # 4. Chaînage du prompt et de l'extracteur
        result: IntentOutput = extractor.invoke(
            [SystemMessage(content=prompt_system_text)]
        )
        intent_verdict = result.intent
        logger.info(f"[intent_classifier_node] Intent Détécté : {intent_verdict}")

    except Exception as e:
        logger.error(
            f"[intent_classifier_node] Échec de l'extraction structurée guidée ({e}). Bascule sur RECHERCHE."
        )
        intent_verdict = "RECHERCHE"

    # 5. LA SÉCURITÉ METIER : Forçage si le stock est vide
    if intent_verdict == "DISCUSSION" and not has_context_bool:
        logger.warning(
            "[intent_classifier_node] L'utilisateur veut discuter mais AUCUN FILM n'est en stock. Redirection."
        )
        intent_verdict = "AUCUN_FILM_TROUVE"

    # 6. Si la session vient d'ouvrir et qu'on ne sait pas quoi faire
    elif not has_context_bool and intent_verdict not in ["CHITCHAT", "RECHERCHE"]:
        logger.info("[intent_classifier_node] Demarage de la session. Redirection. ")
        intent_verdict = "AUCUN_FILM_TROUVE"

    # 7. Tracabilité : Mise à jour des steps et envoi du verdict au front possible.
    steps.append(
        AgentStep(
            step="intent_classification",
            status=f"Intention retenue : {intent_verdict}",
            intent=intent_verdict,
        )
    )
    new_branch = "DISCUSSION" if intent_verdict == "DISCUSSION" else "RAG"
    return {
        "intent": intent_verdict,
        "current_step": intent_verdict,
        "steps": steps,
        "branch_search_wiki": new_branch,
    }


def title_router_node(state: AgentState) -> Dict[str, Any]:
    """
    Détecte la présence d'un titre de film dans la requête.

    Ce nœud utilise un LLM spécialisé pour analyser l'entrée textuelle de l'utilisateur.
    Selon le résultat, il aiguille le graphe vers deux stratégies distinctes :
      - Processus A (Direct) : Recherche focalisée sur un titre exact.
      - Processus B (Hybride) : Recherche multicritères via filtres relationnels.

    Args:
        state (AgentState): L'état courant du graphe LangGraph.

    Returns:
        Dict[str, Any]: Les clés d'état à mettre à jour pour l'arête conditionnelle.
    """
    logger.info(
        f"[title_router_node] Début de title_router_node. Analyse de la requête utilisateur : '{state.user_query}'"
    )
    # Copie locale de la liste des étapes pour respecter le principe d'immutabilité de LangGraph
    steps = list(state.steps)

    # Appel au LLM avec le prompt système d'extraction sémantique et la requête brute
    response: AIMessage = llm.invoke(
        [
            SystemMessage(content=TITLE_DETECTOR_PROMPT),
            HumanMessage(content=state.user_query),
        ]
    )

    # Nettoyage de la réponse pour supprimer les guillemets parasites d'hallucination
    response_str = str(response.content)
    detected_title = response_str.strip().replace('"', "").replace("'", "")

    # ---------- CAS 1 : Un titre de film a été isolé par le modèle ----------------
    if detected_title:
        logger.info(
            f"[title_router_node] Titre de film explicitement détecté par le LLM : '{detected_title}'"
        )
        # Traçabilité : Enregistrement de l'action réussie dans le suivi de session
        steps.append(
            AgentStep(
                step="title_detection",
                status=f"Titre détecté : '{detected_title}'",
            )
        )
        # Mutation de l'état : Aiguillage vers "has_title" pour 'route_after_title_check'
        return {
            "current_step": "has_title",
            "search_branch": "direct",
            "steps": steps,
            "answer": detected_title,  # Stockage temporaire du titre pour direct_movie_detail
        }

    # ---------- CAS 2 : La requête est floue ou décrit des critères (ex: "un film de SF de 2022") ----------
    logger.info(
        "[title_router_node] Aucun titre spécifique détecté par le LLM. Bascule en mode recherche par critères."
    )

    # Traçabilité : Enregistrement du choix de repli par critères
    steps.append(
        AgentStep(
            step="title_detection",
            status="Aucun titre détecté. Passage au mode critères.",
        )
    )
    # Mutation de l'état : Aiguillage vers "no_title" (Processus B - Hybride)
    return {"current_step": "no_title", "search_branch": "hybrid", "steps": steps}


# ==============================================================================
# PHASE 2 : NODES RAG
# ==============================================================================


def merge_filters_node(state: AgentState) -> Dict[str, Any]:
    """
    Extrait les filtres SQL depuis la requête utilisateur (LLM structuré),
    les merge avec initial_filters (front-end), valide les bornes.
    Alimente sql_filters pour search_vector_node.
    """
    logger.info(
        f"[merge_filters_node] Début de l'extraction filtres pour : '{state.user_query}'"
    )
    steps = list(state.steps)

    # 1. Extraction LLM → ChatFilters
    try:
        extractor = structured_llm.with_structured_output(ChatFilters)
        extracted = extractor.invoke(
            [("system", ROUTER_PROMPT), ("user", state.user_query)]
        )
        logger.info(
            f"[merge_filters_node] extraits par le LLM : {extracted.model_dump(exclude_none=True)}"
        )
    except Exception as e:
        logger.error(f"[merge_filters_node] Échec extraction : {e}. Filtres vides.")
        extracted = ChatFilters()

    # 2. Guard : LLM hallucine parfois en excluant TOUT le catalogue
    if extracted.genres_excluded and set(extracted.genres_excluded) >= CATALOG_GENRES:
        logger.warning(
            "[merge_filters_node] genres_excluded couvre tout le catalogue — ignoré."
        )
        extracted.genres_excluded = []

    # 3. Merge : initial_filters (front) + extracted (LLM), le LLM écrase si valeur active
    logger.info(
        "[merge_filters_node] Fusion des filtres de l'interface graphique (front-end) et du LLM."
    )
    merged_filters_dict = state.initial_filters.model_dump()
    for key, value in extracted.model_dump(exclude_none=True).items():
        if value:
            merged_filters_dict[key] = value
    merged_filters: ChatFilters = ChatFilters(**merged_filters_dict)

    # 4. Validation bornes d'années
    if merged_filters.release_year_min and merged_filters.release_year_max:
        if merged_filters.release_year_min > merged_filters.release_year_max:
            logger.warning(
                "[merge_filters_node] Bornes années inversées — correction auto."
            )
            merged_filters.release_year_min, merged_filters.release_year_max = (
                merged_filters.release_year_max,
                merged_filters.release_year_min,
            )

    # 5. Tracabilité : Mise à jour des steps et envoi du verdict au front possible.
    logger.info(
        f"[merge_filters_node] Filtres finaux consolidés (Merged) : {merged_filters.model_dump(exclude_none=True)}"
    )
    steps.append(
        AgentStep(
            step="merge_filters",
            status=f"Filtres consolidés : {merged_filters.model_dump(exclude_none=True)}",
        )
    )

    return {
        "sql_filters": merged_filters,
        "current_step": "filters_ready",
        "steps": steps,
    }


def search_vector_node(state: AgentState) -> Dict[str, Any]:
    """
    Exécute le pré-filtrage SQL puis la recherche FAISS.
    Commun aux deux branches (direct et hybride).

    - Branche directe  : query = state.answer (titre extrait), top_k=1, pas de filtres SQL
    - Branche hybride  : query = state.user_query, top_k=5, filtres SQL depuis state.sql_filters
    """
    logger.info(f"[search_vector_node] Branche : '{state.search_branch}'")
    steps = list(state.steps)

    is_direct = state.search_branch == "direct"
    query = state.answer if is_direct else state.user_query
    top_k = 1 if is_direct else 5

    # 1. Pré-filtrage SQL (branche hybride uniquement)
    candidate_ids = None
    if not is_direct and state.sql_filters:
        f = state.sql_filters
        candidate_ids = filter_films_by_criteria.func(
            realisateur=f.realisateur,
            genres_included=f.genres_included or None,
            genres_excluded=f.genres_excluded or None,
            release_year_min=f.release_year_min,
            release_year_max=f.release_year_max,
            tmdb_score_min=f.tmdb_score_min,
            runtime_min=f.runtime_min,
            runtime_max=f.runtime_max,
        )
        logger.info(
            f"[search_vector_node] Pool SQL : {len(candidate_ids) if candidate_ids else 'None (catalogue complet)'}"
        )

    # Court-circuit : pool SQL vide = aucun film possible
    if candidate_ids is not None and len(candidate_ids) == 0:
        logger.warning("[search_vector_node] Pool SQL vide — aucun film candidat.")
        steps.append(
            AgentStep(step="search_vector", status="Pool SQL vide — aucun résultat.")
        )
        return {
            "retrieved_movies": [],
            "candidate_ids": [],
            "current_step": "no_results",
            "steps": steps,
        }
    elif candidate_ids:
        logger.info(
            f"[search_vector_node] Nombre d'ID(s) candidats injecté(s) comme masque dans FAISS : {len(candidate_ids)}"
        )
    else:
        logger.info(
            "Aucune contrainte stricte SQL (candidate_ids est None). Recherche vectorielle ouverte sur tout le catalogue."
        )

    # Tracabilité : Mise à jour des steps
    steps.append(
        AgentStep(
            step="vector_recommendations",
            status="Calcul des affinités sémantiques...",
        )
    )
    # 2. Recherche FAISS
    results = search_vector_catalog.func(
        query=query,
        top_k=top_k,
        candidate_ids=candidate_ids,
    )
    logger.info(
        f"[search_vector_node] FAISS → {len(results)} résultat(s) pour query='{query}'"
    )

    # Tracabilité : Mise à jour des steps et envoi du verdict au front possible.
    steps.append(
        AgentStep(
            step="search_vector",
            status=f"{len(results)} film(s) trouvé(s) — branche {'directe' if is_direct else 'hybride'}",
        )
    )

    return {
        "retrieved_movies": results,
        "candidate_ids": candidate_ids,
        "current_step": "has_results" if results else "no_results",
        "steps": steps,
    }


def hydratation_node(state: AgentState) -> Dict[str, Any]:
    """
    Branche directe uniquement.
    Hydrate le FilmShort retourné par FAISS en FilmDetail complet via SQL.
    """
    logger.info("[hydratation_node] Hydratation FilmShort → FilmDetail")
    steps = list(state.steps)

    # Cas 1 : Hydratation échouée : Pas de film retrouvé dans retrieved_movies.
    if not state.retrieved_movies:
        logger.warning("[hydratation_node] retrieved_movies vide — rien à hydrater.")
        steps.append(AgentStep(step="hydratation", status="Aucun film à hydrater."))
        return {"current_step": "no_results", "steps": steps}

    # Recupération du premier résultat de la liste retrieved_movies.
    tmdb_id = state.retrieved_movies[0].tmdb_id
    logger.info(f"[hydratation_node] Hydratation pour tmdb_id={tmdb_id}")

    # Hydratation du film selectionné.
    details = get_films_details_by_ids([tmdb_id])

    # Cas 2 : Hydratation échouée : Film Absent de la table SQL
    if not details:
        logger.error(
            f"[hydratation_node] Film tmdb_id={tmdb_id} absent de la table SQL."
        )
        steps.append(
            AgentStep(step="hydratation", status=f"Film {tmdb_id} introuvable en SQL.")
        )
        return {"current_step": "no_results", "steps": steps}

    # Cas 3 : Hydratation résussi : Film présent dans la table SQL
    else:
        steps.append(
            AgentStep(
                step="hydratation", status=f"FilmDetail chargé : '{details[0].title}'"
            )
        )

        return {
            "retrieved_movies": details,
            "current_step": "hydrated",
            "steps": steps,
        }


def card_node(state: AgentState) -> Dict[str, Any]:
    """
    Branche directe.
    Signale que retrieved_movies est prêt à être envoyé au front via SSE type='card'.
    Filtre retrieved_movies pour ne conserver que le premier film (FilmDetail unique).
    Le nœud ne formate rien — c'est le stream handler qui sérialise FilmDetail.
    """
    logger.info("[card_node] Selection du film pour l'envoie de la Card via SSE.")
    steps = list(state.steps)

    # Cas 1 : Génération de la Card échouée : pas de Film à affiché
    if not state.retrieved_movies:
        logger.error(
            "[card_node] Aucun films présent dans le retrieved_movie. envoi step : no_results"
        )
        steps.append(AgentStep(step="card", status="Aucun film à afficher."))
        return {"current_step": "no_results", "steps": steps}

    # Recupération du premier résultat de la liste retrieved_movies.
    film = state.retrieved_movies[0]
    logger.info(f"[card_node] Selection du film : '{film.title}'")

    last_displayed_movies_id = [film.tmdb_id]
    logger.info(
        f"[card_node] Sauvegarde de la liste des films affichés : {last_displayed_movies_id}"
    )
    # Cas 2 : Génération de la card réussi, selection du film (premier résultat)
    steps.append(AgentStep(step="card", status=f"Carte prête : '{film.title}'"))

    return {
        "current_step": "card_ready",
        "steps": steps,
        "retrieved_movies": [film],
        "last_displayed_movies_id": last_displayed_movies_id,
    }


def validation_node(state: AgentState) -> Dict[str, Any]:
    """
    Branche directe uniquement.
    Vérifie la cohérence sémantique entre le FilmDetail hydraté et la requête.
    """
    logger.info("[validation_node] Validation sémantique film ↔ requête")
    steps = list(state.steps)

    # Cas 1 : Validation échouée : pas de film dnas retrieved_movie
    if not state.retrieved_movies:
        logger.warning(
            "[validation_node] Aucun film trouvé dans les catalogues SQL/FAISS."
        )
        steps.append(
            AgentStep(
                step="validation_direct", status="Aucun film trouvé. Fin du graphe."
            )
        )
        return {"current_step": "invalid_coherence", "steps": steps}

    # Recuperation de premier film de retrieved_movie
    film = state.retrieved_movies[0]

    # Création des parramètres pour l'appel de validation
    evaluator = structured_llm.with_structured_output(ValidationResult)
    prompt = f"""
    Tu es un contrôleur qualité pour un système RAG sur le cinéma d'horreur.
    Analyse si la réponse générée correspond fidèlement aux films trouvés et à la question initiale.
    
    Requête Utilisateur : {state.user_query}
    Films trouvés (Contexte) : {film.title}
    Réponse générée par le LLM : {state.answer}

    Si la réponse est incorrecte ET que tu peux identifier avec certitude le titre exact
    du film qui aurait dû être recherché (ex: la requête décrit clairement un film connu
    par son réalisateur/synopsis mais le mauvais film a été renvoyé), indique ce titre
    dans corrected_title pour permettre une nouvelle recherche ciblée.
    """

    # Appel de Validation
    try:
        result = evaluator.invoke(prompt)
        logger.info(f"[validation_node] Résultat : {result.model_dump()}")
    except Exception as e:
        logger.error(
            f"[validation_node] Échec évaluateur : {e}. Validation par défaut."
        )
        result = ValidationResult(
            is_relevant=True, has_missing_info=False, feedback="Fallback"
        )

    # Cas 2 : Le résultat est validé et il ne manque pas d'informations
    if result.is_relevant and not result.has_missing_info:
        status = "valid"
        logger.info(
            "[validation_node] Validation Réussie : La réponse est pertinente et complète."
        )
        steps.append(AgentStep(step="validation_direct", status=status))
        return {"current_step": status, "steps": steps}

    # Cas 3 : Le résultat est validé et il manque des informations
    elif result.is_relevant and result.has_missing_info:
        status = "valid_missing_synopsis"
        logger.info(
            "[validation_node] Validation Réussie : La réponse est pertinente mais incomplète."
        )
        steps.append(AgentStep(step="validation_direct", status=status))
        return {"current_step": status, "steps": steps}

    # Le résultat est invalide.
    else:
        logger.warning(f"[validation_node] Film invalide : {result.feedback}")
        steps.append(
            AgentStep(
                step="validation_direct",
                status=f"invalid_coherence : {result.feedback}",
            )
        )

        update: Dict[str, Any] = {
            "current_step": "invalid_coherence",
            "steps": steps,
            "retry_count": state.retry_count + 1,
            "answer": result.corrected_title,
        }

        # Extraction générique depuis les guillemets simples du feedback

        import re

        if not result.corrected_title:
            match = re.search(r"'([^']+)'", result.feedback)
            if match:
                result.corrected_title = match.group(1)
                logger.info(
                    f"[validation_node] Titre extrait du feedback : '{result.corrected_title}'"
                )

        # Cas 4 : Validation Echouée du validateur mais titre trouvé
        if result.corrected_title:
            logger.warning(
                f"[validation_node] Validation Échouée. Titre corrigé identifié par le validateur : "
                f"'{result.corrected_title}'. Nouvelle recherche directe ciblée."
            )
            update["answer"] = result.corrected_title
            return update

        # Cas 5 : Validation Echouée du validateur et aucun titre trouvé
        else:
            logger.warning("[validation_node] Validation Échouée. Aucun titre trouvé. ")
            return update


def format_cards_node(state: AgentState) -> Dict[str, Any]:
    """
    Branche hybride uniquement.
    Ré-hydrate les FilmShort depuis SQL (synopsis inclus) via get_films_short_by_ids
    et signale que les cartes sont prêtes pour envoi SSE type='card'.
    """
    logger.info("[format_cards_node] Hydratation FilmShort depuis SQL.")
    steps = list(state.steps)

    # Cas 1 : Hydratation Echouée : Pas de film trouvé pour l'hydratation
    if not state.retrieved_movies:
        logger.warning("[format_cards_node] Aucun film à hydrater.")
        steps.append(AgentStep(step="format_cards", status="Aucun film à afficher."))
        return {"current_step": "no_results", "steps": steps}

    # Recupération des ids des retrieved_movies
    tmdb_ids = [f.tmdb_id for f in state.retrieved_movies]

    # Appel de la base de donnée pour récupérer toutes les informations SQL pour Film_shorts
    try:
        with db_session() as session:
            films = get_films_short_by_ids(session, tmdb_ids)
        # Cas 2 : Hydratation Réussie
        logger.info(
            f"[format_cards_node] {len(films)} FilmShort hydratés : {[f.title for f in films]}"
        )

    # Cas 3 : Hydratation Echouée : Erreur SQL
    except Exception as e:
        logger.error(f"[format_cards_node] Erreur SQL : {e}. Aucune carte disponible.")
        steps.append(
            AgentStep(
                step="format_cards", status="Erreur SQL — aucune carte disponible."
            )
        )
        return {"retrieved_movies": [], "current_step": "no_results", "steps": steps}

    last_displayed_movies_id = [f.tmdb_id for f in films]
    logger.info(
        f"[format_cards_node] Sauvegarde de la liste des films affichés : {last_displayed_movies_id}"
    )

    # Traçabilité : Enregistrement du choix de repli par critères
    steps.append(
        AgentStep(step="format_cards", status=f"{len(films)} carte(s) prête(s).")
    )

    return {
        "retrieved_movies": films,
        "current_step": "cards_ready",
        "steps": steps,
        "last_displayed_movies_id": last_displayed_movies_id,
    }


def validation_film_node(state: AgentState) -> Dict[str, Any]:
    """
    Branche hybride uniquement.
    Vérifie la cohérence de la liste de FilmShort retournée par FAISS
    par rapport aux filtres initiaux et à la requête utilisateur.
    """
    logger.info("[validation_film_node] Validation liste films ↔ filtres")
    steps = list(state.steps)

    # Cas 1 : Aucun film retourné par FAISS
    if not state.retrieved_movies:
        logger.warning("[validation_film_node] Aucun film à valider.")
        steps.append(AgentStep(step="validation_hybrid", status="Aucun film trouvé."))
        return {"current_step": "invalid_coherence", "steps": steps}

    # Création de listes pour vérifier la cohérence des films retournés par FAISS
    films_summary = "\n".join(
        [
            f"- {f.title} ({f.release_date}) | Genres : {', '.join(f.genres) if f.genres else 'N/A'} | TMDB : {f.tmdb_score}/10 | Synopsis : {f.synopsis or 'Non disponible'}"
            for f in state.retrieved_movies
        ]
    )

    #
    filters_summary = (
        state.sql_filters.model_dump(exclude_none=True) if state.sql_filters else {}
    )

    # Préparation de l'appel LLM
    evaluator = structured_llm.with_structured_output(ValidationFilmListResult)
    prompt = f"""
        Tu es un contrôleur qualité pour un système RAG cinéma d'horreur.
        Vérifie que la liste de films proposée correspond aux critères demandés.

        Requête utilisateur : {state.user_query}
        Filtres appliqués : {filters_summary}
        Films proposés :
        {films_summary}

        is_relevant : True si au moins la majorité des films correspondent aux critères.
        has_missing_info : True si des films pertinents ont un synopsis absent ou vide.
        corrected_title : laisser vide pour la recherche hybride.
        """

    # Appel LLM pour validation des films proposés
    try:
        result = evaluator.invoke(prompt)
        logger.info(f"[validation_film_node] Résultat : {result.model_dump()}")
    except Exception as e:
        logger.error(
            f"[validation_film_node] Échec évaluateur : {e}. Validation par défaut."
        )
        result = ValidationFilmListResult(
            valid_titles=[f.title for f in state.retrieved_movies],
            invalid_titles=[],
            feedback="Fallback",
        )

    # Verification qu'il n'y a pas de doublons dans la liste envoyée par le LLM.
    valid_titles_set = set(result.valid_titles)

    # Création de la liste de FilmShort des film validés
    filtered_movies = [f for f in state.retrieved_movies if f.title in valid_titles_set]

    # Cas 2 : PASS : Aucun films invalide retourné
    if len(result.invalid_titles) == 0:
        steps.append(AgentStep(step="validation_hybrid", status="valid"))
        return {
            "current_step": "valid",
            "retrieved_movies": state.retrieved_movies,
            "steps": steps,
        }

    # Cas 3 : PASS partiel : il y a des films validés mais pas tous,
    if filtered_movies:
        logger.info(
            f"[validation_film_node] PASS partiel : {len(filtered_movies)}/{len(state.retrieved_movies)} films retenus."
        )
        steps.append(
            AgentStep(
                step="validation_hybrid",
                status=f"valid_partial — {len(filtered_movies)} film(s) retenus.",
            )
        )
        return {
            "current_step": "valid_partial",
            "retrieved_movies": filtered_movies,
            "steps": steps,
        }

    # Cas 4 : FAIL Aucun films cohérents détecté par le LLM
    else:
        logger.warning(
            f"[validation_film_node] Aucun film cohérent : {result.feedback}"
        )
        steps.append(
            AgentStep(
                step="validation_hybrid",
                status=f"invalid_coherence : {result.feedback}",
            )
        )
        return {
            "current_step": "invalid_coherence",
            "steps": steps,
            "retry_count": state.retry_count + 1,
        }


# ==============================================================================
# PHASE 3 : DISCUSSION
# ==============================================================================


def load_film_node(state: AgentState) -> Dict[str, Any]:
    """
    Branche DISCUSSION uniquement.
    Charge le FilmDetail depuis last_displayed_movies_id (mémoire session).
    Alimente retrieved_movies pour route_verif_film puis narrator_node.
    """
    logger.info("[load_film_node] Chargement du film en mémoire session.")
    steps = list(state.steps)

    # Recupération des ids dans last_displayed_movie_id
    film_ids = state.last_displayed_movies_id or []

    # Cas 1 : Pas d'id trouvé retour vers la recherche RAG.
    if not film_ids:
        logger.warning("[load_film_node] Aucun film en mémoire session.")
        steps.append(AgentStep(step="load_film", status="Aucun film en mémoire."))
        return {
            "retrieved_movies": [],
            "current_step": "intent_rupture",
            "branch_search_wiki": "RAG",
            "steps": steps,
        }

    logger.info(f"[load_film_node] Chargement pour tmdb_ids : {film_ids}")

    # Hydratation des films pour contexte.
    try:
        details = get_films_details_by_ids(film_ids)
    except Exception as e:
        logger.error(f"[load_film_node] Erreur SQL : {e}.")
        details = []

    # Cas 2 : Pas de détail trouvé
    if not details:
        logger.warning(f"[load_film_node] Aucun FilmDetail trouvé pour ids={film_ids}.")
        steps.append(AgentStep(step="load_film", status="Film introuvable en SQL."))
        return {
            "retrieved_movies": [],
            "current_step": "intent_rupture",
            "branch_search_wiki": "DISCUSSION",
            "steps": steps,
        }

    # Cas 3 : Hydratation Réussie.
    else:
        logger.info(f"[load_film_node] Films chargés : '{details[0].title}'")
        steps.append(
            AgentStep(step="load_film", status=f"Films chargés : '{details[0].title}'")
        )

        return {
            "retrieved_movies": details,
            "current_step": "film_loaded",
            "branch_search_wiki": "DISCUSSION",
            "steps": steps,
        }


def verif_film_node(state: AgentState) -> Dict[str, Any]:
    """
    Branche DISCUSSION uniquement.
    Analyse la question utilisateur et vérifie si le FilmDetail chargé
    contient la donnée nécessaire pour y répondre.
    Positionne current_step = "valid" ou "valid_missing_synopsis".
    """
    logger.info("[verif_film_node] Vérification données films vs question utilisateur.")
    steps = list(state.steps)

    # Cas 1 : Sécurité — aucun film chargé en contexte.
    # Ne devrait pas arriver si load_film_node et route_verif_film sont correctement câblés.
    if not state.retrieved_movies:
        logger.warning("[verif_film_node] Aucun film chargé.")
        steps.append(AgentStep(step="verif_film", status="Aucun film en contexte."))
        return {
            "current_step": "intent_rupture",
            "enrich_ids": [],
            "steps": steps,
        }

    films = state.retrieved_movies

    # Sérialisation de TOUS les films disponibles en contexte.
    # getattr défensif car film peut être FilmShort ou FilmDetail selon la session.
    film_data_summary = "\n\n".join(
        [
            f"Film {i + 1} :\n"
            f"Titre : {f.title}\n"
            f"Réalisateur : {getattr(f, 'realisateur', None) or getattr(f, 'director', 'Non disponible')}\n"
            f"Date de sortie : {getattr(f, 'release_date', 'Non disponible')}\n"
            f"Genres : {', '.join(f.genres) if getattr(f, 'genres', None) else 'Non disponible'}\n"
            f"Synopsis : {getattr(f, 'synopsis', None) or 'Non disponible'}\n"
            f"Score TMDB : {getattr(f, 'tmdb_score', 'Non disponible')}\n"
            f"Score IMDb : {getattr(f, 'imdb_score', 'Non disponible')}\n"
            f"Score RT : {getattr(f, 'rotten_tomatometer', 'Non disponible')}\n"
            f"Durée : {getattr(f, 'runtime', 'Non disponible')} min\n"
            f"Collection : {getattr(f, 'collection', 'Non disponible')}\n"
            f"Tagline : {getattr(f, 'tagline', 'Non disponible')}"
            for i, f in enumerate(films)
        ]
    )

    # Appel structured_llm pour identifier les films avec données manquantes.
    checker = structured_llm.with_structured_output(FilmDataCheck)
    prompt = f"""
        Tu es un assistant qui vérifie si une base de données film contient la réponse à une question.
        
        Question utilisateur : {state.user_query}

        Données disponibles ({len(films)} film(s)) :
        {film_data_summary}

        RÈGLE STRICTE : 
        - Si une donnée nécessaire pour répondre à la question est absente, marquée comme "Non disponible" ou vide dans les données ci-dessus, tu DOIS placer le titre du film dans 'films_missing'.
        - 'films_ok' ne doit contenir que les titres où la donnée est présente ET complète.

        films_ok : titres des films pour lesquels la donnée demandée est présente et non vide.
        films_missing : titres des films pour lesquels la donnée demandée est absente, vide ou marquée comme "Non disponible".
        sujet : identifie précisément ce que l'utilisateur demande.
        feedback : explique ce qui est disponible ou ce qui manque.
        """

    try:
        result: FilmDataCheck = checker.invoke(prompt)
        logger.info(f"[verif_film_node] Résultat : {result.model_dump()}")
    except Exception as e:
        # Cas 2 : Échec du checker LLM.
        # Fallback : on considère toutes les données disponibles pour ne pas bloquer le flux.
        logger.error(f"[verif_film_node] Échec checker : {e}. Fallback valid.")
        result = FilmDataCheck(
            sujet="inconnu",
            films_ok=[f.title for f in films],
            films_missing=[],
            feedback="Fallback",
        )

    # Construction de la liste des tmdb_id à enrichir via Wikipedia.
    missing_titles = set(result.films_missing)
    films_to_enrich = [f for f in films if f.title in missing_titles]
    films_ids_to_enrich = [f.tmdb_id for f in films_to_enrich]

    # Cas 3 : Au moins un film nécessite un enrichissement Wikipedia.
    if films_to_enrich:
        status = "valid_missing_data"
        logger.info(
            f"[verif_film_node] {len(films_to_enrich)} film(s) à enrichir via Wikipedia : "
            f"{[f.title for f in films_to_enrich]}"
        )
    # Cas 4 : Toutes les données sont disponibles.
    else:
        status = "valid"
        logger.info(
            f"[verif_film_node] Toutes les données disponibles pour '{result.sujet}'."
        )

    # Traçabilité : Enregistrement de la liste des film à enrichir dans le journal.
    steps.append(
        AgentStep(
            step="verif_film",
            status=f"{status} — sujet='{result.sujet}' | à enrichir : {[f.title for f in films_to_enrich]} | {result.feedback}",
        )
    )

    return {
        "current_step": status,
        "enrich_ids": films_ids_to_enrich,
        "data_enriched": result.feedback,
        "steps": steps,
    }
