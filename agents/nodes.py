"""agents/nodes.py
Module de définition des nœuds (Nodes) du graphe de l'agent LangGraph.

Ce fichier contient les fonctions Python autonomes qui représentent les étapes de
calcul et de décision du graphe. Chaque nœud reçoit l'état actuel ('AgentState'),
exécute une action spécifique (appel LLM, orchestration d'outils, formatage de données),
puis retourne les mises à jour à appliquer à l'état.

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

import json
import sys
from pathlib import Path
from typing import Any, Dict

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

root_path = Path(__file__).resolve().parent.parent
if str(root_path) not in sys.path:  # pragma: no cover
    sys.path.insert(0, str(root_path))

from agents.config import llm, structured_llm
from agents.prompts import GENERATOR_PROMPT, ROUTER_PROMPT, TITLE_DETECTOR_PROMPT
# from agents.state import AgentState, AgentStep
from agents.tools.sql_tools import filter_films_by_criteria
from agents.tools.vector_tools import search_vector_catalog
from agents.tools.wiki_tools import (
    wikipedia_search,
)
from api.schemas import ChatFilters, AgentState, AgentStep
from database.connection import db_session
from database.queries import get_film_details_by_id

# LOGGER ------------------------------------------------------
from logger import get_logger, setup_logger

setup_logger()

logger = get_logger("NODES")

# ==============================================================================
# ROUTING LOGIC
# ==============================================================================


def route_after_title_check(state: AgentState) -> str:
    """Aiguille le workflow selon la présence ou non d'un titre de film précis."""
    logger.info(
        f"Routage conditionnel invoqué. Étape actuelle détectée : '{state.current_step}'"
    )
    if state.current_step == "has_title":
        logger.info("Aiguillage vers le processus A : 'direct_movie_detail'")
        return "direct_movie_detail"
    logger.info("Aiguillage vers le processus B : 'filter_and_search_hybrid'")
    return "filter_and_search_hybrid"


# ==============================================================================
# NODES
# ==============================================================================


def title_router_node(state: AgentState) -> Dict[str, Any]:
    """Étape 1 : Détecte la mention explicite d'un titre de film dans la requête."""
    logger.info(
        f"Début de title_router_node. Analyse de la requête utilisateur : '{state.user_query}'"
    )

    response = llm.invoke(
        [
            SystemMessage(content=TITLE_DETECTOR_PROMPT),
            HumanMessage(content=state.user_query),
        ]
    )
    detected_title = response.content.strip().replace('"', "").replace("'", "")

    steps = list(state.steps)

    if detected_title:
        logger.info(
            f"Titre de film explicitement détecté par le LLM : '{detected_title}'"
        )
        steps.append(
            AgentStep(
                step="title_detection",
                status=f"Titre détecté : '{detected_title}'",
            )
        )
        return {
            "current_step": "has_title",
            "steps": steps,
            "answer": detected_title,  # Stockage temporaire du titre pour direct_movie_detail
        }
    logger.info(
        "Aucun titre spécifique détecté par le LLM. Bascule en mode recherche par critères."
    )
    steps.append(
        AgentStep(
            step="title_detection",
            status="Aucun titre détecté. Passage au mode critères.",
        )
    )
    return {"current_step": "no_title", "steps": steps}


