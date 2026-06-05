# tests/test_metadata.py

def test_list_genre(client):

    response = client.get("/list_genre")

    assert response.status_code == 200

    data = response.json()

    assert "genres" in data
    assert isinstance(data["genres"], list)


def test_list_real(client):

    response = client.get("/list_real")

    assert response.status_code == 200

    data = response.json()

    assert "directors" in data
    assert isinstance(data["directors"], list)

