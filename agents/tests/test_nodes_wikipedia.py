"""tests/test_nodes_wikipedia.py"""

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage

from agents.nodes_wikipedia import synthesis_node, wikipedia_search_node
from api.schemas import AgentStep

# ==============================================================================
# FIXTURES
# ==============================================================================


@pytest.fixture
def base_state():
    """État minimal par défaut."""
    state = MagicMock()
    state.user_query = "Quel est le synopsis de ce film ?"
    state.steps = []
    state.retrieved_movies = []
    state.data_enrich = {}
    state.branch_search_wiki = "RAG"
    state.enrich_ids = []
    return state


class MockFilmShort:
    def __init__(self, tmdb_id=123, title="Alien", release_date=None):
        self.tmdb_id = tmdb_id
        self.title = title
        self.release_date = release_date
        self.genres = ["Horror"]
        self.tmdb_score = 8.2
        self.synopsis = "A terrifying creature in space."


class MockFilmDetail(MockFilmShort):
    def __init__(self, tmdb_id=123, title="Alien"):
        super().__init__(tmdb_id=tmdb_id, title=title)
        self.realisateur = "Ridley Scott"
        self.director = "Ridley Scott"
        self.release_date = "1979-05-25"  # ← string, pas datetime
        self.runtime = 117
        self.tagline = "In space no one can hear you scream."
        self.imdb_score = 8.1
        self.rotten_tomatometer = 98
        self.collection = None


# ==============================================================================
# TESTS : wikipedia_search_node
# ==============================================================================


def test_wikipedia_search_node_cas1_aucun_film(base_state):
    """
    Cas 1 : retrieved_movies vide → retour immédiat avec data_enrich vide.
    Wikipedia ne doit pas être appelé.
    """
    base_state.retrieved_movies = []

    with patch("agents.nodes_wikipedia.wikipedia_search") as mock_wiki:
        result = wikipedia_search_node(base_state)

    mock_wiki.invoke.assert_not_called()
    assert result["data_enrich"] == {}
    assert result["current_step"] == "wiki_done"
    assert any(s.step == "wikipedia_search" for s in result["steps"])


def test_wikipedia_search_node_cas2_discussion_enrich_ids(base_state):
    """
    Cas 2 : Branche DISCUSSION avec enrich_ids — enrichit uniquement les films ciblés.
    Le film hors enrich_ids ne doit pas être enrichi.
    """
    film_a = MockFilmDetail(tmdb_id=1, title="Alien")
    film_b = MockFilmDetail(tmdb_id=2, title="The Shining")
    base_state.retrieved_movies = [film_a, film_b]
    base_state.branch_search_wiki = "DISCUSSION"
    base_state.enrich_ids = [1]  # Uniquement Alien

    with patch("agents.nodes_wikipedia.wikipedia_search") as mock_wiki:
        mock_wiki.invoke.return_value = {
            "source": "wikipedia",
            "synopsis": "Synopsis wiki Alien.",
            "source_url": "https://en.wikipedia.org/wiki/Alien",
        }
        result = wikipedia_search_node(base_state)

    assert 1 in result["data_enrich"]
    assert 2 not in result["data_enrich"]
    assert mock_wiki.invoke.call_count == 1


def test_wikipedia_search_node_cas3_rag_premier_film_uniquement(base_state):
    """
    Cas 3 : Branche RAG — enrichit uniquement retrieved_movies[0].
    """
    film_a = MockFilmDetail(tmdb_id=1, title="Alien")
    film_b = MockFilmDetail(tmdb_id=2, title="The Shining")
    base_state.retrieved_movies = [film_a, film_b]
    base_state.branch_search_wiki = "RAG"
    base_state.enrich_ids = []

    with patch("agents.nodes_wikipedia.wikipedia_search") as mock_wiki:
        mock_wiki.invoke.return_value = {
            "source": "wikipedia",
            "synopsis": "Synopsis wiki.",
            "source_url": "https://en.wikipedia.org/wiki/Alien",
        }
        result = wikipedia_search_node(base_state)

    assert mock_wiki.invoke.call_count == 1
    assert 1 in result["data_enrich"]
    assert 2 not in result["data_enrich"]


def test_wikipedia_search_node_cas4_recherche_reussie(base_state):
    """
    Cas 4 : Recherche Wikipedia réussie — data_enrich contient le résultat.
    """
    film = MockFilmDetail()
    base_state.retrieved_movies = [film]

    with patch("agents.nodes_wikipedia.wikipedia_search") as mock_wiki:
        mock_wiki.invoke.return_value = {
            "source": "wikipedia",
            "synopsis": "Long synopsis from Wikipedia.",
            "source_url": "https://en.wikipedia.org/wiki/Alien_(film)",
        }
        result = wikipedia_search_node(base_state)

    assert result["data_enrich"][123]["source"] == "wikipedia"
    assert result["data_enrich"][123]["synopsis"] == "Long synopsis from Wikipedia."
    assert result["current_step"] == "wiki_done"


