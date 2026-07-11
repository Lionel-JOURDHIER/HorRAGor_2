"""
agents/chat_terminal.py
Interface terminal pour dialoguer avec l'agent HorRAGor.

Usage :
    python agents/chat_terminal.py

Stop words : 'exit', 'quit', 'q', 'bye'
"""

import os
import sys
from pathlib import Path

# --- CHEMINS ---
root_path = Path(__file__).resolve().parents[1]  # agents/ → racine
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

from agents.graph import graph as build_my_graph
from api.schemas import ChatFilters
from database.connection import db_session
from database.faiss_service import faiss_global_service

STOP_WORDS = {"exit", "quit", "q", "bye"}


def build_faiss():
    """Charge l'index FAISS depuis le disque ou le construit depuis Supabase."""
    index_path = os.getenv(
        "FAISS_INDEX_PATH", str(root_path / "faiss_data/horragor.index")
    )
    mapping_path = os.getenv(
        "FAISS_MAPPING_PATH", str(root_path / "faiss_data/horragor_mapping.json")
    )

    loaded = faiss_global_service.load_index(index_path, mapping_path)

    if not loaded:
        print("🔧 Construction de l'index FAISS depuis Supabase...")
        with db_session() as session:
            faiss_global_service.build_index(session)
        faiss_global_service.save_index(index_path, mapping_path)

    print()


_graph = build_my_graph()


def chat(user_input: str, thread_id: str = "default") -> str:
    config = {"configurable": {"thread_id": thread_id}}
    """Envoie une requête à l'agent et retourne la réponse finale."""
    initial_state = {
        "user_query": user_input,
        "initial_filters": ChatFilters(),
    }

    result = _graph.invoke(initial_state, config=config)
    return result.get("answer", "⚠️ Aucune réponse générée.")


def main():
    print("=" * 50)
    print("🎬 HorRAGor — Interface Terminal")
    print("   Tapez 'exit' pour quitter.")
    print("=" * 50)

    build_faiss()

    while True:
        try:
            user_input = input("Vous : ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n👋 À bientôt.")
            break

        if not user_input:
            continue

        if user_input.lower() in STOP_WORDS:
            print("👋 À bientôt.")
            break

        print("🤖 HorRAGor : ", end="", flush=True)
        answer = chat(user_input)
        print(answer)
        print()


if __name__ == "__main__":
    main()
