@echo off
REM Script de démarrage rapide pour tester l'EPIC 10 (Windows)

echo 🚀 === Démarrage de HorRAGor avec authentification ===
echo.

REM 1. Créer les tables si ce n'est pas déjà fait
echo 1️⃣ Création des tables d'authentification...
cd database
python create_auth_tables.py
cd ..
echo.

REM 2. Démarrer l'API en arrière-plan
echo 2️⃣ Démarrage de l'API FastAPI...
cd api
start "HorRAGor API" cmd /k "uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000"
cd ..
echo    ✅ API démarrée sur http://localhost:8000
echo.

REM 3. Attendre que l'API soit prête
echo 3️⃣ Attente du démarrage de l'API...
timeout /t 5 /nobreak >nul
echo.

REM 4. Lancer les tests
echo 4️⃣ Lancement des tests d'authentification...
python test_auth.py
echo.

REM 5. Démarrer le frontend
echo 5️⃣ Démarrage du frontend Streamlit...
echo    💡 Ouvrez http://localhost:8501 dans votre navigateur
cd frontend
streamlit run app.py
