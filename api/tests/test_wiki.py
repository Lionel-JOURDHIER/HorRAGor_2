# tests/test_wiki.py

def test_wiki(client):

    response = client.get("/wikipedia/11252")
    data = response.json()
    expected_keys = {"title", "synopsis", "source_url"}

    assert response.status_code == 200
    assert expected_keys.issubset(data.keys())
    assert data["title"] is not None