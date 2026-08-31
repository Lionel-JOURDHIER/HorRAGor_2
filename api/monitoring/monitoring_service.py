"""
Service de récupération des métriques Langfuse.

Ce module centralise les appels vers l'API Langfuse afin de fournir
des statistiques exploitables par le frontend (Streamlit).

Responsabilités :
    - récupérer les traces ;
    - calculer des métriques globales ;
    - préparer les données pour les endpoints FastAPI.

Auteur :
    Hanna
"""

from __future__ import annotations

import os
from typing import Any

import requests


class MonitoringService:
    """
    Service d'accès aux métriques Langfuse.
    """

    def __init__(self) -> None:
        self.host = os.getenv("LANGFUSE_HOST", "http://localhost:3000")
        self.public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
        self.secret_key = os.getenv("LANGFUSE_SECRET_KEY")

    @property
    def auth(self) -> tuple[str, str]:
        """
        Authentification Basic utilisée par l'API Langfuse.
        """
        return self.public_key, self.secret_key

    def get_traces(self, limit: int = 100) -> list[dict[str, Any]]:
        """
        Récupère les dernières traces Langfuse.

        Args:
            limit: nombre maximum de traces.

        Returns:
            Liste des traces.
        """

        response = requests.get(
            f"{self.host}/api/public/traces",
            params={"limit": limit},
            auth=self.auth,
            timeout=10,
        )

        response.raise_for_status()

        return response.json().get("data", [])

    def get_metrics(self) -> dict[str, Any]:
        """
        Calcule des métriques simples à partir des traces.

        Returns:
            Dictionnaire prêt à être envoyé au frontend.
        """

        traces = self.get_traces()

        total_latency = 0
        total_input_tokens = 0
        total_output_tokens = 0

        for trace in traces:
            total_latency += trace.get("latency", 0)

            usage = trace.get("usage", {})

            total_input_tokens += usage.get("input", 0)
            total_output_tokens += usage.get("output", 0)

        total_traces = len(traces)

        return {
            "total_traces": total_traces,
            "average_latency_ms": (
                total_latency / total_traces if total_traces else 0
            ),
            "input_tokens": total_input_tokens,
            "output_tokens": total_output_tokens,
            "total_tokens": total_input_tokens + total_output_tokens,
        }

# Instance utilisée par FastAPI
monitoring_service = MonitoringService()