def direct_movie_detail_node(state: AgentState) -> Dict[str, Any]:
    """
    Processus A : Fiche technique complète d'un film identifié par titre.

    Flux :
        1. search_vector_catalog (top_k=1) → FilmShort (tmdb_id)
        2. get_film_details_by_id (tmdb_id) → FilmDetail (données complètes)
        3. Génération LLM à partir de la fiche FilmDetail
    """
    title_to_search = state.answer  # Titre extrait par title_router_node
    logger.info(
        f"Début de direct_movie_detail_node. Lancement de la recherche directe pour : '{title_to_search}'"
    )
    steps = list(state.steps)
    steps.append(
        AgentStep(
            step="vector_search_direct",
            status="Recherche de la fiche technique complète...",
        )
    )

    # 1. Recherche vectorielle → FilmShort (tmdb_id uniquement)
    logger.info("Étape 1/4 : Interrogation du catalogue vectoriel FAISS (top_k=1).")
    movies = search_vector_catalog.func(query=title_to_search, top_k=1)

    if not movies:
        logger.warning(
            f"Aucune correspondance trouvée dans le catalogue vectoriel pour le titre : '{title_to_search}'"
        )
        steps.append(AgentStep(step="generation", status="Terminé"))
        answer = llm.invoke(
            GENERATOR_PROMPT.format(context="Aucun film trouvé pour cette recherche.")
        ).content
        return {"current_step": "completed", "steps": steps, "answer": answer}

    film_short = movies[0]
    logger.info(
        f"Correspondance vectorielle trouvée : '{film_short.title}' (TMDB ID: {film_short.tmdb_id})"
    )

    # 2. Hydratation complète FilmShort → FilmDetail
    logger.info(
        f"Étape 2/4 : Hydratation des données complètes depuis la base SQL pour le TMDB ID : {film_short.tmdb_id}"
    )
    with db_session() as session:
        film_detail = get_film_details_by_id(session, film_short.tmdb_id)

    if not film_detail:
        logger.error(
            f"Incohérence détectée : Film trouvé dans FAISS mais introuvable dans la table SQL (ID: {film_short.tmdb_id})"
        )
        steps.append(AgentStep(step="generation", status="Terminé"))
        answer = llm.invoke(
            GENERATOR_PROMPT.format(context="Aucun film trouvé pour cette recherche.")
        ).content
        return {"current_step": "completed", "steps": steps, "answer": answer}

    # 3. Sérialisation des champs FilmDetail pour le contexte RAG
    logger.info(
        f"Étape 3/4 : Préparation et sérialisation du contexte RAG pour '{film_detail.title}'"
    )
    movie_context = (
        f"FICHE TECHNIQUE COMPLÈTE :\n"
        f"- Titre : {film_detail.title} (Titre original : {film_detail.original_title})\n"
        f"  Réalisateur : {film_detail.realisateur or film_detail.director}\n"
        f"  Date de sortie : {film_detail.release_date} | Durée : {film_detail.runtime} min\n"
        f"  Genres : {', '.join(film_detail.genres)}\n"
        f"  Synopsis : {film_detail.synopsis}\n"
        f"  Slogan : {film_detail.tagline}\n"
        f"  Scores : TMDB: {film_detail.tmdb_score}/10 | IMDb: {film_detail.imdb_score}/10 "
        f"| RT: {film_detail.rotten_tomatometer}% / {film_detail.rotten_audience_score}%\n"
        f"  Score agrégé : {film_detail.aggregated_score}/10\n"
        f"  Collection : {film_detail.collection or 'Aucune'}"
    )

    # 4. Génération
    logger.info("Étape 4/4 : Envoi du contexte complet au générateur LLM.")
    steps.append(AgentStep(step="generation", status="Terminé"))
    answer = llm.invoke(GENERATOR_PROMPT.format(context=movie_context)).content

    logger.info("Génération de la fiche technique terminée avec succès.")
    return {
        "current_step": "completed",
        "steps": steps,
        "retrieved_movies": [film_short],
        "answer": answer,
    }


