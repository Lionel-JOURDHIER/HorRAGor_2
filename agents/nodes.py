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

root_path = Path(__file__).resolve().parent.parent
if str(root_path) not in sys.path:  # pragma: no cover
    sys.path.insert(0, str(root_path))

from agents.config import llm, structured_llm
from agents.prompts import GENERATOR_PROMPT, ROUTER_PROMPT, TITLE_DETECTOR_PROMPT
from agents.state import AgentState, AgentStep
from agents.tools.sql_tools import filter_films_by_criteria
from agents.tools.vector_tools import search_vector_catalog
from api.schemas import ChatFilters
from database.connection import db_session
from database.queries import get_film_details_by_id  # ← ajout

# ==============================================================================
# ROUTING LOGIC
# ==============================================================================


def route_after_title_check(state: AgentState) -> str:
    """Aiguille le workflow selon la présence ou non d'un titre de film précis."""
    if state.current_step == "has_title":
        return "direct_movie_detail"
    return "filter_and_search_hybrid"


# ==============================================================================
# NODES
# ==============================================================================


def title_router_node(state: AgentState) -> Dict[str, Any]:
    """Étape 1 : Détecte la mention explicite d'un titre de film dans la requête."""
    response = llm.invoke(
        [
            SystemMessage(content=TITLE_DETECTOR_PROMPT),
            HumanMessage(content=state.user_query),
        ]
    )
    detected_title = response.content.strip().replace('"', "").replace("'", "")

    steps = list(state.steps)

    if detected_title:
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

    steps.append(
        AgentStep(
            step="title_detection",
            status="Aucun titre détecté. Passage au mode critères.",
        )
    )
    return {"current_step": "no_title", "steps": steps}


def validation_node(state: AgentState) -> Dict[str, Any]:
    """
    Étape 2 : Valide la cohérence de l'état avant l'aiguillage.

    À ce stade sql_filters n'est pas encore peuplé (il le sera dans
    filter_and_search_hybrid_node après le merge). On valide uniquement
    ce qui est disponible : current_step et user_query.
    """
    steps = list(state.steps)

    if not state.user_query or not state.user_query.strip():
        steps.append(
            AgentStep(step="validation", status="Requête vide — redirection critères.")
        )
        return {"current_step": "no_title", "steps": steps}

    steps.append(
        AgentStep(
            step="validation",
            status=f"Requête validée. Direction : {state.current_step}",
        )
    )
    return {"steps": steps}


