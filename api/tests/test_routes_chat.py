# api/tests/test_routeschat.py
import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from api.auth_utils import get_current_user
from api.main import app

FAKE_USER = SimpleNamespace(id=1, email="test@example.com", is_active=True)


@pytest.fixture(autouse=True)
def override_current_user():
    """/chat/response_stream exige un utilisateur authentifié (thread_id
    dérivé de son id) — on court-circuite la dépendance pour ces tests."""
    app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    yield
    app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------
# /chat/response_stream — single film
# ---------------------------------------------------------


@patch("api.routes.run_agent_stream_final")
def test_chat_response_stream_single_film(mock_stream, client):

    async def fake_stream(request, user):
        yield {
            "type": "step",
            "node": "search_vector_node",
            "step": {
                "steps": [
                    {
                        "step": "search",
                        "status": "completed",
                    }
                ]
            },
        }

        yield {
            "type": "final",
            "result": {
                "answer": "Voici le film",
                "steps": [
                    {
                        "step": "search",
                        "status": "completed",
                    }
                ],
                "retrieved_movies": [
                    {
                        "tmdb_id": 115128,
                        "title": "Creature of the Walking Dead",
                        "original_title": "Creature of the Walking Dead",
                        "original_language": "en",
                        "realisateur": None,
                        "release_date": "1965-06-15",
                        "runtime": 72,
                        "status": "Released",
                        "synopsis": "Horror movie",
                        "tagline": "Horror-Cade of Excitement",
                        "director": None,
                        "genres": ["Horror", "Science Fiction"],
                        "poster_url": "https://example.com/poster.jpg",
                        "backdrop_url": None,
                        "budget": None,
                        "revenue": None,
                        "tmdb_score": 3.3,
                        "tmdb_vote_count": 16,
                        "imdb_score": 2.9,
                        "imdb_vote_count": 346,
                        "rotten_tomatometer": None,
                        "rotten_audience_score": 0,
                        "aggregated_score": 31.0,
                        "collection": None,
                    }
                ],
            },
        }

    mock_stream.side_effect = fake_stream

    response = client.post(
        "/chat/response_stream",
        json={
            "message": "Tell me about Creature of the Walking Dead",
            "filters": None,
        },
    )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

    events = [
        line.removeprefix("data: ")
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]

    final_event = json.loads(events[-2])

    assert final_event["answer"] == "Voici le film"
    assert final_event["film"]["tmdb_id"] == 115128
    assert final_event["film"]["title"] == "Creature of the Walking Dead"
    assert final_event["recommendations"] == []

    assert json.loads(events[-1]) == {"type": "done"}


# ---------------------------------------------------------
# /chat/response_stream — recommendations
# ---------------------------------------------------------


@patch("api.routes.run_agent_stream_final")
def test_chat_response_stream_recommendations(mock_stream, client):

    async def fake_stream(request, user):
        yield {
            "type": "final",
            "result": {
                "answer": "Voici les recommandations",
                "steps": [],
                "retrieved_movies": [
                    {
                        "tmdb_id": 1,
                        "title": "Film 1",
                    },
                    {
                        "tmdb_id": 2,
                        "title": "Film 2",
                    },
                ],
            },
        }

    mock_stream.side_effect = fake_stream

    response = client.post(
        "/chat/response_stream",
        json={
            "message": "Recommend films",
            "filters": None,
        },
    )

    assert response.status_code == 200

    events = [
        line.removeprefix("data: ")
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]

    final_event = json.loads(events[-2])

    assert final_event["answer"] == "Voici les recommandations"
    assert final_event["film"] is None
    assert len(final_event["recommendations"]) == 2

    assert final_event["recommendations"][0]["tmdb_id"] == 1
    assert final_event["recommendations"][0]["title"] == "Film 1"

    assert final_event["recommendations"][1]["tmdb_id"] == 2
    assert final_event["recommendations"][1]["title"] == "Film 2"

    assert json.loads(events[-1]) == {"type": "done"}