def filter_and_search_hybrid_node(state: AgentState) -> Dict[str, Any]:
    """
    Processus B : Extraction des filtres, Merge, SQL puis FAISS.

    Flux :
        1. Extraction LLM → ChatFilters
        2. Merge avec initial_filters (priorité au prompt)
        3. Validation des bornes (années inversées)
        4. filter_films_by_criteria → candidate_ids
        5. search_vector_catalog → List[FilmShort]
        6. Génération LLM → ChatResponse
    """
    logger.info("Début de filter_and_search_hybrid_node (Recherche multicritères).")
    steps = list(state.steps)
    steps.append(
        AgentStep(
            step="filter_extraction",
            status="Extraction et traitement des critères...",
        )
    )

    # 1. Extraction des filtres structurés via LLM JSON
    logger.info(
        "Étape 1/7 : Extraction des filtres sémantiques via l'API structured_llm."
    )
    extractor = structured_llm.with_structured_output(ChatFilters)
    extracted_filters = extractor.invoke(
        [("system", ROUTER_PROMPT), ("user", state.user_query)]
    )
    logger.info(
        f"Filtres extraits par le LLM : {extracted_filters.model_dump(exclude_none=True)}"
    )

    # 2. Merge : le prompt écrase le front uniquement si valeur active
    logger.info(
        "Étape 2/7 : Fusion des filtres de l'interface graphique (front-end) et du LLM."
    )
    merged_filters_dict = state.initial_filters.model_dump()
    for key, value in extracted_filters.model_dump(exclude_none=True).items():
        if value:
            merged_filters_dict[key] = value

    merged_filters = ChatFilters(**merged_filters_dict)
    logger.info(
        f"Filtres finaux consolidés (Merged) : {merged_filters.model_dump(exclude_none=True)}"
    )

    # 3. Validation des bornes d'années (logique déplacée depuis validation_node)
    logger.info("Étape 3/7 : Validation des bornes d'années.")
    if merged_filters.release_year_min and merged_filters.release_year_max:
        if merged_filters.release_year_min > merged_filters.release_year_max:
            logger.warning(
                f"Incohérence détectée sur les bornes temporelles : "
                f"release_year_min ({merged_filters.release_year_min}) > release_year_max ({merged_filters.release_year_max}). "
                f"Inversion automatique des valeurs appliquée."
            )
            merged_filters.release_year_min, merged_filters.release_year_max = (
                merged_filters.release_year_max,
                merged_filters.release_year_min,
            )

    # 4. Pré-filtrage SQL
    logger.info("Étape 4/7 : Exécution du pré-filtrage SQL relationnel.")
    steps.append(
        AgentStep(
            step="sql_filtering",
            status="Application des filtres sur la base de données...",
        )
    )
    candidate_ids = filter_films_by_criteria.func(
        realisateur=merged_filters.realisateur,
        genres_included=merged_filters.genres_included or None,
        genres_excluded=merged_filters.genres_excluded or None,
        release_year_min=merged_filters.release_year_min,
        release_year_max=merged_filters.release_year_max,
        tmdb_score_min=merged_filters.tmdb_score_min,
        runtime_min=merged_filters.runtime_min,
        runtime_max=merged_filters.runtime_max,
    )

    # 5. Recherche vectorielle adaptative
    logger.info("Étape 5/7 : Préparation de la recherche sémantique vectorielle.")
    steps.append(
        AgentStep(
            step="vector_recommendations",
            status="Calcul des affinités sémantiques...",
        )
    )

    # Court-circuit si les filtres SQL sont trop restrictifs (pool vide [])
    if candidate_ids is not None and len(candidate_ids) == 0:
        logger.warning(
            "Court-circuit activé : Le filtrage SQL n'a retourné aucun ID candidat. Passage direct à l'étape finale."
        )
        recommendations = []
    else:
        if candidate_ids:
            logger.info(
                f"Nombre d'ID(s) candidats injecté(s) comme masque dans FAISS : {len(candidate_ids)}"
            )
        else:
            logger.info(
                "Aucune contrainte stricte SQL (candidate_ids est None). Recherche vectorielle ouverte sur tout le catalogue."
            )
        recommendations = search_vector_catalog.func(
            query=state.user_query,
            top_k=5,
            candidate_ids=candidate_ids,
        )
        logger.info(
            f"Nombre de recommandations retournées par FAISS : {len(recommendations)}"
        )

    # 6. Formatage du contexte RAG (champs réels de FilmShort)
    logger.info(
        "Étape 6/7 : Formatage de la liste de films pour injection dans le contexte RAG."
    )
    context_lines = []
    for m in recommendations:
        genres_str = ", ".join(m.genres) if m.genres else "N/A"
        context_lines.append(
            f"- {m.title} ({m.release_date}) | Genres : {genres_str} | Note TMDB : {m.tmdb_score}/10"
        )
    context_str = "\n".join(context_lines)

    # 7. Génération finale
    logger.info(
        "Étape 7/7 : Soumission du contexte consolidé au LLM pour génération du livrable final."
    )
    steps.append(AgentStep(step="generation", status="Terminé"))
    final_answer = llm.invoke(
        GENERATOR_PROMPT.format(
            context=context_str or "Aucun film ne correspond à ces critères."
        )
    ).content
    logger.info("Processus B (Recherche Hybride) terminé avec succès.")

    return {
        "current_step": "completed",
        "steps": steps,
        "sql_filters": merged_filters,
        "candidate_ids": candidate_ids,
        "retrieved_movies": recommendations,
        "answer": final_answer,
    }