def direct_movie_detail_node(state: AgentState) -> Dict[str, Any]:
    """
    Processus A : Fiche technique complète d'un film identifié par titre.

    Flux :
        1. search_vector_catalog (top_k=1) → FilmShort (tmdb_id)
        2. get_film_details_by_id (tmdb_id) → FilmDetail (données complètes)
        3. Génération LLM à partir de la fiche FilmDetail
    """
    title_to_search = state.answer  # Titre extrait par title_router_node
    steps = list(state.steps)
    steps.append(
        AgentStep(
            step="vector_search_direct",
            status="Recherche de la fiche technique complète...",
        )
    )

    # 1. Recherche vectorielle → FilmShort (tmdb_id uniquement)
    movies = search_vector_catalog.func(query=title_to_search, top_k=1)

    if not movies:
        steps.append(AgentStep(step="generation", status="Terminé"))
        answer = llm.invoke(
            GENERATOR_PROMPT.format(context="Aucun film trouvé pour cette recherche.")
        ).content
        return {"current_step": "completed", "steps": steps, "answer": answer}

    film_short = movies[0]

    # 2. Hydratation complète FilmShort → FilmDetail
    with db_session() as session:
        film_detail = get_film_details_by_id(session, film_short.tmdb_id)

    if not film_detail:
        steps.append(AgentStep(step="generation", status="Terminé"))
        answer = llm.invoke(
            GENERATOR_PROMPT.format(context="Aucun film trouvé pour cette recherche.")
        ).content
        return {"current_step": "completed", "steps": steps, "answer": answer}

    # 3. Sérialisation des champs FilmDetail pour le contexte RAG
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
    steps.append(AgentStep(step="generation", status="Terminé"))
    answer = llm.invoke(GENERATOR_PROMPT.format(context=movie_context)).content

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
    steps = list(state.steps)
    steps.append(
        AgentStep(
            step="filter_extraction",
            status="Extraction et traitement des critères...",
        )
    )

    # 1. Extraction des filtres structurés via LLM JSON
    extractor = structured_llm.with_structured_output(ChatFilters)
    extracted_filters = extractor.invoke(
        [("system", ROUTER_PROMPT), ("user", state.user_query)]
    )

    # 2. Merge : le prompt écrase le front uniquement si valeur active
    merged_filters_dict = state.initial_filters.model_dump()
    for key, value in extracted_filters.model_dump(exclude_none=True).items():
        if value:
            merged_filters_dict[key] = value

    merged_filters = ChatFilters(**merged_filters_dict)

    # 3. Validation des bornes d'années (logique déplacée depuis validation_node)
    if merged_filters.release_year_min and merged_filters.release_year_max:
        if merged_filters.release_year_min > merged_filters.release_year_max:
            merged_filters.release_year_min, merged_filters.release_year_max = (
                merged_filters.release_year_max,
                merged_filters.release_year_min,
            )

    # 4. Pré-filtrage SQL
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
    steps.append(
        AgentStep(
            step="vector_recommendations",
            status="Calcul des affinités sémantiques...",
        )
    )

    # Court-circuit si les filtres SQL sont trop restrictifs (pool vide [])
    if candidate_ids is not None and len(candidate_ids) == 0:
        recommendations = []
    else:
        recommendations = search_vector_catalog.func(
            query=state.user_query,
            top_k=5,
            candidate_ids=candidate_ids,
        )

    # 6. Formatage du contexte RAG (champs réels de FilmShort)
    context_lines = []
    for m in recommendations:
        genres_str = ", ".join(m.genres) if m.genres else "N/A"
        context_lines.append(
            f"- {m.title} ({m.release_date}) | Genres : {genres_str} | Note TMDB : {m.tmdb_score}/10"
        )
    context_str = "\n".join(context_lines)

    # 7. Génération finale
    steps.append(AgentStep(step="generation", status="Terminé"))
    final_answer = llm.invoke(
        GENERATOR_PROMPT.format(
            context=context_str or "Aucun film ne correspond à ces critères."
        )
    ).content

    return {
        "current_step": "completed",
        "steps": steps,
        "sql_filters": merged_filters,
        "candidate_ids": candidate_ids,
        "retrieved_movies": recommendations,
        "answer": final_answer,
    }


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

    # validation
    res = validation_node(state_1)
    state_1 = state_1.model_copy(update=res)
    print(f"✅ validation → {state_1.steps[-1].status}")

    # aiguillage
    next_node = route_after_title_check(state_1)
    print(f"🔀 Direction : {next_node}")

    if next_node == "direct_movie_detail":
        res = direct_movie_detail_node(state_1)
        state_1 = state_1.model_copy(update=res)
        print(f"\n🤖 RÉPONSE :\n{state_1.answer}")

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

    # validation
    res = validation_node(state_2)
    state_2 = state_2.model_copy(update=res)
    print(f"✅ validation → {state_2.steps[-1].status}")

    # aiguillage
    next_node = route_after_title_check(state_2)
    print(f"🔀 Direction : {next_node}")

    if next_node == "filter_and_search_hybrid":
        res = filter_and_search_hybrid_node(state_2)
        state_2 = state_2.model_copy(update=res)

        print("\n⚙️  Filtres mergés :")
        print(json.dumps(state_2.sql_filters.model_dump(exclude_none=True), indent=2))
        print(f"\n🎯 IDs SQL candidats : {len(state_2.candidate_ids or [])}")
        print(f"📚 Films FAISS retenus : {len(state_2.retrieved_movies)}")
        print(f"\n🤖 RÉPONSE :\n{state_2.answer}")

    print("\n" + "─" * 50)
