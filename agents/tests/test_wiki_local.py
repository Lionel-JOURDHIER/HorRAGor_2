from unittest.mock import MagicMock, patch

import pytest
import requests
from agents.tools.wiki_tools import wikipedia_search

# --- Scénario 1 : Succès total ---


@patch("agents.tools.wiki_tools.requests.get")
def test_wikipedia_search_success(mock_get):

    # Simulation de la réponse de recherche de titre
    mock_search_resp = MagicMock()
    mock_search_resp.status_code = 200
    mock_search_resp.json.return_value = {
        "query": {"search": [{"title": "Alien (film)"}]}
    }

    # Simulation de la réponse de récupération du résumé
    mock_summary_resp = MagicMock()
    mock_summary_resp.status_code = 200
    mock_summary_resp.json.return_value = {
        "query": {
            "pages": {
                "123": {
                    "extract": "Ceci est le résumé du film Alien.",
                    "fullurl": "https://en.wikipedia.org/wiki/Alien_(film)",
                }
            }
        }
    }

    # On fait en sorte que get retourne la recherche d'abord, puis le résumé
    mock_get.side_effect = [mock_search_resp, mock_summary_resp]

    result = wikipedia_search.invoke({"title": "Alien"})

    assert result["title"] == "Alien (film)"
    assert "résumé" in result["synopsis"]
    assert result["source"] == "wikipedia"
    assert result["source_url"] == "https://en.wikipedia.org/wiki/Alien_(film)"


# --- Scénario 2 : Titre non trouvé ---


@patch("agents.tools.wiki_tools.requests.get")
def test_wikipedia_search_not_found(mock_get):

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"query": {"search": []}}
    mock_get.return_value = mock_resp

    result = wikipedia_search.invoke({"title": "FilmInexistant123"})

    assert result["source"] == "NOT_FOUND"
    assert result["synopsis"] is None
    assert result["source_url"] is None


# --- Scénario 3 : Gestion d'erreur réseau ---


@patch("agents.tools.wiki_tools.requests.get")
def test_wikipedia_search_timeout(mock_get):

    mock_get.side_effect = requests.Timeout

    result = wikipedia_search.invoke({"title": "Alien"})

    assert result["error"] == "TIMEOUT"


# 1. Test : Titre vide (Couvre la première zone rouge)


def test_wikipedia_search_empty_title():

    result = wikipedia_search.invoke({"title": ""})

    assert result["source"] == "EMPTY_TITLE"
    assert result["synopsis"] is None


# 2. Test : Aucun résultat trouvé (Couvre la zone NOT_FOUND)


@patch("agents.tools.wiki_tools.requests.get")
def test_wikipedia_search_no_results(mock_get):

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"query": {"search": []}}
    mock_get.return_value = mock_resp

    result = wikipedia_search.invoke({"title": "Inexistant"})

    assert result["source"] == "NOT_FOUND"


# 3. Test : Pas de résumé trouvé sur la page (Couvre la zone NO_SUMMARY)


@patch("agents.tools.wiki_tools.requests.get")
def test_wikipedia_search_no_summary(mock_get):

    # Simulation du succès de la recherche de titre
    mock_search = MagicMock()
    mock_search.status_code = 200
    mock_search.json.return_value = {"query": {"search": [{"title": "Film"}]}}

    # Simulation de l'absence de résumé
    mock_summary = MagicMock()
    mock_summary.status_code = 200
    mock_summary.json.return_value = {"query": {"pages": {}}}

    # L'ordre des side_effect correspond à l'ordre d'appel
    mock_get.side_effect = [mock_search, mock_summary]

    result = wikipedia_search.invoke({"title": "Film"})

    assert result["source"] == "NO_SUMMARY"
    assert result["synopsis"] is None


# 4. Test : Erreur de connexion


@patch("agents.tools.wiki_tools.requests.get")
def test_wikipedia_search_connection_error(mock_get):

    mock_get.side_effect = requests.ConnectionError

    result = wikipedia_search.invoke({"title": "Alien"})

    assert result["error"] == "CONNECTION_ERROR"


# 5. Test : Exception générique


@patch("agents.tools.wiki_tools.requests.get")
def test_wikipedia_search_generic_exception(mock_get):

    mock_get.side_effect = Exception("Crash")

    result = wikipedia_search.invoke({"title": "Alien"})

    assert result["error"] == "UNKNOWN_ERROR"


# --- Tests des fonctions internes ---


@patch("agents.tools.wiki_tools.requests.get")
def test_search_wiki_http_error(mock_get):

    # Simulation d'une erreur HTTP
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_get.return_value = mock_resp

    from agents.tools.wiki_tools import _search_wiki

    result = _search_wiki("Un titre")

    assert result is None


@patch("agents.tools.wiki_tools.requests.get")
def test_get_summary_exception_block(mock_get):

    # On force une exception pour couvrir le bloc except
    mock_get.side_effect = Exception("Erreur critique inattendue")

    from agents.tools.wiki_tools import _get_summary

    with pytest.raises(Exception) as excinfo:
        _get_summary("Titre")

    assert "Erreur critique inattendue" in str(excinfo.value)
