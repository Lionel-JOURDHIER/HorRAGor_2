# tests/test_metadata.py

from unittest.mock import patch

def test_list_genre(client):

    response = client.get("/list_genre")

    assert response.status_code == 200

    data = response.json()

    assert "genres" in data
    assert isinstance(data["genres"], list)

def test_list_genre_exception(client):
    with patch("api.routes.get_all_genres") as mock_get_all_genres:
        mock_get_all_genres.side_effect = Exception("DB error")

        response = client.get("/list_genre")

        assert response.status_code == 500
        assert "Failed to retrieve genres" in response.json()["detail"]


def test_list_real(client):

    response = client.get("/list_real")

    assert response.status_code == 200

    data = response.json()

    assert "directors" in data
    assert isinstance(data["directors"], list)

def test_list_real_exception(client):
    with patch("api.routes.get_all_directors") as mock_get_all_genres:
        mock_get_all_genres.side_effect = Exception("DB error")

        response = client.get("/list_real")

        assert response.status_code == 500
        assert "Failed to retrieve directors" in response.json()["detail"]