class ValidationResult(BaseModel):
    is_relevant: bool = Field(
        description="True si la réponse répond de manière pertinente, fidèle et non erronée à la requête de l'utilisateur sur le(s) film(s) trouvé(s)."
    )
    has_missing_info: bool = Field(
        description="True si la réponse est globalement bonne mais qu'un élément crucial comme le résumé/synopsis est manquant ou vide."
    )
    feedback: str = Field(
        description="Explication concise du choix de validation ou de ce qui fait défaut."
    )


# ==============================================================================
# NODES & ROUTING LOGIC (VALIDATION & WIKIPÉDIA)
# ==============================================================================


def validation_node(state: AgentState) -> Dict[str, Any]:
    """
    Étape 3 : Évalue la qualité et la pertinence de la réponse générée par le LLM.

    Applique les règles suivantes :
      1. Si aucun film n'a été trouvé (retrieved_movies vide) -> END (go_to_end).
      2. Si la réponse est validée à 100% -> END (go_to_end).
      3. Si la réponse manque de contenu (synopsis absent) -> wikipedia_enrich.
      4. Si la réponse est jugée KO/Hallucinée -> renvoi local (retry_direct ou retry_hybrid).
    """
    logger.info(
        "Début de validation_node. Évaluation de la réponse générée par le LLM."
    )
    steps = list(state.steps)

    # RÈGLE 3 : Si la recherche en BDD n'a absolument rien retourné, on arrête les frais (END)
    if not state.retrieved_movies:
        logger.warning(
            "Validation : Aucun film trouvé dans les catalogues SQL/FAISS. Court-circuit vers END."
        )
        steps.append(
            AgentStep(step="validation", status="Aucun film trouvé. Fin du graphe.")
        )
        return {"current_step": "go_to_end", "steps": steps}

    # Interrogation du LLM évaluateur avec le format structuré
    evaluator = structured_llm.with_structured_output(ValidationResult)

    prompt_evaluation = f"""
    Tu es un contrôleur qualité pour un système RAG sur le cinéma d'horreur.
    Analyse si la réponse générée correspond fidèlement aux films trouvés et à la question initiale.
    
    Requête Utilisateur : {state.user_query}
    Films trouvés (Contexte) : {[m.title for m in state.retrieved_movies]}
    Réponse générée par le LLM : {state.answer}
    """

    try:
        evaluation = evaluator.invoke(prompt_evaluation)
        logger.info(f"Résultat de l'évaluation : {evaluation.model_dump()}")
    except Exception as e:
        logger.error(
            f"Échec de l'invocation de l'évaluateur : {repr(e)}. Validation par défaut."
        )
        evaluation = ValidationResult(
            is_relevant=True, has_missing_info=False, feedback="Fallback"
        )

    # RÈGLE 5 : La réponse est parfaite
    if evaluation.is_relevant and not evaluation.has_missing_info:
        logger.info("Validation Réussie : La réponse est pertinente et complète.")
        steps.append(AgentStep(step="validation", status="Réponse validée à 100%."))
        return {"current_step": "go_to_end", "steps": steps}

    # RÈGLE 4 : Réponse pertinente mais synopsis absent -> Redirection Wikipédia
    if evaluation.is_relevant and evaluation.has_missing_info:
        logger.info(
            "Validation Partielle : Synopsis manquant détecté. Redirection Wikipédia."
        )
        steps.append(
            AgentStep(
                step="validation",
                status="Synopsis manquant. Redirection vers l'enrichissement Wikipédia.",
            )
        )
        return {"current_step": "enrich_with_wiki", "steps": steps}

    # RÈGLES 1 & 2 : La réponse est KO. On vérifie la branche d'origine pour boucler localement
    if state.current_step == "has_title":
        logger.warning(
            f"Validation Échouée ({evaluation.feedback}). Ré-essai sur direct_movie_detail."
        )
        steps.append(
            AgentStep(
                step="validation",
                status=f"Réponse KO. Ré-essai de la branche directe. Motif : {evaluation.feedback}",
            )
        )
        return {"current_step": "retry_direct", "steps": steps}
    else:
        logger.warning(
            f"Validation Échouée ({evaluation.feedback}). Ré-essai sur filter_and_search_hybrid."
        )
        steps.append(
            AgentStep(
                step="validation",
                status=f"Réponse KO. Ré-essai de la branche hybride. Motif : {evaluation.feedback}",
            )
        )
        return {"current_step": "retry_hybrid", "steps": steps}


