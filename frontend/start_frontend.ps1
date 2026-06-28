# HorRAGor - Script de lancement du Frontend
Write-Host "====================================" -ForegroundColor Cyan
Write-Host " HorRAGor - Lancement du Frontend" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""

# Vérifier si Streamlit est installé
Write-Host "[1/3] Vérification de Streamlit..." -ForegroundColor Yellow
try {
    $streamlitVersion = streamlit --version 2>$null
    Write-Host "✓ Streamlit trouvé: $streamlitVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Streamlit non trouvé. Installation..." -ForegroundColor Red
    pip install streamlit
}

# Vérifier si l'API est accessible
Write-Host ""
Write-Host "[2/3] Vérification de l'API..." -ForegroundColor Yellow
try {
    $apiResponse = Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get -TimeoutSec 2
    Write-Host "✓ API accessible sur http://localhost:8000" -ForegroundColor Green
} catch {
    Write-Host "⚠ API non accessible. Assurez-vous de lancer l'API d'abord:" -ForegroundColor Red
    Write-Host "  cd api" -ForegroundColor White
    Write-Host "  uvicorn main:app --reload" -ForegroundColor White
    Write-Host ""
    $continue = Read-Host "Continuer quand même ? (O/N)"
    if ($continue -ne "O" -and $continue -ne "o") {
        exit
    }
}

# Lancement de Streamlit
Write-Host ""
Write-Host "[3/3] Lancement de Streamlit..." -ForegroundColor Yellow
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "  Interface disponible sur:" -ForegroundColor White
Write-Host "  http://localhost:8501" -ForegroundColor Green
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""
Write-Host "Appuyez sur Ctrl+C pour arrêter" -ForegroundColor Yellow
Write-Host ""

# Changer le répertoire vers le dossier frontend
Set-Location $PSScriptRoot

# Lancer Streamlit
streamlit run app.py
