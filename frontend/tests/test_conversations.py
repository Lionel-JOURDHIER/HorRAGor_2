"""Tests de gestion locale des conversations Streamlit."""

from types import SimpleNamespace

from pytest import MonkeyPatch


def test_create_new_conversation_vide_messages(monkeypatch: MonkeyPatch):
    """Créer une conversation vide préserve l'ancienne et vide le fil actif."""
    import app

    monkeypatch.setattr(app.st, "session_state", SimpleNamespace())
    app.st.session_state.messages = [{"role": "user", "content": "Premier fil"}]
    app.st.session_state.conversations = {
        "conversation-a": {
            "title": "Premier fil",
            "messages": app.st.session_state.messages,
        }
    }
    app.st.session_state.active_conversation_id = "conversation-a"

    app.create_new_conversation()

    assert len(app.st.session_state.conversations) == 2
    assert app.st.session_state.messages == []
    assert app.st.session_state.active_conversation_id != "conversation-a"
    assert app.st.session_state.conversations["conversation-a"]["messages"] == [
        {"role": "user", "content": "Premier fil"}
    ]


def test_delete_active_conversation_garde_un_fil(monkeypatch: MonkeyPatch):
    """Supprimer la conversation active laisse toujours une conversation active."""
    import app

    monkeypatch.setattr(app.st, "session_state", SimpleNamespace())
    app.st.session_state.messages = []
    app.st.session_state.conversations = {
        "conversation-a": {"title": "A", "messages": []}
    }
    app.st.session_state.active_conversation_id = "conversation-a"

    app.delete_conversation("conversation-a")

    assert len(app.st.session_state.conversations) == 1
    assert app.st.session_state.messages == []
    assert (
        app.st.session_state.active_conversation_id
        in app.st.session_state.conversations
        )