def route_after_validation(state: AgentState) -> str:
    """Aiguille le workflow vers le bon nœud selon la décision prise par le validateur."""
    logger.info(
        f"Routage post-validation. Décision actuelle de l'état : '{state.current_step}'"
    )

    if state.current_step == "go_to_end":
        return "go_to_end"
    elif state.current_step == "enrich_with_wiki":
        return "enrich_with_wiki"
    elif state.current_step == "retry_direct":
        return "retry_direct"
    else:
        return "retry_hybrid"


def wikipedia_enrich_node(state: AgentState) -> Dict[str, Any]:
    """
    Étape Optionnelle : Complète les synopsis absents ou incomplets en interrogeant l'outil Wikipédia,
    puis reconstruit le contexte pour régénérer la réponse finale.
    """
    logger.info(
        "Début de wikipedia_enrich_node. Recherche de compléments sur Wikipédia."
    )
    steps = list(state.steps)

    # On prend le premier film du catalogue récupéré pour chercher son résumé
    main_movie = state.retrieved_movies[0]
    logger.info(
        f"Tentative d'enrichissement pour le film principal : '{main_movie.title}'"
    )

    # Appel de l'outil de recherche Wikipédia
    wiki_res = wikipedia_search.invoke({"title": main_movie.title})

    # Construction du nouveau bloc de contexte enrichi
    if wiki_res and wiki_res.get("source") not in ["NOT_FOUND", "NO_SUMMARY"]:
        logger.info(
            f"Synopsis Wikipédia récupéré avec succès pour : '{main_movie.title}'"
        )
        extended_context = (
            f"FICHE TECHNIQUE ENRICHIE VIA WIKIPÉDIA :\n"
            f"- Titre : {main_movie.title}\n"
            f"- Note TMDB : {main_movie.tmdb_score}/10\n"
            f"- Synopsis Enrichi : {wiki_res.get('summary')}\n"
            f"- Source : {wiki_res.get('url')}"
        )
        steps.append(
            AgentStep(
                step="wikipedia_enrich",
                status=f"Synopsis enrichi depuis Wikipédia pour : '{main_movie.title}'",
            )
        )
    else:
        logger.warning(
            f"Wikipédia n'a pas retourné de résumé exploitable ({wiki_res.get('source')}). Utilisation des données existantes."
        )
        extended_context = f"Données partielles pour le film {main_movie.title}. Pas de synopsis supplémentaire disponible."
        steps.append(
            AgentStep(
                step="wikipedia_enrich", status="Aucun complément trouvé sur Wikipédia."
            )
        )

    # Ré-invocation finale du LLM générateur avec le contexte enrichi
    logger.info(
        "Régénération de la réponse finale avec le contexte enrichi de Wikipédia."
    )
    enriched_answer = llm.invoke(
        GENERATOR_PROMPT.format(context=extended_context)
    ).content

    return {"current_step": "completed", "steps": steps, "answer": enriched_answer}


# ==============================================================================
# ZONE DE TESTS LOCAUX
# ==============================================================================

