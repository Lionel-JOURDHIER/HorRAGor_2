from agents.tools.wiki_tools import wikipedia_search


def test_wiki_tool_success():
    result = wikipedia_search.invoke({"title": "Alien", "year": 1979})

    assert isinstance(result, dict)
    assert result["title"] is not None
    assert result["source"] == "wikipedia"
    assert result["synopsis"] is not None
    assert result["source_url"] is not None


def test_wiki_not_found():
    result = wikipedia_search.invoke({"title": "asdhakjsdhakjsdh", "year": None})

    assert result["source"] in ["NOT_FOUND", "NO_SUMMARY"]


def test_wiki_empty():
    result = wikipedia_search.invoke({"title": ""})

    assert result["source"] == "EMPTY_TITLE"