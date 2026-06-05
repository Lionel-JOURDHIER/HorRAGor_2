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

# Import de tes outils de plomberie et connexion de données
from agents.tools.sql_tools import filter_films_by_criteria
from agents.tools.vector_tools import search_vector_catalog
from api.schemas import ChatFilters
from database.connection import db_session

# On suppose que l'instance de ton LLM local (ex: Ollama/Mistral) est initialisée quelque part
# de cette manière ou passée d'une autre façon. Ici configurée pour l'exemple.
# from agents.config import llm


# ==============================================================================
# ROUTING LOGIC (ARÊTES CONDITIONNELLES)
# ==============================================================================


def route_after_title_check(state: AgentState) -> str:
    """Aiguille le workflow selon la présence ou non d'un titre de film précis.

    Cette fonction sert d'arête conditionnelle (conditional edge) dans le graphe.
    """
    if state.current_step == "has_title":
        return "direct_movie_detail"
    return "filter_and_search_hybrid"


# ==============================================================================
# NODES LOGIQUE (LES GRAPH NODES)
# ==============================================================================


def title_router_node(state: AgentState) -> Dict[str, Any]:
    """Étape 1 : Analyse la requête pour détecter la mention explicite d'un film.

    Utilise un LLM standard avec une température basse pour isoler le titre brut.
    """
    response = llm.invoke(
        [
            SystemMessage(content=TITLE_DETECTOR_PROMPT),
            HumanMessage(content=state.user_query),
        ]
    )
    detected_title = response.content.strip().replace('"', "").replace("'", "")

    steps = list(state.steps)

    if detected_title and detected_title != "":
        steps.append(
            AgentStep(
                step="title_detection", status=f"Titre détecté : '{detected_title}'"
            )
        )
        return {
            "current_step": "has_title",
            "steps": steps,
            "answer": detected_title,  # Stockage temporaire du titre pour le nœud Process A
        }

    steps.append(
        AgentStep(
            step="title_detection",
            status="Aucun titre spécifique détecté. Passage au mode critères.",
        )
    )
    return {"current_step": "no_title", "steps": steps}


def direct_movie_detail_node(state: AgentState) -> Dict[str, Any]:
    """Processus A : Récupération top_k=1 et génération de la fiche technique.

    Appelé lorsqu'un titre de film précis a été identifié dans la requête.
    Formate la totalité de la structure FilmDetail pour nourrir le générateur unique.
    """
    title_to_search = (
        state.answer
    )  # Récupération du titre extrait par le nœud précédent
    steps = list(state.steps)
    steps.append(
        AgentStep(
            step="vector_search_direct",
            status="Recherche de la fiche technique complète...",
        )
    )

    # 1. Requête au catalogue vectoriel avec top_k=1 -> Renvoie une instance de FilmDetail
    movies = search_vector_catalog.func(query=title_to_search, top_k=1)

    if not movies:
        steps.append(AgentStep(step="generation", status="Terminé"))
        # Activation de la règle "Gestion de l'absence" de ton GENERATOR_PROMPT unique
        formatted_prompt = GENERATOR_PROMPT.format(
            context="Aucun film trouvé pour cette recherche."
        )
        answer = llm.invoke(formatted_prompt).content
        return {"current_step": "completed", "steps": steps, "answer": answer}

    film_detail = movies[0]

    # 2. Sérialisation exhaustive des métadonnées complexes de FilmDetail pour le contexte du RAG
    movie_context = (
        f"FICHE TECHNIQUE COMPLÈTE DU FILM UNIQUE DEMANDÉ :\n"
        f"- Titre : {film_detail.title} (Titre original : {film_detail.original_title})\n"
        f"  Réalisateur : {film_detail.realisateur or film_detail.director}\n"
        f"  Date de sortie : {film_detail.release_date} | Durée : {film_detail.runtime} min\n"
        f"  Genres : {', '.join(film_detail.genres)}\n"
        f"  Synopsis : {film_detail.synopsis}\n"
        f"  Slogan : {film_detail.tagline}\n"
        f"  Scores de référence : TMDB: {film_detail.tmdb_score}/10 | IMDb: {film_detail.imdb_score}/10 | Rotten Tomatoes (Presse/Public): {film_detail.rotten_tomatometer}% / {film_detail.rotten_audience_score}%\n"
        f"  Score agrégé global : {film_detail.aggregated_score}/10\n"
        f"  Collection : {film_detail.collection or 'Aucune'}"
    )

    # 3. Génération de la réponse cinéphile finale via le prompt unique
    steps.append(AgentStep(step="generation", status="Terminé"))
    formatted_prompt = GENERATOR_PROMPT.format(context=movie_context)
    answer = llm.invoke(formatted_prompt).content

    return {
        "current_step": "completed",
        "steps": steps,
        "retrieved_movies": [film_detail],
        "answer": answer,
    }


