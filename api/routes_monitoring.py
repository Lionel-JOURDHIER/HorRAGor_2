# api/routes_monitoring.py
"""
Endpoints de monitoring Langfuse.

Expose les métriques Langfuse pour le frontend Streamlit.
"""

from fastapi import APIRouter, HTTPException

from api.monitoring.monitoring_service import monitoring_service

# LOGGER ------------------------------------------------------
from logger import get_logger, setup_logger

setup_logger()
logger = get_logger("ROUTES")


# ROUTER ---------------------------------------------------------
router = APIRouter(
    prefix="/monitoring",
    tags=["Monitoring"]
)


# METRICS --------------------------------------------------------
@router.get("/metrics")
def get_langfuse_metrics():
    """
    Retourne les métriques globales Langfuse.

    Returns:
        Nombre de traces,
        latence moyenne,
        tokens utilisés.
    """
    try:
        return monitoring_service.get_metrics()

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.get("/traces")
def get_langfuse_traces(limit: int = 20):
    """
    Retourne les dernières traces Langfuse.
    """
    try:
        return {"traces": monitoring_service.get_traces(limit)}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )