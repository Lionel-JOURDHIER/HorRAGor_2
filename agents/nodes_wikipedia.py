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

from langchain_core.messages import SystemMessage

root_path = Path(__file__).resolve().parent.parent
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))  # pragma: no cover

from agents.config import llm_synthesis
from agents.tools.wiki_tools import wikipedia_search
from api.schemas import AgentState, AgentStep

# LOGGER ------------------------------------------------------
from logger import get_logger, setup_logger

setup_logger()
logger = get_logger("NODES")

# ==============================================================================
# PHASE 4 : AGENT WIKIPEDIA
# ==============================================================================


def wikipedia_search_node(state: AgentState) -> Dict[str, Any]:
    """
    Recherche Wikipedia pour le film principal de retrieved_movies.
    Alimente data_enrich avec le résultat brut pour synthesis_node.
    Commun aux branches RAG et DISCUSSION.
    """
    logger.info("[wikipedia_search_node] Recherche Wikipedia.")
    steps = list(state.steps)

    # Cas 1 : Aucun film en contexte — sécurité.
    if not state.retrieved_movies:
        logger.warning("[wikipedia_search_node] Aucun film en contexte.")
        steps.append(
            AgentStep(step="wikipedia_search", status="Aucun film à enrichir.")
        )
        return {
            "current_step": "wiki_done",
            "data_enrich": {},
            "steps": steps,
        }

    # Récupération des attribut du state
    branch = getattr(state, "branch_search_wiki", "RAG")
    enrich_ids = set(getattr(state, "enrich_ids", []))

    # Cas 2 : Branche DISCUSSION — on enrichit uniquement les films listés dans enrich_ids.
    if branch == "DISCUSSION" and enrich_ids:
        films_to_enrich = [f for f in state.retrieved_movies if f.tmdb_id in enrich_ids]
        logger.info(
            f"[wikipedia_search_node] DISCUSSION — {len(films_to_enrich)} film(s) à enrichir : "
            f"{[f.title for f in films_to_enrich]}"
        )

    # Cas 3 : Branche RAG — on enrichit uniquement le premier film de retrieved_movies.
    else:
        films_to_enrich = [state.retrieved_movies[0]]
        logger.info(
            f"[wikipedia_search_node] RAG — enrichissement pour : '{films_to_enrich[0].title}'"
        )

    # Recherche Wikipedia pour chaque film ciblé.
    wiki_results: Dict[int, dict] = {}
    for film in films_to_enrich:
        title = film.title
        release_date = getattr(film, "release_date", None)
        if release_date and hasattr(release_date, "year"):
            year = release_date.year
        elif release_date and isinstance(release_date, str):
            year = int(release_date[:4])
        else:
            year = None

        # Cas 4 : Recherche Wikipedia réussie.
        try:
            result = wikipedia_search.invoke({"title": title, "year": year})
            wiki_results[film.tmdb_id] = result
            logger.info(
                f"[wikipedia_search_node] '{title}' → source='{result.get('source')}'"
            )
        # Cas 5 : Erreur Wikipedia pour ce film — on stocke un résultat vide.
        except Exception as e:
            logger.error(f"[wikipedia_search_node] Erreur pour '{title}' : {e}.")
            wiki_results[film.tmdb_id] = {
                "source": "ERROR",
                "synopsis": None,
                "source_url": None,
            }

    steps.append(
        AgentStep(
            step="wikipedia_search",
            status=f"Wikipedia enrichi pour {len(wiki_results)} film(s) : {[f.title for f in films_to_enrich]}",
        )
    )

    return {
        "data_enrich": wiki_results,
        "current_step": "wiki_done",
        "steps": steps,
    }