def test_wikipedia_search_node_cas5_erreur_wikipedia(base_state):
    """
    Cas 5 : Erreur Wikipedia — data_enrich contient source=ERROR, pas d'exception levée.
    """
    film = MockFilmDetail()
    base_state.retrieved_movies = [film]

    with patch("agents.nodes_wikipedia.wikipedia_search") as mock_wiki:
        mock_wiki.invoke.side_effect = Exception("Connection timeout")
        result = wikipedia_search_node(base_state)

    assert result["data_enrich"][123]["source"] == "ERROR"
    assert result["data_enrich"][123]["synopsis"] is None
    assert result["current_step"] == "wiki_done"


def test_wikipedia_search_node_release_date_none(base_state):
    """
    Vérifie que release_date=None ne lève pas d'exception.
    """
    film = MockFilmShort(tmdb_id=1, title="Film sans date", release_date=None)
    base_state.retrieved_movies = [film]

    with patch("agents.nodes_wikipedia.wikipedia_search") as mock_wiki:
        mock_wiki.invoke.return_value = {
            "source": "wikipedia",
            "synopsis": "ok",
            "source_url": "",
        }
        result = wikipedia_search_node(base_state)

    # year=None doit être passé sans exception
    call_kwargs = mock_wiki.invoke.call_args[0][0]
    assert call_kwargs["year"] is None


def test_wikipedia_search_node_discussion_enrich_ids_vide(base_state):
    """
    Cas 3 fallback : Branche DISCUSSION mais enrich_ids vide → enrichit retrieved_movies[0].
    """
    film = MockFilmDetail()
    base_state.retrieved_movies = [film]
    base_state.branch_search_wiki = "DISCUSSION"
    base_state.enrich_ids = []  # vide → fallback RAG

    with patch("agents.nodes_wikipedia.wikipedia_search") as mock_wiki:
        mock_wiki.invoke.return_value = {
            "source": "wikipedia",
            "synopsis": "ok",
            "source_url": "",
        }
        result = wikipedia_search_node(base_state)

    assert mock_wiki.invoke.call_count == 1
    assert 123 in result["data_enrich"]


def test_wikipedia_search_node_multi_films_discussion(base_state):
    """
    Cas 2 multi-films : plusieurs enrich_ids → Wikipedia appelé pour chacun.
    """
    films = [MockFilmDetail(tmdb_id=i, title=f"Film {i}") for i in range(1, 4)]
    base_state.retrieved_movies = films
    base_state.branch_search_wiki = "DISCUSSION"
    base_state.enrich_ids = [1, 2, 3]

    with patch("agents.nodes_wikipedia.wikipedia_search") as mock_wiki:
        mock_wiki.invoke.return_value = {
            "source": "wikipedia",
            "synopsis": "ok",
            "source_url": "",
        }
        result = wikipedia_search_node(base_state)

    assert mock_wiki.invoke.call_count == 3
    assert all(i in result["data_enrich"] for i in [1, 2, 3])


def test_wikipedia_search_node_steps_append(base_state):
    """
    Vérifie que wikipedia_search_node ajoute bien un AgentStep.
    """
    base_state.steps = [AgentStep(step="verif_film", status="valid")]
    base_state.retrieved_movies = [MockFilmDetail()]

    with patch("agents.nodes_wikipedia.wikipedia_search") as mock_wiki:
        mock_wiki.invoke.return_value = {
            "source": "wikipedia",
            "synopsis": "ok",
            "source_url": "",
        }
        result = wikipedia_search_node(base_state)

    assert len(result["steps"]) == 2
    assert result["steps"][-1].step == "wikipedia_search"


# ==============================================================================
# TESTS : synthesis_node
# ==============================================================================


def test_synthesis_node_cas1_aucun_film(base_state):
    """
    Cas 1 : retrieved_movies vide → data_enriched = 'Aucune donnée disponible.'
    llm_synthesis ne doit pas être appelé.
    """
    base_state.retrieved_movies = []
    base_state.data_enrich = {}

    with patch("agents.nodes_wikipedia.llm_synthesis") as mock_llm:
        result = synthesis_node(base_state)

    mock_llm.invoke.assert_not_called()
    assert result["data_enriched"] == "Aucune donnée disponible."
    assert result["current_step"] == "synthesis_done"


