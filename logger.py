"""logger.py
Module de configuration du système de logging global basé sur Loguru.

Ce module centralise la configuration du logger utilisé dans l'ensemble
du projet HorRAGor (API FastAPI, agents LangGraph, outils RAG, tests).

Il fournit :
    - une configuration unique des logs (console + fichiers)
    - une séparation par niveau (INFO / ERROR / DEBUG)
    - un système de contextualisation par module via `bind`
    - une structure adaptée au débogage d'un pipeline RAG industriel

Fonctionnalités principales :
    - Logging console lisible pour le développement
    - Fichier de logs général (app.log) pour le suivi global
    - Fichier d'erreurs dédié (error.log) pour le monitoring des exceptions
    - Support de la contextualisation des logs par module (API, WIKI, GRAPH, etc.)

Usage :
    from logger import setup_logger, get_logger

    setup_logger()

    logger = get_logger("WIKI_TOOL")
    logger.info("Recherche Wikipedia en cours")

Design :
    Ce module est conçu pour être importé une seule fois au démarrage
    de l'application (FastAPI startup) afin d'éviter la duplication
    des handlers Loguru.

Auteur :
    Équipe HorRAGor - projet pédagogique IA / RAG
"""

from loguru import logger
import sys
from pathlib import Path

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)


def setup_logger():
    logger.remove()

    logger.add(
        sys.stdout,
        level="DEBUG",
        format="<green>{time}</green> | <level>{level}</level> | {extra[module]} | {message}"
    )

    logger.add(
        LOG_DIR / "app.log",
        level="INFO",
        rotation="10 MB",
        retention="7 days",
        format="{time} | {level} | {extra[module]} | {message}"
    )

    logger.add(
        LOG_DIR / "error.log",
        level="ERROR",
        rotation="5 MB",
        retention="14 days",
        format="{time} | {level} | {extra[module]} | {message}"
    )

    return logger


def get_logger(module: str):
    return logger.bind(module=module)