def synthesis_node(state: AgentState) -> Dict[str, Any]:
    """
    Fusionne Wikipedia + FilmDetail et invoque llm_synthesis pour produire
    une réponse ciblée à la question utilisateur (max 200 tokens).
    Produit data_enriched (str) consommé par narrator_node.
    """
    logger.info("[synthesis_node] Fusion Wikipedia + FilmDetail → llm_synthesis.")
    steps = list(state.steps)

    films = state.retrieved_movies
    wiki_data: Dict[int, dict] = getattr(state, "data_enrich", {}) or {}

    # Cas 1 : Aucun film en contexte — sécurité.
    if not films:
        logger.warning("[synthesis_node] Aucun film en contexte.")
        steps.append(AgentStep(step="synthesis", status="Aucun film à synthétiser."))
        return {
            "data_enriched": "Aucune donnée disponible.",
            "current_step": "synthesis_done",
            "steps": steps,
        }

    # Construction du contexte complet pour chaque film.
    # Pour chaque film, on fusionne les données DB avec le résultat Wikipedia si disponible.
    context_blocks = []
    for i, film in enumerate(films):
        # Bloc de base depuis FilmDetail / FilmShort
        base = (
            f"Film {i + 1} : {film.title}\n"
            f"Réalisateur : {getattr(film, 'realisateur', None) or getattr(film, 'director', 'N/A')}\n"
            f"Date de sortie : {getattr(film, 'release_date', 'N/A')}\n"
            f"Genres : {', '.join(film.genres) if getattr(film, 'genres', None) else 'N/A'}\n"
            f"Synopsis DB : {getattr(film, 'synopsis', None) or 'Non disponible'}\n"
            f"Score TMDB : {getattr(film, 'tmdb_score', 'N/A')}/10\n"
            f"Score IMDb : {getattr(film, 'imdb_score', 'N/A')}/10\n"
            f"Score RT : {getattr(film, 'rotten_tomatometer', 'N/A')}%\n"
            f"Durée : {getattr(film, 'runtime', 'N/A')} min\n"
            f"Collection : {getattr(film, 'collection', 'N/A')}\n"
            f"Tagline : {getattr(film, 'tagline', 'N/A')}"
        )

        # Cas 2 : Enrichissement Wikipedia disponible pour ce film.
        wiki = wiki_data.get(film.tmdb_id, {})
        source = wiki.get("source", "ERROR")

        if source not in ("ERROR", "NOT_FOUND", "NO_SUMMARY", "EMPTY_TITLE"):
            wiki_synopsis = wiki.get("synopsis", "")
            wiki_url = wiki.get("source_url", "")
            block = (
                f"{base}\n"
                f"Synopsis Wikipedia : {wiki_synopsis[:10000] if wiki_synopsis else 'Non disponible'}\n"
                f"Source : {wiki_url}"
            )
            logger.info(
                f"[synthesis_node] '{film.title}' — enrichissement Wikipedia OK."
            )

        # Cas 3 : Pas d'enrichissement Wikipedia pour ce film — données DB seules.
        else:
            logger.warning(
                f"[synthesis_node] '{film.title}' — Wikipedia indisponible ({source}). Données DB seules."
            )
            block = base

        context_blocks.append(block)

    full_context = "\n\n---\n\n".join(context_blocks)

    # Appel llm_synthesis pour répondre précisément à la question utilisateur.
    synthesis_prompt = f"""Tu es un assistant cinéma concis et précis.
        Réponds uniquement à la question de l'utilisateur en te basant sur le contexte fourni.
        Ne génère pas de présentation générale des films si ce n'est pas demandé.
        Sois bref et direct. Maximum 200 tokens.

        Contexte :
        {full_context}

        Question : {state.user_query}
        """

    # Cas 4 : Synthèse LLM réussie.
    try:
        response = llm_synthesis.invoke([SystemMessage(content=synthesis_prompt)])
        data_enriched = response.content
        status = f"Synthèse OK pour {len(films)} film(s)."
        logger.info(f"[synthesis_node] {status}")

    # Cas 5 : Échec llm_synthesis — fallback contexte brut.
    except Exception as e:
        logger.error(
            f"[synthesis_node] Erreur llm_synthesis : {e}. Fallback contexte brut."
        )
        data_enriched = full_context
        status = "Erreur llm_synthesis — fallback contexte brut."

    steps.append(AgentStep(step="synthesis", status=status))

    return {
        "data_enriched": data_enriched,
        "current_step": "synthesis_done",
        "steps": steps,
    }