def test_synthesis_node_cas2_wikipedia_disponible(base_state):
    """
    Cas 2 : data_enrich contient un synopsis Wikipedia valide →
    le contexte LLM doit inclure 'Synopsis Wikipedia'.
    """
    film = MockFilmDetail()
    base_state.retrieved_movies = [film]
    base_state.data_enrich = {
        123: {
            "source": "wikipedia",
            "synopsis": "Synopsis enrichi depuis Wikipedia.",
            "source_url": "https://en.wikipedia.org/wiki/Alien",
        }
    }

    with patch("agents.nodes_wikipedia.llm_synthesis") as mock_llm:
        mock_llm.invoke.return_value = AIMessage(content="Synthèse enrichie.")
        result = synthesis_node(base_state)

    assert result["data_enriched"] == "Synthèse enrichie."
    call_content = mock_llm.invoke.call_args[0][0][0].content
    assert "Synopsis Wikipedia" in call_content
    assert "Synopsis enrichi depuis Wikipedia." in call_content


def test_synthesis_node_cas3_wikipedia_indisponible(base_state):
    """
    Cas 3 : source=ERROR → données DB seules dans le contexte, pas de synopsis Wikipedia.
    """
    film = MockFilmDetail()
    base_state.retrieved_movies = [film]
    base_state.data_enrich = {123: {"source": "ERROR", "synopsis": None}}

    with patch("agents.nodes_wikipedia.llm_synthesis") as mock_llm:
        mock_llm.invoke.return_value = AIMessage(content="Synthèse DB seule.")
        result = synthesis_node(base_state)

    call_content = mock_llm.invoke.call_args[0][0][0].content
    assert "Synopsis Wikipedia" not in call_content
    assert "Alien" in call_content


def test_synthesis_node_cas3_sources_invalides(base_state):
    """
    Cas 3 : Toutes les sources invalides (NOT_FOUND, NO_SUMMARY, EMPTY_TITLE)
    → données DB seules pour chacune.
    """
    for source in ("NOT_FOUND", "NO_SUMMARY", "EMPTY_TITLE"):
        film = MockFilmDetail()
        base_state.retrieved_movies = [film]
        base_state.data_enrich = {123: {"source": source, "synopsis": None}}

        with patch("agents.nodes_wikipedia.llm_synthesis") as mock_llm:
            mock_llm.invoke.return_value = AIMessage(content="ok")
            result = synthesis_node(base_state)

        call_content = mock_llm.invoke.call_args[0][0][0].content
        assert "Synopsis Wikipedia" not in call_content, f"Échec pour source={source}"


def test_synthesis_node_cas4_llm_reussi(base_state):
    """
    Cas 4 : llm_synthesis répond correctement → data_enriched = contenu LLM.
    """
    film = MockFilmDetail()
    base_state.retrieved_movies = [film]
    base_state.data_enrich = {}

    with patch("agents.nodes_wikipedia.llm_synthesis") as mock_llm:
        mock_llm.invoke.return_value = AIMessage(content="Réponse factuelle précise.")
        result = synthesis_node(base_state)

    assert result["data_enriched"] == "Réponse factuelle précise."
    assert result["current_step"] == "synthesis_done"


def test_synthesis_node_cas5_llm_echec_fallback(base_state):
    """
    Cas 5 : llm_synthesis plante → fallback = full_context (données brutes).
    Pas d'exception levée.
    """
    film = MockFilmDetail()
    base_state.retrieved_movies = [film]
    base_state.data_enrich = {}

    with patch("agents.nodes_wikipedia.llm_synthesis") as mock_llm:
        mock_llm.invoke.side_effect = Exception("Ollama unreachable")
        result = synthesis_node(base_state)

    assert result["current_step"] == "synthesis_done"
    assert "Alien" in result["data_enriched"]  # full_context contient les données DB
    assert any(s.step == "synthesis" for s in result["steps"])


def test_synthesis_node_multi_films_contexte(base_state):
    """
    Vérifie que le contexte LLM contient les données de TOUS les films,
    séparés par '---'.
    """
    films = [MockFilmDetail(tmdb_id=i, title=f"Film {i}") for i in range(1, 4)]
    base_state.retrieved_movies = films
    base_state.data_enrich = {}

    with patch("agents.nodes_wikipedia.llm_synthesis") as mock_llm:
        mock_llm.invoke.return_value = AIMessage(content="ok")
        result = synthesis_node(base_state)

    call_content = mock_llm.invoke.call_args[0][0][0].content
    assert "Film 1" in call_content
    assert "Film 2" in call_content
    assert "Film 3" in call_content
    assert "---" in call_content


