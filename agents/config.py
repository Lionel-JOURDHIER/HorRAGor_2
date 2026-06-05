"""agents/config.py
Centralisation de l'initialisation des modèles de langage locaux (Souverains).
"""

from langchain_ollama import ChatOllama

# LLM Principal pour la génération de texte et l'analyse sémantique
llm = ChatOllama(
    model="granite4.1:8b",
    temperature=0,  # Température basse pour privilégier la fidélité au contexte RAG
)

# Variante du LLM configurée strictement pour l'extraction de données structurées (JSON)
structured_llm = ChatOllama(
    model="granite4.1:8b",
    temperature=0.0,  # Zéro créativité pour l'extraction factuelle des filtres
    format="json",  # Force le serveur Ollama à valider et renvoyer du JSON brut
)
