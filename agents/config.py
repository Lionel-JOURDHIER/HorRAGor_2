"""agents/config.py
Centralisation de l'initialisation des modèles de langage locaux (Souverains).
"""

import os

from dotenv import load_dotenv
from langchain_ollama import ChatOllama

load_dotenv()

_OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")

# LLM Principal pour la génération de texte et l'analyse sémantique
llm = ChatOllama(
    # model="granite4.1:8b",   # TOO HEAVY
    model="granite4.1:3b",
    base_url=_OLLAMA_URL,
    temperature=0,  # Température basse pour privilégier la fidélité au contexte RAG
)

# Variante du LLM configurée strictement pour l'extraction de données structurées (JSON)
structured_llm = ChatOllama(
    # model="granite4.1:8b",    # TOO HEAVY
    model="granite4.1:3b",
    base_url=_OLLAMA_URL,
    temperature=0.0,  # Zéro créativité pour l'extraction factuelle des filtres
    format="json",  # Force le serveur Ollama à valider et renvoyer du JSON brut
)
