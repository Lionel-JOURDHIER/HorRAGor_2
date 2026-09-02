# api/tests/test_wiki.py


from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch


def test_wiki(client):

    mock_film = SimpleNamespace(
        title="The Dark",
        release_date=None,
    )

    mock_wikipedia = MagicMock()
    mock_wikipedia.invoke.return_value = {
        "title": "The Dark",
        "synopsis": "A horror film.",
        "source_url": "https://en.wikipedia.org/wiki/The_Dark",
    }

    with (
        patch(
            "api.routes.get_film",
            new=AsyncMock(return_value=mock_film),
        ),
        patch(
            "api.routes.wikipedia_search",
            new=mock_wikipedia,
        ),
    ):
        response = client.get("/wikipedia/11252")

    assert response.status_code == 200

    data = response.json()

    expected_keys = {
        "title",
        "synopsis",
        "source_url",
    }

    assert expected_keys.issubset(data.keys())
    assert data["title"] is not None

    mock_wikipedia.invoke.assert_called_once()