if __name__ == "__main__":
    from database.faiss_service import faiss_global_service  # ← ajout

    print("🎬 Début des tests manuels des nœuds de HorRAGor...\n")

    # Initialisation obligatoire de l'index FAISS avant tout appel aux tools
    print("🔧 Initialisation de l'index FAISS...")
    with db_session() as session:
        faiss_global_service.build_index(session)
    print()

    # --------------------------------------------------------------------------
    # SCÉNARIO 1 : Processus A — Titre détecté
    # --------------------------------------------------------------------------
    print("─" * 50)
    print("SCÉNARIO 1 : Recherche Directe par Titre")
    print("─" * 50)

    state_1 = AgentState(
        user_query="Dis-m'en plus sur le film Alien de Ridley Scott ?",
        initial_filters=ChatFilters(),
    )

    print(f"👉 Question : '{state_1.user_query}'")

    # title_router
    res = title_router_node(state_1)
    state_1 = state_1.model_copy(update=res)
    print(f"✅ title_router → current_step : {state_1.current_step}")
    print(f"📋 {state_1.steps[-1].status}")

    # aiguillage
    next_node = route_after_title_check(state_1)
    print(f"🔀 Direction : {next_node}")

    if next_node == "direct_movie_detail":
        # 3. Exécution de la génération de fiche technique
        res = direct_movie_detail_node(state_1)
        state_1 = state_1.model_copy(update=res)
        print(
            f"ℹ️  Films récupérés pour contexte : {[m.title for m in state_1.retrieved_movies]}"
        )
        print(f"🤖 PREMIÈRE RÉPONSE LLM :\n{state_1.answer}\n")

        # 4. Passage dans le nœud de Validation (Output Guardrails)
        print("🔍 Lancement de la validation de la réponse...")
        res_val = validation_node(state_1)
        state_1 = state_1.model_copy(update=res_val)
        print(
            f"📋 Résultat Validateur → current_step d'aiguillage : {state_1.current_step}"
        )
        print(f"📋 Status : {state_1.steps[-1].status}")

        # 5. Simulation du routage post-validation
        post_val_route = route_after_validation(state_1)
        print(f"🔀 Action requise du graphe : {post_val_route}")

        if post_val_route == "enrich_with_wiki":
            print("🌐 Déclenchement du nœud Wikipédia...")
            res_wiki = wikipedia_enrich_node(state_1)
            state_1 = state_1.model_copy(update=res_wiki)
            print(f"🤖 RÉPONSE ENRICHIE FINALE :\n{state_1.answer}")
        elif post_val_route == "go_to_end":
            print("🏁 Réponse validée sans modification nécessaire.")
        elif post_val_route == "retry_direct":
            print("🔄 La validation a demandé un ré-essai (Correction locale).")
    print()

    # --------------------------------------------------------------------------
    # SCÉNARIO 2 : Processus B — Critères sans titre
    # --------------------------------------------------------------------------
    print("─" * 50)
    print("SCÉNARIO 2 : Recherche Hybride avec Filtres")
    print("─" * 50)

    front_filters = ChatFilters(genres_excluded=["Sci-Fi"])
    state_2 = AgentState(
        user_query="Je veux un film d'horreur de John Carpenter sorti dans les années 80, pas de science-fiction.",
        initial_filters=front_filters,
    )

    print(f"👉 Question : '{state_2.user_query}'")

    # title_router
    res = title_router_node(state_2)
    state_2 = state_2.model_copy(update=res)
    print(f"✅ title_router → current_step : {state_2.current_step}")

    # aiguillage
    next_node = route_after_title_check(state_2)
    print(f"🔀 Direction : {next_node}")

    if next_node == "filter_and_search_hybrid":
        # 3. Exécution de la recherche hybride SQL + FAISS
        res = filter_and_search_hybrid_node(state_2)
        state_2 = state_2.model_copy(update=res)

        print("\n⚙️  Filtres mergés :")
        print(json.dumps(state_2.sql_filters.model_dump(exclude_none=True), indent=2))
        print(f"🎯 IDs SQL candidats : {len(state_2.candidate_ids or [])}")
        print(f"📚 Films FAISS retenus : {len(state_2.retrieved_movies)}")
        print(f"🤖 PREMIÈRE RÉPONSE LLM :\n{state_2.answer}\n")

        # 4. Passage dans le nœud de Validation
        print("🔍 Lancement de la validation de la réponse...")
        res_val = validation_node(state_2)
        state_2 = state_2.model_copy(update=res_val)
        print(
            f"📋 Résultat Validateur → current_step d'aiguillage : {state_2.current_step}"
        )
        print(f"📋 Status : {state_2.steps[-1].status}")

        # 5. Simulation du routage post-validation
        post_val_route = route_after_validation(state_2)
        print(f"🔀 Action requise du graphe : {post_val_route}")

        if post_val_route == "enrich_with_wiki":
            print("🌐 Déclenchement du nœud Wikipédia...")
            res_wiki = wikipedia_enrich_node(state_2)
            state_2 = state_2.model_copy(update=res_wiki)
            print(f"🤖 RÉPONSE ENRICHIE FINALE :\n{state_2.answer}")
        elif post_val_route == "go_to_end":
            print("🏁 Réponse validée ou aucun film disponible. Fin nominale.")
        elif post_val_route == "retry_hybrid":
            print("🔄 La validation a demandé un ré-essai (Correction locale).")

    print("\n" + "─" * 50)