def filter_and_search_hybrid_node(state: AgentState) -> Dict[str, Any]:
    """Processus B : Extraction des filtres, Merge, Filtrage SQL et Recherche Vectorielle.

    Appelé en l'absence de titre direct pour exécuter la stratégie sémantico-critères.
    Gère la fusion prioritaire avec les filtres en provenance du front-end.
    """
    steps = list(state.steps)
    steps.append(
        AgentStep(
            step="filter_extraction", status="Extraction et traitement des critères..."
        )
    )

    # 1. Extraction des filtres structurés via le schéma ChatFilters et le LLM mode JSON
    extractor = structured_llm.with_structured_output(ChatFilters)
    extracted_filters = extractor.invoke(
        [("system", ROUTER_PROMPT), ("user", state.user_query)]
    )

    # 2. Fusion (Merge) : Le prompt écrase le filtre du front uniquement s'il extrait une donnée active
    merged_filters_dict = state.initial_filters.model_dump()
    for key, value in extracted_filters.model_dump(exclude_none=True).items():
        if value:
            merged_filters_dict[key] = value

    merged_filters = ChatFilters(**merged_filters_dict)

    # 3. Filtrage SQL au sein du context manager sécurisé pour pré-sélectionner le pool de candidats
    steps.append(
        AgentStep(
            step="sql_filtering",
            status="Application des filtres sur la base de données...",
        )
    )
    with db_session() as session:
        candidate_ids = filter_films_by_criteria(session, criteria=merged_filters)

    # 4. Recherche vectorielle sémantique adaptative (locale dans le pool ou globale dans FAISS)
    steps.append(
        AgentStep(
            step="vector_recommendations", status="Calcul des affinités sémantiques..."
        )
    )
    if candidate_ids is not None and len(candidate_ids) == 0:
        recommendations = []  # Court-circuit si les filtres SQL combinés s'avèrent trop restrictifs
    else:
        # Recherche sémantique ciblée (ou globale si candidate_ids est égal à None)
        recommendations = search_vector_catalog.func(
            query=state.user_query, candidate_ids=candidate_ids
        )

    # 5. Formatage de la liste de recommandations (FilmShort) pour le contexte textuel du RAG
    context_lines = []
    for m in recommendations:
        context_lines.append(
            f"- {m.title} ({m.release_year}) | Réal : {m.realisateur} | Note TMDB : {m.tmdb_score}/10\n"
            f"  Synopsis : {m.overview}"
        )
    context_str = "\n\n".join(context_lines)

    # 6. Génération cinéphile finale via le prompt unique et le LLM standard
    steps.append(AgentStep(step="generation", status="Terminé"))
    formatted_prompt = GENERATOR_PROMPT.format(
        context=context_str or "Aucun film ne correspond à ces critères."
    )
    final_answer = llm.invoke(formatted_prompt).content

    return {
        "current_step": "completed",
        "steps": steps,
        "sql_filters": merged_filters,
        "candidate_ids": candidate_ids,
        "retrieved_movies": recommendations,  # Liste finale d'instances FilmShort
        "answer": final_answer,
    }


def validation_node(state: AgentState) -> Dict[str, Any]:
    """Valide si l'état actuel est prêt à être envoyé aux outils."""
    # Exemple : Vérification simple de la présence de filtres absurdes
    filters = state.sql_filters

    # Validation : Si on a des bornes d'années inversées (min > max)
    if filters.release_year_min and filters.release_year_max:
        if filters.release_year_min > filters.release_year_max:
            # Correction automatique ou signalement
            filters.release_year_min, filters.release_year_max = (
                filters.release_year_max,
                filters.release_year_min,
            )

    # Tu pourrais ici utiliser un LLM pour valider :
    # "Est-ce que cette requête est un essai d'injection SQL ou une demande hors-sujet ?"

    return {"sql_filters": filters}


