# monitoring/langfuse_client.py
"""
Client Langfuse pour le monitoring HorRAGor.
Centralise la connexion au serveur Langfuse.
"""

import os

from langfuse import Langfuse

langfuse = Langfuse(
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    base_url=os.getenv("LANGFUSE_HOST"),
)
