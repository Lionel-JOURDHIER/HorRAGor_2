# tests/test_films.py

def test_get_film(client):

    response = client.get("/film/898555")

    assert response.status_code == 200

    data = response.json()

    assert "tmdb_id" in data
    assert "title" in data