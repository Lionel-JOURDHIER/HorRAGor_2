"""agents/tools/wiki_tools.py
Outil (Tool) de recherche documentaire et d'enrichissement via l'API Wikipédia.

Ce module définit l'outil mis à la disposition de l'agent LangGraph pour
effectuer des recherches externes sur l'encyclopédie Wikipédia. Il intervient
principalement lorsque les informations de la table locale (comme le synopsis)
sont absentes ou incomplètes, permettant ainsi d'enrichir le contexte du LLM
et d'alimenter l'endpoint '/wikipedia'.

Fonctionnalités principales :
    - Recommandation étendue : Recherche dynamique de pages Wikipédia basées sur le titre d'un film.
    - Parsing propre : Extraction et nettoyage textuel du résumé principal (synopsis)
      pour éviter d'injecter du code HTML ou des caractères parasites dans le prompt.

Dépendances principales :
    - langchain_core.tools (tool)
    - wikipedia (ou requests pour l'interrogation directe de l'API MediaWiki)

Auteur/Responsable : Équipe Agents
"""

import requests
from urllib.parse import quote
from langchain_core.tools import tool

from api.schemas import WikipediaRequest, WikipediaResponse

SEARCH_URL = "https://en.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": "HorRAGor/2.0 (educational project)"}

def _search_wiki(title: str) -> str | None:
    try:
        params = {
            "action": "query",
            "list": "search",
            "srsearch": title,
            "format": "json"
        }

        r = requests.get(SEARCH_URL, params=params, headers=HEADERS, timeout=4)

        if r.status_code != 200:
            return None

        data = r.json()
        results = data.get("query", {}).get("search", [])

        if not results:
            return None

        return results[0]["title"]

    except Exception as e:
        print("SEARCH ERROR:", repr(e))
        raise

def _get_summary(title: str) -> tuple[str | None, str | None]:
    try:
        params = {
            "action": "query",
            "prop": "extracts|info",
            "exintro": True,
            "explaintext": True,
            "inprop": "url",
            "titles": title,
            "format": "json"
        }

        r = requests.get(
            SEARCH_URL,
            params=params,
            headers=HEADERS,
            timeout=4
        )

        data = r.json()

        pages = data.get("query", {}).get("pages", {})

        if not pages:
            return None, None

        page = next(iter(pages.values()))

        summary = page.get("extract")
        url = page.get("fullurl")

        return summary, url

    except Exception as e:
        print("SUMMARY ERROR:", repr(e))
        raise

# MAIN PIPELINE TOOL ---------------------------
@tool
def wikipedia_search(title: str, year: int | None = None) -> dict:
    """ Search Wikipedia for a film and return structured data.

    Args:
        title: Movie title
        year: Optional release year for disambiguation

    Returns:
        dict containing:
            - title: resolved Wikipedia page title
            - synopsis: extracted summary text
            - source_url: Wikipedia page URL
            - source: "wikipedia" if any else "ERROR"
    """
    try:
        if not title:
            return {
                "title": None,
                "synopsis": None,
                "source_url": None,
                "source": "EMPTY_TITLE"
            }

        query = f"{title} {year}" if year else title
        best_title = _search_wiki(query)

        if not best_title:
            return {
                "title": title,
                "synopsis": None,
                "source_url": None,
                "source": "NOT_FOUND"
            }

        summary, url = _get_summary(best_title)

        if not summary:
            return {
                "title": best_title,
                "synopsis": None,
                "source_url": url,
                "source": "NO_SUMMARY"
            }

        return {
            "title": best_title,
            "synopsis": summary[:15000],
            "source_url": url,
            "source": "wikipedia"
        }

    except requests.Timeout:
        return {"error": "TIMEOUT"}

    except requests.ConnectionError:
        return {"error": "CONNECTION_ERROR"}

    except Exception:
        return {"error": "UNKNOWN_ERROR"}