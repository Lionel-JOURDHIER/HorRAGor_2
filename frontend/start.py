#!/usr/bin/env python3
"""
Script de démarrage rapide pour l'interface Streamlit HorRAGor.

Usage:
    python start.py
    
Options:
    --port PORT     Port pour Streamlit (défaut: 8501)
    --check-api     Vérifie la connexion à l'API avant de démarrer
"""

import sys
import subprocess
import argparse
import requests
from pathlib import Path


def check_api_connection(api_url: str = "http://localhost:8000") -> bool:
    """Vérifie si l'API est accessible."""
    try:
        response = requests.get(f"{api_url}/health", timeout=5)
        if response.status_code == 200:
            print(f"✅ API connectée : {api_url}")
            return True
        else:
            print(f"⚠️  API répond mais avec un statut {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Impossible de se connecter à l'API : {api_url}")
        print(f"   Erreur : {e}")
        return False


def main():
    """Fonction principale."""
    parser = argparse.ArgumentParser(description="Démarrage de l'interface Streamlit HorRAGor")
    parser.add_argument("--port", type=int, default=8501, help="Port pour Streamlit")
    parser.add_argument("--check-api", action="store_true", help="Vérifier la connexion API")
    parser.add_argument("--api-url", type=str, default="http://localhost:8000", help="URL de l'API")
    
    args = parser.parse_args()
    
    # Vérification de l'API si demandé
    if args.check_api:
        print("🔍 Vérification de la connexion à l'API...")
        if not check_api_connection(args.api_url):
            print("\n⚠️  L'API n'est pas accessible. Voulez-vous continuer quand même ? (o/n)")
            response = input().lower()
            if response != 'o':
                print("Arrêt du démarrage.")
                sys.exit(1)
    
    # Chemin vers app.py
    app_path = Path(__file__).parent / "app.py"
    
    if not app_path.exists():
        print(f"❌ Fichier app.py introuvable : {app_path}")
        sys.exit(1)
    
    # Démarrage de Streamlit
    print(f"\n🚀 Démarrage de l'interface Streamlit sur le port {args.port}...")
    print(f"📍 URL : http://localhost:{args.port}")
    print("\nAppuyez sur Ctrl+C pour arrêter.\n")
    
    try:
        subprocess.run([
            "streamlit", "run",
            str(app_path),
            "--server.port", str(args.port),
            "--server.headless", "true"
        ])
    except KeyboardInterrupt:
        print("\n\n👋 Arrêt de l'application.")
    except FileNotFoundError:
        print("❌ Streamlit n'est pas installé. Installez-le avec : pip install streamlit")
        sys.exit(1)


if __name__ == "__main__":
    main()
