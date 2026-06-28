@echo off
echo ====================================
echo  HorRAGor - Lancement du Frontend
echo ====================================
echo.

echo [1/2] Verification de l'environnement...
cd /d "%~dp0"

echo [2/2] Lancement de Streamlit...
echo.
echo Interface disponible sur: http://localhost:8501
echo.
echo Appuyez sur Ctrl+C pour arreter
echo.

streamlit run app.py

pause