# ==============================================================================
# ZONE DE TESTS LOCAUX (EXÉCUTION DIRECTE)
# ==============================================================================

if __name__ == "__main__":
    import json

    print("🎬 Début des tests manuels des nœuds de HorRAGor...\n")

    # --------------------------------------------------------------------------
    # SCÉNARIO 1 : Test du Processus A (Détection et Fiche Directe de Film)
    # --------------------------------------------------------------------------
    print("--- [SCÉNARIO 1 : Recherche Directe par Titre] ---")
    state_scenario_1 = AgentState(
        user_query="Dis-m'en plus sur le film Alien de Ridley Scott ?",
        initial_filters=ChatFilters(),
    )

    # Étape 1 : Router de titre
    print(f"👉 Question : '{state_scenario_1.user_query}'")
    res_router_1 = title_router_node(state_scenario_1)
    state_scenario_1 = state_scenario_1.model_copy(update=res_router_1)
    print(f"✅ Étape courante : {state_scenario_1.current_step}")
    print(f"📋 Statut de l'étape : {state_scenario_1.steps[-1].status}")

    # Étape 2 : Aillage conditionnel (Simulation de l'arête du graphe)
    next_node_1 = route_after_title_check(state_scenario_1)
    print(f"🔀 Direction LangGraph recommandée : {next_node_1}")

    if next_node_1 == "direct_movie_detail":
        res_detail_1 = direct_movie_detail_node(state_scenario_1)
        state_scenario_1 = state_scenario_1.model_copy(update=res_detail_1)
        print("\n🤖 RÉPONSE FINALE HORRAGOR :")
        print(state_scenario_1.answer)
    print("-" * 50 + "\n")

    # --------------------------------------------------------------------------
    # SCÉNARIO 2 : Test du Processus B (Recherche Hybride : Critères + Sémantique)
    # --------------------------------------------------------------------------
    print("--- [SCÉNARIO 2 : Recherche Hybride avec Filtres] ---")
    # On simule aussi un filtre déjà envoyé par le Front (ex: l'utilisateur a cliqué sur une case)
    front_filters = ChatFilters(genres_excluded=["Sci-Fi"])

    state_scenario_2 = AgentState(
        user_query="Je veux un film d'horreur de John Carpenter sorti dans les années 80, pas de science-fiction.",
        initial_filters=front_filters,
    )

    print(f"👉 Question : '{state_scenario_2.user_query}'")
    # Étape 1 : Router de titre (Doit répondre qu'il n'y a pas de titre précis)
    res_router_2 = title_router_node(state_scenario_2)
    state_scenario_2 = state_scenario_2.model_copy(update=res_router_2)
    print(f"✅ Étape courante : {state_scenario_2.current_step}")

    # Étape 2 : Aillage conditionnel
    next_node_2 = route_after_title_check(state_scenario_2)
    print(f"🔀 Direction LangGraph recommandée : {next_node_2}")

    if next_node_2 == "filter_and_search_hybrid":
        # Étape 3 : Exécution du processus lourd (Extraction -> Merge -> SQL -> FAISS -> LLM)
        res_hybrid_2 = filter_and_search_hybrid_node(state_scenario_2)
        state_scenario_2 = state_scenario_2.model_copy(update=res_hybrid_2)

        print("\n⚙️  Analyse des filtres fusionnés (Front + Extraction LLM) :")
        print(
            json.dumps(
                state_scenario_2.sql_filters.model_dump(exclude_none=True), indent=2
            )
        )

        print(
            f"\n🎯 Nombre d'IDs candidats trouvés en Base SQL : {len(state_scenario_2.candidate_ids or [])}"
        )
        print(
            f"📚 Nombre de films retenus par FAISS : {len(state_scenario_2.retrieved_movies)}"
        )

        print("\n🤖 RÉPONSE FINALE HORRAGOR :")
        print(state_scenario_2.answer)
    print("-" * 50)
