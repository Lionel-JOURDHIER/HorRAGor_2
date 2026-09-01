# api/tests/test_health.py
from unittest.mock import MagicMock
from api.main import app
from fastapi import HTTPException


@app.get("/health")
async def health():
    try:
        ...
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Health check failed: {e}"
        )