def test_synthesis_node_wiki_synopsis_tronque_a_3000(base_state):
    """
    Vérifie que le synopsis Wikipedia est tronqué à 3000 caractères.
    """
    film = MockFilmDetail()
    long_synopsis = "x" * 5000
    base_state.retrieved_movies = [film]
    base_state.data_enrich = {
        123: {"source": "wikipedia", "synopsis": long_synopsis, "source_url": ""}
    }

    with patch("agents.nodes_wikipedia.llm_synthesis") as mock_llm:
        mock_llm.invoke.return_value = AIMessage(content="ok")
        result = synthesis_node(base_state)

    call_content = mock_llm.invoke.call_args[0][0][0].content
    # Le synopsis tronqué ne doit pas dépasser 3000 'x'
    assert "x" * 3001 not in call_content
    assert "x" * 3000 in call_content


def test_synthesis_node_film_sans_attributs_optionnels(base_state):
    """
    Vérifie que getattr défensif ne lève pas d'exception
    si les attributs optionnels sont None.
    """
    film = MagicMock()
    film.tmdb_id = 42
    film.title = "Film Incomplet"
    film.realisateur = None
    film.director = None
    film.release_date = None
    film.genres = None
    film.synopsis = None
    film.tmdb_score = None
    film.imdb_score = None
    film.rotten_tomatometer = None
    film.runtime = None
    film.collection = None
    film.tagline = None

    base_state.retrieved_movies = [film]
    base_state.data_enrich = {}

    with patch("agents.nodes_wikipedia.llm_synthesis") as mock_llm:
        mock_llm.invoke.return_value = AIMessage(content="ok")
        result = synthesis_node(base_state)

    assert result["current_step"] == "synthesis_done"
    call_content = mock_llm.invoke.call_args[0][0][0].content
    assert "N/A" in call_content


def test_synthesis_node_data_enrich_none(base_state):
    """
    Vérifie que data_enrich=None est géré proprement (fallback vers dict vide).
    """
    film = MockFilmDetail()
    base_state.retrieved_movies = [film]
    base_state.data_enrich = None

    with patch("agents.nodes_wikipedia.llm_synthesis") as mock_llm:
        mock_llm.invoke.return_value = AIMessage(content="ok")
        result = synthesis_node(base_state)

    assert result["current_step"] == "synthesis_done"


def test_synthesis_node_steps_append(base_state):
    """
    Vérifie que synthesis_node ajoute bien un AgentStep en fin de pipeline.
    """
    base_state.steps = [AgentStep(step="wikipedia_search", status="ok")]
    base_state.retrieved_movies = [MockFilmDetail()]
    base_state.data_enrich = {}

    with patch("agents.nodes_wikipedia.llm_synthesis") as mock_llm:
        mock_llm.invoke.return_value = AIMessage(content="ok")
        result = synthesis_node(base_state)

    assert len(result["steps"]) == 2
    assert result["steps"][-1].step == "synthesis"


def test_synthesis_node_question_dans_prompt(base_state):
    """
    Vérifie que user_query est bien injectée dans le prompt envoyé à llm_synthesis.
    """
    film = MockFilmDetail()
    base_state.retrieved_movies = [film]
    base_state.data_enrich = {}
    base_state.user_query = "Qui a réalisé ce film ?"

    with patch("agents.nodes_wikipedia.llm_synthesis") as mock_llm:
        mock_llm.invoke.return_value = AIMessage(content="ok")
        synthesis_node(base_state)

    call_content = mock_llm.invoke.call_args[0][0][0].content
    assert "Qui a réalisé ce film ?" in call_content


def test_wikipedia_search_node_release_date_string(base_state):
    """
    Vérifie que release_date au format string 'YYYY-MM-DD' est bien parsée en année entière.
    """
    film = MockFilmDetail()  # release_date = "1979-05-25"
    base_state.retrieved_movies = [film]

    with patch("agents.nodes_wikipedia.wikipedia_search") as mock_wiki:
        mock_wiki.invoke.return_value = {
            "source": "wikipedia",
            "synopsis": "ok",
            "source_url": "",
        }
        result = wikipedia_search_node(base_state)

    call_kwargs = mock_wiki.invoke.call_args[0][0]
    assert call_kwargs["year"] == 1979


from datetime import date


def test_wikipedia_search_node_release_date_objet_date(base_state):
    """
    Vérifie que release_date sous forme d'objet datetime.date
    est correctement parsée via .year (ligne 98 — branche hasattr).
    """
    film = MockFilmShort(tmdb_id=1, title="Alien", release_date=date(1979, 5, 25))
    base_state.retrieved_movies = [film]

    with patch("agents.nodes_wikipedia.wikipedia_search") as mock_wiki:
        mock_wiki.invoke.return_value = {
            "source": "wikipedia",
            "synopsis": "ok",
            "source_url": "",
        }
        result = wikipedia_search_node(base_state)

    call_kwargs = mock_wiki.invoke.call_args[0][0]
    assert call_kwargs["year"] == 1979
    assert 1 in result["data_enrich"]
