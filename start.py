#!/usr/bin/env python3
"""Script de démarrage complet pour HorRAGor avec authentification.

Ce script lance automatiquement :
1. Création des tables d'authentification
2. API FastAPI en arrière-plan
3. Tests d'authentification
4. Frontend Streamlit

Auteur : Flavie - EPIC 10
"""

import os
import sys
import time
import subprocess
import platform
import requests
from pathlib import Path

def print_header(text: str):
    """Affiche un en-tête stylisé."""
    print(f"\n{'=' * 70}")
    print(f"  {text}")
    print(f"{'=' * 70}\n")

def print_step(step: int, text: str):
    """Affiche une étape numérotée."""
    print(f"\n🔹 ÉTAPE {step}: {text}")
    print("-" * 70)

def run_command(cmd: list, cwd: str = None, check: bool = True) -> subprocess.CompletedProcess:
    """Execute une commande et affiche le résultat."""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            check=check,
            capture_output=True,
            text=True
        )
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
        return result
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur lors de l'exécution : {' '.join(cmd)}")
        print(f"   Code de retour: {e.returncode}")
        if e.stdout:
            print(f"   Sortie: {e.stdout}")
        if e.stderr:
            print(f"   Erreur: {e.stderr}")
        if check:
            sys.exit(1)
        return e

def wait_for_api(url: str = "http://localhost:8000/health", timeout: int = 30):
    """Attend que l'API soit prête."""
    print(f"⏳ Attente du démarrage de l'API (max {timeout}s)...")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                print("✅ API prête !")
                return True
        except requests.exceptions.RequestException:
            pass
        time.sleep(1)
        print(".", end="", flush=True)
    
    print("\n❌ Timeout : l'API n'a pas répondu dans le délai imparti")
    return False

def main():
    """Fonction principale."""
    print_header("🎬 HORRAGOR - DÉMARRAGE AVEC AUTHENTIFICATION")
    
    # Vérifier le répertoire de travail
    project_root = Path(__file__).parent
    os.chdir(project_root)
    print(f"📁 Répertoire de travail : {project_root}")
    
    # ===== ÉTAPE 1 : Créer les tables =====
    print_step(1, "Création des tables d'authentification")
    
    if not (project_root / "database" / "create_auth_tables.py").exists():
        print("❌ Fichier create_auth_tables.py non trouvé")
        sys.exit(1)
    
    run_command(
        [sys.executable, "create_auth_tables.py"],
        cwd=str(project_root / "database")
    )
    
    # ===== ÉTAPE 2 : Installer les dépendances =====
    print_step(2, "Installation des dépendances API")
    
    # Vérifier si uv est installé
    try:
        subprocess.run(["uv", "--version"], check=True, capture_output=True)
        print("✅ uv est installé")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠️ uv n'est pas installé. Installation de uv...")
        run_command([sys.executable, "-m", "pip", "install", "uv"])
    
    run_command(
        ["uv", "sync"],
        cwd=str(project_root / "api")
    )
    
    # ===== ÉTAPE 3 : Démarrer l'API en arrière-plan =====
    print_step(3, "Démarrage de l'API FastAPI")
    
    api_process = None
    try:
        if platform.system() == "Windows":
            # Windows : utiliser subprocess avec CREATE_NEW_PROCESS_GROUP
            api_process = subprocess.Popen(
                ["uv", "run", "uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"],
                cwd=str(project_root / "api"),
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )
        else:
            # Linux/Mac : utiliser nohup
            api_process = subprocess.Popen(
                ["uv", "run", "uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"],
                cwd=str(project_root / "api"),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
        
        print(f"✅ API démarrée (PID: {api_process.pid})")
        print("   URL : http://localhost:8000")
        print("   Docs : http://localhost:8000/docs")
        
        # Attendre que l'API soit prête
        if not wait_for_api():
            print("❌ Impossible de démarrer l'API")
            if api_process:
                api_process.terminate()
            sys.exit(1)
        
    except Exception as e:
        print(f"❌ Erreur lors du démarrage de l'API : {e}")
        sys.exit(1)
    
    # ===== ÉTAPE 4 : Lancer les tests =====
    print_step(4, "Lancement des tests d'authentification")
    
    if (project_root / "test_auth.py").exists():
        try:
            run_command([sys.executable, "test_auth.py"], check=False)
        except Exception as e:
            print(f"⚠️ Erreur lors des tests : {e}")
    else:
        print("⚠️ Fichier test_auth.py non trouvé, tests ignorés")
    
    # ===== ÉTAPE 5 : Démarrer le frontend =====
    print_step(5, "Démarrage du frontend Streamlit")
    
    print("\n✨ L'API est en cours d'exécution en arrière-plan")
    print("🌐 Ouvrez votre navigateur sur : http://localhost:8501")
    print("\n📝 Instructions :")
    print("   1. Créez un compte dans l'onglet 'Inscription'")
    print("   2. Connectez-vous dans l'onglet 'Connexion'")
    print("   3. Profitez de HorRAGor ! 🎬")
    print("\n⚠️ Pour arrêter l'application, appuyez sur Ctrl+C")
    print("-" * 70)
    
    try:
        # Lancer Streamlit (bloquant)
        subprocess.run(
            ["streamlit", "run", "app.py"],
            cwd=str(project_root / "frontend"),
            check=True
        )
    except KeyboardInterrupt:
        print("\n\n🛑 Arrêt de l'application...")
    finally:
        # Arrêter l'API
        if api_process:
            print("🛑 Arrêt de l'API...")
            api_process.terminate()
            try:
                api_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                api_process.kill()
        
        print("\n✅ Application arrêtée proprement")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 Arrêt de l'application...")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Erreur fatale : {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
